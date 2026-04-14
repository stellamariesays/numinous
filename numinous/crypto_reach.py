"""
Crypto Reach — specialized reach scan for cryptocurrency research using Stingray.

This module extends the Numinous reach system to find crypto-related research gaps
and leverage the Stingray skill for data gathering that can be folded into Manifold.
"""

from __future__ import annotations

import json
import requests
from dataclasses import dataclass, field
from pathlib import Path

from core.atlas import Atlas
from numinous.reach import reach_scan, _tokenize, ReachRegion, ReachReading


@dataclass
class CryptoResearchRegion(ReachRegion):
    """A crypto research region with Stingray-specific capabilities."""
    research_methods: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    market_focus: str = ""
    
    def to_manifold_compatible(self) -> dict:
        """Convert to format that can be folded into Manifold."""
        return {
            "term": self.term,
            "strength": self.strength,
            "implied_by": self.implied_by,
            "covering_agents": self.covering_agents,
            "interpretation": self.interpretation,
            "crypto_extension": {
                "research_methods": self.research_methods,
                "data_sources": self.data_sources,
                "market_focus": self.market_focus
            }
        }


def crypto_reach_scan(atlas: Atlas, top_n: int = 10) -> ReachReading:
    """
    Scan for crypto-related research gaps using Stingray skill.
    
    Finds regions where the mesh is reaching toward cryptocurrency research
    but hasn't explicitly named them. Uses Stingray capabilities for data gathering.
    """
    # First get the standard reach scan
    standard_reading = reach_scan(atlas, top_n=20)
    
    # Filter and enhance crypto-related regions
    crypto_regions = []
    for region in standard_reading.candidate_regions:
        crypto_score = _assess_crypto_potential(region.term, region.implied_by)
        
        if crypto_score > 0.3:  # Threshold for crypto relevance
            enhanced = CryptoResearchRegion(
                term=region.term,
                strength=region.strength * crypto_score,  # Boost crypto potential
                implied_by=region.implied_by,
                covering_agents=region.covering_agents,
                interpretation=f"crypto research: {region.interpretation}",
                research_methods=stingray_research_methods(region.term),
                data_sources=stingray_data_sources(region.term),
                market_focus=identify_market_focus(region.term)
            )
            crypto_regions.append(enhanced)
    
    # Sort by enhanced strength
    crypto_regions.sort(key=lambda x: x.strength, reverse=True)
    crypto_regions = crypto_regions[:top_n]
    
    return ReachReading(
        candidate_regions=crypto_regions,
        seam_hints=standard_reading.seam_hints,
        total_implied=len(crypto_regions),
        interpretation=f"crypto research reach: {len(crypto_regions)} potential regions identified"
    )


def _assess_crypto_potential(term: str, implied_by: list[str]) -> float:
    """Assess how crypto-relevant a reach region is."""
    crypto_keywords = {
        'bitcoin', 'crypto', 'blockchain', 'defi', 'trading', 'market', 'price',
        'wallet', 'exchange', 'token', 'nft', 'web3', 'metaverse', 'staking',
        'yield', 'liquidity', 'volatility', 'inflection', 'pattern', 'analysis'
    }
    
    term_tokens = _tokenize(term)
    implied_tokens = set()
    for imp in implied_by:
        implied_tokens.update(_tokenize(imp))
    
    all_tokens = term_tokens | implied_tokens
    crypto_matches = len(all_tokens & crypto_keywords)
    total_tokens = len(all_tokens)
    
    if total_tokens == 0:
        return 0.0
    
    return min(1.0, crypto_matches / total_tokens)


def stingray_research_methods(topic: str) -> list[str]:
    """Define research methods using Stingray capabilities for a topic."""
    base_methods = [
        "market_data_analysis",
        "alert_creation", 
        "entity_resolution",
        "news_sentiment",
        "technical_indicators",
        "price_tracking"
    ]
    
    topic_methods = []
    if 'inflection' in topic.lower():
        topic_methods.extend([
            "threshold_analysis",
            "drop_detection",
            "momentum_shifts"
        ])
    if 'pattern' in topic.lower():
        topic_methods.extend([
            "historical_comparison",
            "cycle_recognition",
            "repetition_analysis"
        ])
    
    return base_methods + topic_methods


def stingray_data_sources(topic: str) -> list[str]:
    """Define data sources via Stingray for a topic."""
    sources = [
        "coingecko_api",
        "trading_pairs",
        "price_history",
        "news_feeds",
        "social_media",
        "on_chain_data"
    ]
    
    if 'inflection' in topic.lower():
        sources.extend([
            "volume_spike_detection",
            "momentum_indicators",
            "cross_asset_correlation"
        ])
    
    return sources


def identify_market_focus(topic: str) -> str:
    """Identify primary market focus for a research topic."""
    if 'bitcoin' in topic.lower() or 'btc' in topic.lower():
        return "Bitcoin market dynamics"
    elif 'inflection' in topic.lower():
        return "Market turning points"
    elif 'pattern' in topic.lower():
        return "Historical pattern recognition"
    else:
        return "General cryptocurrency research"


def generate_crypto_research_task(region: CryptoResearchRegion) -> dict:
    """Generate a crypto research task using Stingray capabilities."""
    return {
        "topic": region.term,
        "research_goal": f"Analyze {region.term} using Stingray data collection and analysis",
        "methods": region.research_methods,
        "data_sources": region.data_sources,
        "output_format": "manifold_compatible_research",
        "market_focus": region.market_focus,
        "stingray_alert_config": {
            "enabled": True,
            "severity": "medium" if region.strength > 0.5 else "low",
            "components": ["price", "news", "ta"]
        }
    }


def save_crypto_research_regions(regions: list[CryptoResearchRegion], output_path: str):
    """Save crypto research regions for Manifold integration."""
    output_data = {
        "crypto_research_regions": [r.to_manifold_compatible() for r in regions],
        "stingray_capabilities": {
            "alert_creation": True,
            "market_data": True,
            "entity_resolution": True,
            "news_analysis": True,
            "technical_analysis": True
        },
        "integration_timestamp": json.dumps({"created": "2026-04-13"})
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✓ Crypto research regions saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    from core.registry import CapabilityRegistry
    
    # Load current atlas
    atlas_file = Path("/home/zaphod/.openclaw/workspace/data/manifold/stella-atlas.json")
    if atlas_file.exists():
        with open(atlas_file) as f:
            atlas_data = json.load(f)
        
        reg = CapabilityRegistry()
        for agent in atlas_data.get("agents", []):
            reg.update_from_announcement(agent)
        
        atlas = Atlas.build(reg)
        
        # Run crypto reach scan
        crypto_reading = crypto_reach_scan(atlas, top_n=5)
        
        print("🔍 CRYPTO RESEARCH REACH REGIONS")
        print("=" * 40)
        
        for region in crypto_reading.candidate_regions:
            print(f"\n{region.term} (strength: {region.strength:.2f})")
            print(f"  Market focus: {region.market_focus}")
            print(f"  Research methods: {', '.join(region.research_methods)}")
            print(f"  Data sources: {', '.join(region.data_sources)}")
            print(f"  Implied by: {', '.join(region.implied_by)}")
        
        # Save for Manifold integration
        output_file = "/home/zaphod/.openclaw/workspace/crypto_research_regions.json"
        save_crypto_research_regions(crypto_reading.candidate_regions, output_file)
        
        # Generate sample research task
        if crypto_reading.candidate_regions:
            sample_task = generate_crypto_research_task(crypto_reading.candidate_regions[0])
            print(f"\n🎯 Sample research task for Manifold:")
            print(json.dumps(sample_task, indent=2))
    else:
        print("Atlas file not found - cannot run crypto reach scan")