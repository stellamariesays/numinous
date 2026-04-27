"""
Reach — generative territory mapping for the cognitive mesh.

Manifold maps what agents know. Reach maps what the mesh is *reaching toward* —
regions strongly implied by the existing vocabulary that haven't been named yet.

The mechanism: agents share vocabulary tokens across seams. Where multiple agents
use the same tokens in different compound terms, a region exists in the overlap
that neither agent has explicitly claimed. That gap is the reach.

This is not prediction. It is reading the negative space.

    reach_scan(atlas) -> ReachReading

The strongest reach regions are where the mesh has the most convergent pressure
toward something it hasn't yet said.

Example::

    from numinous import reach_scan

    reading = reach_scan(atlas)
    for region in reading.candidate_regions[:5]:
        print(region.term, '->', region.implied_by)
        # 'solar-memory' -> ['solar-flare-prediction', 'session-memory', 'solar-memory-state-machine']
        # 'agent-topology' -> ['mesh-topology', 'agent-orchestration', 'topology-analysis']
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from core.atlas import Atlas


def _tokenize(term: str) -> set[str]:
    """Split a capability term into tokens. 'solar-flare-prediction' → {'solar','flare','prediction'}."""
    return set(re.split(r'[-_\s]+', term.lower())) - {'', 'a', 'the', 'of', 'in', 'for'}


def _all_tokens(vocab: set[str]) -> Counter:
    """Count token frequency across a vocabulary."""
    counts: Counter = Counter()
    for term in vocab:
        for tok in _tokenize(term):
            counts[tok] += 1
    return counts


def auto_stoplist(
    atlas: Atlas,
    max_freq_ratio: float = 0.6,
    min_absolute: int = 4,
) -> set[str]:
    """
    Auto-generate a stoplist from the token frequency distribution.

    Tokens that appear in more than ``max_freq_ratio`` of all agents
    (and at least ``min_absolute`` agents) are generic noise — they
    contribute no discriminative value and dominate reach_scan results.

    Returns a set of token strings to exclude.
    """
    tokens_by_agent: dict[str, Counter] = {}
    for chart in atlas.charts():
        tokens_by_agent[chart.agent_name] = _all_tokens(chart.vocabulary)

    total_agents = len(tokens_by_agent) or 1
    agent_presence: Counter = Counter()  # token → number of agents it appears in
    for counts in tokens_by_agent.values():
        for tok in counts:
            agent_presence[tok] += 1

    stoplist: set[str] = set()
    for tok, count in agent_presence.items():
        freq_ratio = count / total_agents
        if freq_ratio >= max_freq_ratio and count >= min_absolute:
            stoplist.add(tok)

    return stoplist


@dataclass
class ReachRegion:
    """
    A region the mesh is reaching toward but hasn't named.

    :param term: The implied term — what the mesh is gesturing at.
    :param strength: Convergence score 0.0–1.0. How strongly the existing mesh implies this region.
    :param implied_by: Existing *capability terms* (compound strings) that contributed
        the tokens implying this region — not raw single tokens.
    :param covering_agents: Agents whose vocabulary comes closest to this region.
    :param interpretation: Human-readable label.
    """

    term: str
    strength: float
    implied_by: list[str]
    covering_agents: list[str]
    interpretation: str


@dataclass
class ReachReading:
    """
    A snapshot of what the mesh is reaching toward.

    :param candidate_regions: Implied but absent regions, sorted by strength descending.
    :param seam_hints: Agent pairs where the reach pressure is strongest.
    :param total_implied: Total number of candidate regions found before filtering.
    :param interpretation: Mesh-level read.
    """

    candidate_regions: list[ReachRegion]
    seam_hints: list[tuple[str, str]]
    total_implied: int
    interpretation: str


def _seam_tokens(atlas: Atlas) -> dict[str, list[str]]:
    """
    Find tokens that appear in 2+ agents' vocabularies.
    Returns: {token: [agent_name, ...]}
    """
    token_agents: dict[str, list[str]] = defaultdict(list)
    for chart in atlas.charts():
        seen = set()
        for term in chart.vocabulary:
            for tok in _tokenize(term):
                if tok not in seen:
                    token_agents[tok].append(chart.agent_name)
                    seen.add(tok)
    # Only tokens shared across 2+ agents
    return {tok: agents for tok, agents in token_agents.items() if len(agents) >= 2}


def _existing_terms(atlas: Atlas) -> tuple[set[str], set[str]]:
    """
    Return two sets:
      - domain_terms: original compound capability strings (e.g. 'identity-modeling')
        Used for the exclusion filter — prevents re-generating already-covered regions.
      - token_terms: tokenised vocabulary single-tokens (e.g. {'identity','modeling'})
        Used for implied_by matching — stable counts, unaffected by domain size.
    """
    domain_terms: set[str] = set()
    token_terms: set[str] = set()
    for chart in atlas.charts():
        domain_terms.update(chart.domain)
        token_terms.update(chart.vocabulary)
    return domain_terms, token_terms


def _implied_compounds(
    shared_tokens: dict[str, list[str]],
    domain_terms: set[str],
    token_terms: set[str],
    existing_tokens_by_agent: dict[str, Counter],
) -> list[tuple[str, float, list[str], list[str]]]:
    """
    Generate candidate compound terms from shared token pairs and triples.
    Returns list of (candidate_term, strength, implied_by_terms, covering_agents).

    Two term sets serve different roles:
      domain_terms — compound capability strings; used ONLY for the exclusion filter
                     (already-covered regions should not re-appear as dark circles)
      token_terms  — single vocab tokens; used for implied_by matching to keep
                     implication counts stable regardless of domain_terms size
    """
    # Exclusion: skip candidates already covered as a compound capability.
    # Must normalise compound strings (e.g. 'identity-modeling') to match
    # the sorted-token candidate format (also 'identity-modeling').
    existing_normalized = {re.sub(r'[-_\s]+', '-', t.lower()) for t in domain_terms}

    # Implied-by matching uses single-token vocabulary terms (original behaviour).
    token_list = list(token_terms)

    # Precompute token rarity (IDF-like): fewer agents = more specific
    total_agents = len(existing_tokens_by_agent) or 1
    token_rarity: dict[str, float] = {}
    for tok, agents in shared_tokens.items():
        token_rarity[tok] = 1.0 - (len(agents) / (2.0 * total_agents))

    shared = list(shared_tokens.keys())
    candidates: dict[str, dict] = {}

    for r in (2, 3):
        for combo in combinations(shared, r):
            candidate = '-'.join(sorted(combo))

            if candidate in existing_normalized:
                continue
            if any(tok in ('and', 'or', 'is', 'to', 'by') for tok in combo):
                continue
            if len(candidate) < 6:
                continue

            # Which vocabulary tokens are implied by (adjacent to) this combo?
            implied_by = []
            covering = set()
            for term in token_list:
                term_toks = _tokenize(term)
                if all(tok in term_toks for tok in combo):
                    implied_by.append(term)
                elif sum(1 for tok in combo if tok in term_toks) >= len(combo) - 1:
                    implied_by.append(term)

            for tok in combo:
                covering.update(shared_tokens[tok])

            if not implied_by:
                continue

            # Cross-domain bonus: tokens from DIFFERENT agents > always co-occurring
            token_agent_sets = [set(shared_tokens[tok]) for tok in combo]
            union = set()
            intersection = None
            for s in token_agent_sets:
                union |= s
                intersection = s if intersection is None else intersection & s
            overlap_ratio = len(intersection or set()) / max(1, len(union))
            cross_domain_bonus = 1.0 - overlap_ratio

            # Average rarity of tokens in this combo
            avg_rarity = sum(token_rarity.get(tok, 0.5) for tok in combo) / len(combo)

            # Strength: base convergence * specificity * cross-domain
            agent_count = len(covering)
            implication_count = len(implied_by)
            base = (agent_count * implication_count) / 20.0
            strength = round(min(1.0, base * avg_rarity * (0.5 + 0.5 * cross_domain_bonus)), 4)

            if strength < 0.05:
                continue

            candidates[candidate] = {
                'strength': strength,
                'implied_by': implied_by[:5],
                'covering_agents': sorted(covering),
            }

    return [
        (term, d['strength'], d['implied_by'], d['covering_agents'])
        for term, d in candidates.items()
    ]


def _region_interpretation(term: str, strength: float, agent_count: int) -> str:
    if strength > 0.6:
        return f"strong convergence — {agent_count} agents pressing toward this"
    elif strength > 0.3:
        return f"active reach — implied across {agent_count} agents"
    else:
        return f"faint signal — {agent_count} agent(s) gesturing this way"


def reach_scan(atlas: Atlas, top_n: int = 15) -> ReachReading:
    """
    Scan the atlas for what the mesh is reaching toward.

    Finds regions strongly implied by the existing vocabulary that haven't
    been named — the generative territory at the edge of the explicit mesh.

    :param atlas: A built Manifold Atlas.
    :param top_n: Number of top candidate regions to return.
    :returns: ReachReading with candidate regions sorted by strength.

    Example::

        reading = reach_scan(atlas)
        print(reading.interpretation)
        for r in reading.candidate_regions[:5]:
            print(f'{r.term}: {r.strength:.2f}')
    """
    shared_tokens = _seam_tokens(atlas)
    domain_terms, token_terms = _existing_terms(atlas)

    # Token counts per agent (for internal use)
    tokens_by_agent: dict[str, Counter] = {}
    for chart in atlas.charts():
        tokens_by_agent[chart.agent_name] = _all_tokens(chart.vocabulary)

    # Build auto-stoplist (issue #2)
    stoplist = auto_stoplist(atlas)

    raw = _implied_compounds(shared_tokens, domain_terms, token_terms, tokens_by_agent)
    total_implied = len(raw)

    # Filter out candidates whose combo tokens are entirely in the stoplist
    raw = [
        (term, strength, ib, ca)
        for term, strength, ib, ca in raw
        if not all(tok in stoplist for tok in _tokenize(term))
    ]

    # Resolve implied_by to capability *terms* not raw tokens (issue #3)
    # Build reverse map: token → set of domain terms containing it
    token_to_domain_terms: dict[str, list[str]] = defaultdict(list)
    for dt in domain_terms:
        for tok in _tokenize(dt):
            token_to_domain_terms[tok].append(dt)

    resolved_raw = []
    for term, strength, implied_by, covering_agents in raw:
        # For each raw token in implied_by, resolve to the domain terms
        # that contributed it
        resolved: list[str] = []
        seen = set()
        combo_tokens = set(_tokenize(term))
        for raw_token in implied_by:
            # raw_token might already be a domain term
            if raw_token in domain_terms:
                if raw_token not in seen:
                    resolved.append(raw_token)
                    seen.add(raw_token)
            else:
                # Resolve to domain terms that contain this token
                for dt in token_to_domain_terms.get(raw_token, []):
                    if dt not in seen and combo_tokens & _tokenize(dt):
                        resolved.append(dt)
                        seen.add(dt)
        # Fallback: if resolution found nothing, keep original
        if not resolved:
            resolved = implied_by[:5]
        resolved_raw.append((term, strength, resolved[:5], covering_agents))

    raw = resolved_raw

    # Sort by strength desc, take top_n
    raw.sort(key=lambda x: x[1], reverse=True)
    raw = raw[:top_n]

    regions = [
        ReachRegion(
            term=term,
            strength=strength,
            implied_by=implied_by,
            covering_agents=covering_agents,
            interpretation=_region_interpretation(term, strength, len(covering_agents)),
        )
        for term, strength, implied_by, covering_agents in raw
    ]

    # Seam hints — agent pairs with most reach pressure between them
    pair_pressure: Counter = Counter()
    for region in regions:
        agents = region.covering_agents
        for a, b in combinations(agents, 2):
            pair_pressure[(a, b)] += region.strength

    seam_hints = [pair for pair, _ in pair_pressure.most_common(5)]

    # Global interpretation
    if not regions:
        interpretation = "mesh is fully articulated — no implied regions found"
    elif regions[0].strength > 0.6:
        interpretation = "strong generative pressure — the mesh is reaching hard toward unnamed territory"
    elif regions[0].strength > 0.3:
        interpretation = "active reach — several implied regions at the edge of the mesh"
    else:
        interpretation = "faint signals — the mesh implies regions but pressure is low"

    return ReachReading(
        candidate_regions=regions,
        seam_hints=seam_hints,
        total_implied=total_implied,
        interpretation=interpretation,
    )
