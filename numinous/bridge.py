"""
Bridge — connects the Python reach layer to the Elixir Void runtime.

Takes a Manifold Atlas, runs reach_scan() to find implied regions,
combines them with atlas.holes() (structural gaps), serialises to JSON,
and pipes into `mix numinous.open` to open live Void processes in the BEAM.

Usage::

    from core.atlas import Atlas
    from numinous.bridge import open_from_atlas

    atlas = Atlas.build(reg)
    voids = open_from_atlas(atlas)
    for v in voids:
        print(v)
    # {'term': 'agent-identity', 'pressure': 0.4, 'implied_by': [...]}

The bridge is the seam between left and right hemisphere.
Python names what it can. Elixir holds what it can't.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.atlas import Atlas

from .reach import reach_scan

# Path to the Elixir project
_ELIXIR_DIR = Path(__file__).parent.parent / "elixir"


def _holes_from_atlas(atlas: Atlas) -> list[dict]:
    """
    Extract structural holes from the atlas.
    These are topics implied by transition maps but covered by no agent.
    """
    holes = []
    for term in atlas.holes():
        # Find which agents are adjacent (cover terms that overlap with this hole)
        adjacent = []
        for chart in atlas.charts():
            from core.chart import _tokenize
            hole_tokens = _tokenize(term)
            if hole_tokens & chart.vocabulary:
                adjacent.append(chart.agent_name)

        holes.append({
            "term": term,
            "implied_by": adjacent,
            "pressure": min(1.0, len(adjacent) * 0.15),
            "source": "atlas.holes",
        })
    return holes


def _holes_from_reach(atlas: Atlas, top_n: int = 10) -> list[dict]:
    """
    Extract generative reach regions — implied but not present.
    """
    reading = reach_scan(atlas, top_n=top_n)
    return [
        {
            "term": r.term,
            "implied_by": r.implied_by,
            "pressure": r.strength,
            "source": "reach_scan",
        }
        for r in reading.candidate_regions
    ]


def _parse_void_output(output: str) -> list[dict]:
    """Parse VOID lines from mix numinous.open output."""
    voids = []
    for line in output.splitlines():
        if not line.startswith("VOID "):
            continue
        parts = line[5:].split(" ", 2)
        if len(parts) < 2:
            continue
        term = parts[0]
        pressure = float(parts[1]) if len(parts) > 1 else 0.0
        implied_raw = parts[2] if len(parts) > 2 else "[]"
        implied = [t.strip() for t in implied_raw.strip("[]").split(",") if t.strip()]
        voids.append({"term": term, "pressure": pressure, "implied_by": implied})
    return voids


def open_from_atlas(
    atlas: Atlas,
    include_reach: bool = True,
    include_holes: bool = True,
    top_n: int = 10,
) -> list[dict]:
    """
    Open Void processes from a Manifold Atlas.

    Combines structural holes (atlas.holes()) and generative reach regions
    (reach_scan()), deduplicates, and opens them as live BEAM processes via
    the Elixir Field.

    :param atlas: A built Manifold Atlas.
    :param include_reach: Include reach_scan() candidates (default True).
    :param include_holes: Include atlas.holes() structural gaps (default True).
    :param top_n: How many reach candidates to include.
    :returns: List of opened Void dicts with term, pressure, implied_by.

    Example::

        voids = open_from_atlas(atlas)
        for v in voids:
            print(f"{v['term']}: pressure={v['pressure']:.2f}")
    """
    all_holes: list[dict] = []

    if include_holes:
        all_holes.extend(_holes_from_atlas(atlas))

    if include_reach:
        all_holes.extend(_holes_from_reach(atlas, top_n=top_n))

    # Deduplicate by term — keep highest pressure
    seen: dict[str, dict] = {}
    for hole in all_holes:
        term = hole["term"]
        if term not in seen or hole["pressure"] > seen[term]["pressure"]:
            seen[term] = hole

    holes = list(seen.values())

    if not holes:
        return []

    payload = json.dumps(holes)

    result = subprocess.run(
        ["mix", "numinous.open"],
        input=payload,
        capture_output=True,
        text=True,
        cwd=str(_ELIXIR_DIR),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"mix numinous.open failed:\n{result.stderr}"
        )

    return _parse_void_output(result.stdout)
