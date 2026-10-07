"""
base.py: Abstract Base Data Provider for Solana market and on-chain intelligence.
Enables pluggable data sources (Helius, DexScreener, Birdeye, Shyft, RPC, Simulator).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseDataProvider(ABC):
    @abstractmethod
    async def fetch_screener_tokens(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Screen universe of Solana tokens based on market filters."""
        pass

    @abstractmethod
    async def fetch_token_market_data(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Fetch current price, volume, liquidity, and pair details."""
        pass

    @abstractmethod
    async def fetch_token_transfers(
        self, mint_address: str, limit: int = 250, before_signature: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical SPL token transfers with sender, receiver, amount, timestamp."""
        pass

    @abstractmethod
    async def fetch_token_holders_snapshot(self, mint_address: str) -> List[Dict[str, Any]]:
        """Fetch list of current token holders and balances."""
        pass

    @abstractmethod
    async def fetch_wallet_funding_source(self, wallet_address: str) -> Optional[str]:
        """Trace the primary SOL funding wallet for clustering analysis."""
        pass
