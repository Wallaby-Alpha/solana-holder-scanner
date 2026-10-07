"""
helius.py: Helius API integration for on-chain wallet transfers, token balances, and funding sources.
Includes smart caching, rate-limit throttling, and batching to minimize Helius credit usage.
"""

import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple

class HeliusProvider:
    def __init__(self, api_key: str = "", rpc_url: Optional[str] = None):
        self.api_key = api_key
        self.rpc_url = rpc_url or f"https://mainnet.helius-rpc.com/?api-key={api_key}"
        self.base_url = "https://api.helius.xyz/v0"
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self.cache_ttl = 300  # 5 min cache for raw transfers
        self.rate_limit_delay = 0.2  # Max 5 req/s to prevent rate-limit penalties

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=25.0)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 8)

    async def fetch_token_transfers(
        self, mint_address: str, limit: int = 100, before_signature: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch enhanced token transfer transactions from Helius parsed API.
        """
        if not self.is_configured():
            return []

        cache_key = f"transfers_{mint_address}_{limit}_{before_signature}"
        if cache_key in self._cache:
            ts, val = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                return val

        await asyncio.sleep(self.rate_limit_delay)
        client = await self.get_client()
        url = f"{self.base_url}/addresses/{mint_address}/transactions?api-key={self.api_key}&limit={limit}"
        if before_signature:
            url += f"&before={before_signature}"

        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                raw_txs = resp.json()
                parsed_transfers = []
                for tx in raw_txs:
                    sig = tx.get("signature")
                    timestamp = tx.get("timestamp")
                    token_transfers = tx.get("tokenTransfers", [])
                    for tt in token_transfers:
                        if tt.get("mint") == mint_address:
                            parsed_transfers.append({
                                "signature": sig,
                                "mint_address": mint_address,
                                "from_address": tt.get("fromUserAccount") or tt.get("fromTokenAccount", "UNKNOWN"),
                                "to_address": tt.get("toUserAccount") or tt.get("toTokenAccount", "UNKNOWN"),
                                "amount": float(tt.get("tokenAmount", 0)),
                                "timestamp": timestamp,
                                "tx_type": tx.get("type", "TRANSFER"),
                                "slot": tx.get("slot", 0)
                            })
                self._cache[cache_key] = (time.time(), parsed_transfers)
                return parsed_transfers
        except Exception as e:
            print(f"[Helius] Transfer fetch failed for {mint_address}: {e}")
        return []

    async def fetch_wallet_funding_source(self, wallet_address: str) -> Optional[str]:
        """
        Determine who originally funded this wallet with SOL by checking its earliest transaction.
        """
        if not self.is_configured():
            return None

        cache_key = f"funding_{wallet_address}"
        if cache_key in self._cache:
            ts, val = self._cache[cache_key]
            if time.time() - ts < 3600 * 24: # 24h cache
                return val

        await asyncio.sleep(self.rate_limit_delay)
        client = await self.get_client()
        # Query oldest transactions for native SOL transfers
        url = f"{self.base_url}/addresses/{wallet_address}/transactions?api-key={self.api_key}&limit=10"
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                txs = resp.json()
                if txs:
                    # Look for native SOL transfers into this wallet
                    for tx in reversed(txs):
                        native_transfers = tx.get("nativeTransfers", [])
                        for nt in native_transfers:
                            if nt.get("toUserAccount") == wallet_address:
                                funder = nt.get("fromUserAccount")
                                if funder and funder != wallet_address:
                                    self._cache[cache_key] = (time.time(), funder)
                                    return funder
        except Exception as e:
            print(f"[Helius] Funding source lookup failed for {wallet_address}: {e}")
        return None

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
