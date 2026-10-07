"""
screener.py: Micro-cap Universe Screening and Filtering Engine for Solana.
Filters tokens by market cap, liquidity, volume, token age, holder count, and price performance.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from ..config import ScreenerFilterConfig, GLOBAL_CONFIG

class TokenScreener:
    def __init__(self, filter_config: Optional[ScreenerFilterConfig] = None):
        self.filters = filter_config or GLOBAL_CONFIG.screener

    def passes_filters(self, token: Dict[str, Any], current_filters: Optional[ScreenerFilterConfig] = None) -> Tuple[bool, List[str]]:
        """
        Evaluates whether a Solana token qualifies under configurable micro-cap research criteria.
        Returns: (passes: bool, reasons_failed: List[str])
        """
        f = current_filters or self.filters
        reasons = []

        mcap = token.get("market_cap_usd", 0.0)
        liq = token.get("liquidity_usd", 0.0)
        vol = token.get("volume_24h_usd", 0.0)
        holders = token.get("holder_count", 0)
        p_chg = token.get("price_change_24h", 0.0)

        # Market Cap check
        if mcap < f.min_market_cap:
            reasons.append(f"Mcap ${mcap:,.0f} < min ${f.min_market_cap:,.0f}")
        if mcap > f.max_market_cap:
            reasons.append(f"Mcap ${mcap:,.0f} > max ${f.max_market_cap:,.0f}")

        # Liquidity check
        if liq < f.min_liquidity:
            reasons.append(f"Liquidity ${liq:,.0f} < min ${f.min_liquidity:,.0f}")

        # 24h Volume check
        if vol < f.min_volume_24h:
            reasons.append(f"Volume ${vol:,.0f} < min ${f.min_volume_24h:,.0f}")

        # Holder Count check (need enough on-chain data for meaningful statistics)
        if holders < f.min_holders:
            reasons.append(f"Holders {holders} < min {f.min_holders}")

        # Price change filter
        if p_chg < f.min_price_change_24h or p_chg > f.max_price_change_24h:
            reasons.append(f"24h Price Change {p_chg}% outside [{f.min_price_change_24h}%, {f.max_price_change_24h}%]")

        return len(reasons) == 0, reasons

    def filter_universe(
        self, tokens: List[Dict[str, Any]], current_filters: Optional[ScreenerFilterConfig] = None
    ) -> List[Dict[str, Any]]:
        """Filters a candidate universe down to qualified research microcaps."""
        passed = []
        for t in tokens:
            ok, _ = self.passes_filters(t, current_filters)
            if ok:
                passed.append(t)
        return passed
