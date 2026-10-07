"""
dexscreener.py: DexScreener API integration with caching and rate-limiting protection.
Used for price discovery, liquidity, 24h volume, FDV, pair age, and buy/sell activity.
"""

import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

class DexScreenerProvider:
    def __init__(self, base_url: str = "https://api.dexscreener.com/latest/dex", cache_ttl_seconds: int = 60):
        self.base_url = base_url
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.cache_ttl:
                return val
        return None

    def _set_cached(self, key: str, val: Any):
        self._cache[key] = (time.time(), val)

    async def fetch_token_pairs(self, mint_address: str) -> List[Dict[str, Any]]:
        cache_key = f"token_pairs_{mint_address}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        client = await self.get_client()
        url = f"{self.base_url}/tokens/{mint_address}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", []) or []
                # Filter for Solana pairs only
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                self._set_cached(cache_key, sol_pairs)
                return sol_pairs
        except Exception as e:
            print(f"[DexScreener] Error fetching pairs for {mint_address}: {e}")
        return []

    async def search_solana_pairs(self, query: str = "SOL") -> List[Dict[str, Any]]:
        cache_key = f"search_{query}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        client = await self.get_client()
        url = f"{self.base_url}/search?q={query}"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                pairs = data.get("pairs", []) or []
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                self._set_cached(cache_key, sol_pairs)
                return sol_pairs
        except Exception as e:
            print(f"[DexScreener] Error searching {query}: {e}")
        return []

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
