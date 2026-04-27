"""
Numinous — the ground the mesh floats in.

Manifold maps what a cognitive mesh knows. Numinous maps what it is
reaching toward — the regions implied by the existing mesh but not
yet named, the patterns present below the threshold of explicit knowledge.

The left hemisphere articulates. The right hemisphere apprehends.
Numinous is the right hemisphere.

Modules:

    reach   — generative territory: what the mesh is reaching toward
    shadow  — apophatic mapping: what the mesh definitively is not
    pulse   — weak signal tracking: sub-threshold patterns over time

Usage::

    from numinous import reach_scan
    from core import Atlas, CapabilityRegistry

    reg = CapabilityRegistry()
    # ... register agents ...
    atlas = Atlas.build(reg)

    reading = reach_scan(atlas)
    print(reading.interpretation)
    for region in reading.candidate_regions[:3]:
        print(f'  {region.term}: {region.strength:.2f} — implied by {region.implied_by}')
"""

from .reach import ReachRegion, ReachReading, reach_scan, auto_stoplist
from .bridge import open_from_atlas

__version__ = "0.2.0"

__all__ = [
    "ReachRegion",
    "ReachReading",
    "reach_scan",
    "open_from_atlas",
]
