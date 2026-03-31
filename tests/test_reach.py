"""Tests for numinous.reach — generative territory scanning."""

import pytest
from manifold.atlas import Atlas
from manifold.registry import CapabilityRegistry
from numinous import reach_scan
from numinous.reach import ReachRegion, ReachReading


def _make_atlas() -> Atlas:
    reg = CapabilityRegistry()
    reg.register_self(
        name="braid",
        capabilities=[
            "solar-flare-prediction",
            "active-region-classification",
            "solar-memory-state-machine",
            "signal-processing",
            "machine-learning",
        ],
        address="mem://braid",
    )
    reg.register_self(
        name="stella",
        capabilities=[
            "session-memory",
            "agent-orchestration",
            "context-management",
            "machine-reasoning",
            "signal-awareness",
        ],
        address="mem://stella",
    )
    reg.register_self(
        name="manifold",
        capabilities=[
            "mesh-topology",
            "agent-coordination",
            "memory-topology",
            "signal-detection",
            "solar-topology",
        ],
        address="mem://manifold",
    )
    return Atlas.build(reg)


class TestReachReading:
    def test_returns_reach_reading(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        assert isinstance(reading, ReachReading)

    def test_has_required_fields(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        assert hasattr(reading, 'candidate_regions')
        assert hasattr(reading, 'seam_hints')
        assert hasattr(reading, 'total_implied')
        assert hasattr(reading, 'interpretation')

    def test_interpretation_is_string(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        assert isinstance(reading.interpretation, str)
        assert len(reading.interpretation) > 0

    def test_total_implied_gte_candidates(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        assert reading.total_implied >= len(reading.candidate_regions)


class TestReachRegions:
    def test_candidate_regions_are_reach_regions(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        for r in reading.candidate_regions:
            assert isinstance(r, ReachRegion)

    def test_region_fields(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        if reading.candidate_regions:
            r = reading.candidate_regions[0]
            assert isinstance(r.term, str)
            assert 0.0 <= r.strength <= 1.0
            assert isinstance(r.implied_by, list)
            assert isinstance(r.covering_agents, list)
            assert isinstance(r.interpretation, str)

    def test_sorted_by_strength_descending(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        strengths = [r.strength for r in reading.candidate_regions]
        assert strengths == sorted(strengths, reverse=True)

    def test_no_candidate_already_in_atlas(self):
        atlas = _make_atlas()
        existing = set()
        for chart in atlas.charts():
            existing.update(chart.vocabulary)
        reading = reach_scan(atlas)
        for r in reading.candidate_regions:
            assert r.term not in existing, f"'{r.term}' already in atlas"

    def test_covering_agents_are_known(self):
        atlas = _make_atlas()
        known = {c.agent_name for c in atlas.charts()}
        reading = reach_scan(atlas)
        for r in reading.candidate_regions:
            for agent in r.covering_agents:
                assert agent in known

    def test_finds_implied_regions_with_overlapping_vocab(self):
        """With shared tokens like 'signal', 'memory', 'solar' across 3 agents,
        there should be implied compound regions."""
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        # With high overlap vocabulary, should find candidates
        assert len(reading.candidate_regions) > 0

    def test_top_n_respected(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas, top_n=3)
        assert len(reading.candidate_regions) <= 3


class TestSeamHints:
    def test_seam_hints_are_pairs(self):
        atlas = _make_atlas()
        reading = reach_scan(atlas)
        for pair in reading.seam_hints:
            assert len(pair) == 2
            assert isinstance(pair[0], str)
            assert isinstance(pair[1], str)

    def test_seam_hint_agents_exist(self):
        atlas = _make_atlas()
        known = {c.agent_name for c in atlas.charts()}
        reading = reach_scan(atlas)
        for a, b in reading.seam_hints:
            assert a in known
            assert b in known


class TestEdgeCases:
    def test_single_agent_no_seam_tokens(self):
        reg = CapabilityRegistry()
        reg.register_self(
            name="solo",
            capabilities=["unique-capability-alpha", "unique-capability-beta"],
            address="mem://solo",
        )
        atlas = Atlas.build(reg)
        reading = reach_scan(atlas)
        # No seam tokens — may find no candidates or few
        assert isinstance(reading, ReachReading)

    def test_empty_candidates_interpretation(self):
        # With very minimal non-overlapping vocab, candidates may be empty
        reg = CapabilityRegistry()
        reg.register_self(name="a", capabilities=["aardvark"], address="mem://a")
        reg.register_self(name="b", capabilities=["zebra"], address="mem://b")
        atlas = Atlas.build(reg)
        reading = reach_scan(atlas)
        assert isinstance(reading.interpretation, str)
