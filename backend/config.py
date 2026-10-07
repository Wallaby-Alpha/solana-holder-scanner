"""
config.py: Global and configurable parameters for Solana Micro-cap Holder Accumulation Research
All thresholds are runtime configurable rather than hardcoded.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

class ScreenerFilterConfig(BaseModel):
    min_market_cap: float = Field(default=25_000.0, description="Minimum market cap in USD")
    max_market_cap: float = Field(default=25_000_000.0, description="Maximum market cap in USD (microcaps)")
    min_liquidity: float = Field(default=10_000.0, description="Minimum liquidity in USD")
    min_volume_24h: float = Field(default=15_000.0, description="Minimum 24h trading volume in USD")
    min_holders: int = Field(default=80, description="Minimum total holders for meaningful statistical sample")
    min_token_age_hours: float = Field(default=12.0, description="Minimum token age in hours")
    max_token_age_days: float = Field(default=180.0, description="Maximum token age in days")
    min_price_change_24h: float = Field(default=-80.0, description="Min 24h price change %")
    max_price_change_24h: float = Field(default=200.0, description="Max 24h price change %")

class AccumulatorConfig(BaseModel):
    # Definition of Persistent Accumulator
    min_purchases: int = Field(default=2, description="Minimum separate buy transactions")
    min_usd_value: float = Field(default=100.0, description="Minimum total USD value accumulated")
    min_pct_increase: float = Field(default=15.0, description="Minimum balance percentage increase")
    max_pct_sold: float = Field(default=20.0, description="Maximum percentage of accumulated tokens subsequently sold")
    min_holding_period_hours: float = Field(default=2.0, description="Minimum duration held between first buy and current")
    
    # Meaningful holder threshold (filters out dust wallets with < $20)
    meaningful_holder_usd: float = Field(default=25.0, description="USD threshold to be considered an active economic holder")

class ScoringWeightsConfig(BaseModel):
    # Holder Accumulation Score weights (sums to 1.0)
    weight_existing_holder_accum: float = 0.25
    weight_persistent_accum_count: float = 0.20
    weight_repeat_buyers: float = 0.15
    weight_accum_to_volume: float = 0.10
    weight_accum_to_supply: float = 0.10
    weight_cohort_retention: float = 0.10
    weight_concentration_improvement: float = 0.05
    weight_cluster_independence: float = 0.05

class AppConfig(BaseModel):
    db_path: str = "data/scanner.db"
    helius_api_key: str = ""
    helius_rpc_url: str = "https://mainnet.helius-rpc.com/?api-key="
    dexscreener_base_url: str = "https://api.dexscreener.com/latest/dex"
    
    # Supported Time Horizons
    horizons: List[str] = ["1h", "6h", "24h", "3d", "7d", "14d", "30d"]
    default_horizon: str = "24h"
    
    screener: ScreenerFilterConfig = ScreenerFilterConfig()
    accumulator: AccumulatorConfig = AccumulatorConfig()
    scoring: ScoringWeightsConfig = ScoringWeightsConfig()

    # Excluded System / Protocol Addresses
    excluded_addresses: Dict[str, str] = {
        # Solana Burn / System
        "11111111111111111111111111111111": "SOLANA_SYSTEM_PROGRAM",
        "deaddeaddeaddeaddeaddeaddeaddeaddeaddeaddead": "BURN_ADDRESS",
        "1nc1nerator11111111111111111111111111111111": "INCINERATOR_BURN",
        # Known DEXes & Programs
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "RAYDIUM_AMM_V4",
        "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": "RAYDIUM_CLMM",
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "ORCA_WHIRLPOOL",
        "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "METEORA_DLMM",
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "PUMP_FUN_BONDING_CURVE_PROGRAM",
        "Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1": "RAYDIUM_AUTHORITY",
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL_TOKEN_PROGRAM",
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "SPL_ASSOCIATED_TOKEN_PROGRAM",
    }

GLOBAL_CONFIG = AppConfig()
