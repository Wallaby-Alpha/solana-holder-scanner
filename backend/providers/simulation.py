"""
simulation.py: High-fidelity Solana Micro-cap Simulator and On-Chain Seed Engine.
Generates realistic wallet histories, LP exclusions, multi-buy persistent accumulation patterns,
cohorts, Sybil clusters, and multi-horizon price series for quantitative research.
"""

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import math

class SimulationProvider:
    def __init__(self):
        # Deterministic seed for reproducible backtesting and analysis
        self.rng = random.Random(42)

    def generate_solana_address(self, prefix: str = "") -> str:
        chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        rand_part = "".join(self.rng.choice(chars) for _ in range(40 - len(prefix)))
        return f"{prefix}{rand_part}"

    def get_seed_tokens(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        
        # 12 carefully structured Solana micro-cap tokens covering distinct research regimes
        tokens = [
            {
                "mint_address": "8PnGzB3QjE9K1mUrtV7GgPoxLz5V3Dq7Wb9YxLm4pump",
                "symbol": "CHILLGUY",
                "name": "Just a Chill Guy",
                "category": "MEME",
                "decimals": 6,
                "total_supply": 1_000_000_000,
                "circulating_supply": 950_000_000,
                "created_at": (now - timedelta(days=22)).isoformat(),
                "market_cap_usd": 1_850_000.0,
                "liquidity_usd": 240_000.0,
                "current_price_usd": 0.001947,
                "volume_24h_usd": 420_000.0,
                "price_change_24h": -14.2,
                "holder_count": 1420,
                "regime": "BULLISH_ACCUMULATION", # Declining price, but heavy existing holder accumulation
            },
            {
                "mint_address": "HeLp7V4eK9LmZtN2QxP8Wj3Uo5Yd1Gb6Rs9Ac8Kypump",
                "symbol": "SWARMS",
                "name": "Autonomous Swarm Protocol",
                "category": "UTILITY",
                "decimals": 6,
                "total_supply": 100_000_000,
                "circulating_supply": 88_000_000,
                "created_at": (now - timedelta(days=45)).isoformat(),
                "market_cap_usd": 3_420_000.0,
                "liquidity_usd": 380_000.0,
                "current_price_usd": 0.03886,
                "volume_24h_usd": 580_000.0,
                "price_change_24h": -2.4,
                "holder_count": 2180,
                "regime": "BREAKOUT_CONSOLIDATION", # Base consolidation, repeat buyers, healthy concentration
            },
            {
                "mint_address": "9K3mP8xR7L1qW2eY5Uo4Ij6Tz9Ac1Vb3Df5Gs8Hnpump",
                "symbol": "DEGENAI",
                "name": "Degen Agent Engine",
                "category": "AI_UTILITY",
                "decimals": 6,
                "total_supply": 500_000_000,
                "circulating_supply": 490_000_000,
                "created_at": (now - timedelta(days=12)).isoformat(),
                "market_cap_usd": 740_000.0,
                "liquidity_usd": 115_000.0,
                "current_price_usd": 0.00151,
                "volume_24h_usd": 195_000.0,
                "price_change_24h": -28.5,
                "holder_count": 860,
                "regime": "DISTRIBUTION", # Distribution candidate: existing holders leaving while price dumps
            },
            {
                "mint_address": "4Bq7V3Lm9K1oP2eR8Uo5Ij7Tz9Ac1Wb4Yx5Gs8Hmpump",
                "symbol": "FARMER",
                "name": "Solana Yield Farmer Club",
                "category": "COMMUNITY",
                "decimals": 6,
                "total_supply": 1_000_000_000,
                "circulating_supply": 920_000_000,
                "created_at": (now - timedelta(days=8)).isoformat(),
                "market_cap_usd": 380_000.0,
                "liquidity_usd": 68_000.0,
                "current_price_usd": 0.000413,
                "volume_24h_usd": 88_000.0,
                "price_change_24h": 4.2,
                "holder_count": 490,
                "regime": "CLUSTERED_SYBIL", # Sybil bot farm: many wallets funded by same wallet
            },
            {
                "mint_address": "2V8jL1mP9K3qW4eR7Uo5Ij6Tz9Ac1Wb3Df5Gs8Kopump",
                "symbol": "MEMETRON",
                "name": "Neural Memetics",
                "category": "MEME",
                "decimals": 6,
                "total_supply": 1_000_000_000,
                "circulating_supply": 980_000_000,
                "created_at": (now - timedelta(days=65)).isoformat(),
                "market_cap_usd": 5_850_000.0,
                "liquidity_usd": 620_000.0,
                "current_price_usd": 0.00597,
                "volume_24h_usd": 920_000.0,
                "price_change_24h": -8.1,
                "holder_count": 3410,
                "regime": "BULLISH_ACCUMULATION", # Established microcap consolidating, high persistent buyers
            },
            {
                "mint_address": "7Y3mL1qP9K2eR4Uo5Ij6Tz8Ac1Wb3Df5Gs8Hj1pump",
                "symbol": "SOLCHATX",
                "name": "Encrypted P2P Comms",
                "category": "UTILITY",
                "decimals": 6,
                "total_supply": 10_000_000,
                "circulating_supply": 9_100_000,
                "created_at": (now - timedelta(days=110)).isoformat(),
                "market_cap_usd": 8_900_000.0,
                "liquidity_usd": 890_000.0,
                "current_price_usd": 0.978,
                "volume_24h_usd": 1_250_000.0,
                "price_change_24h": 1.5,
                "holder_count": 4890,
                "regime": "BREAKOUT_CONSOLIDATION",
            },
            {
                "mint_address": "5Kp8V1mQ3L2eR7Uo4Ij9Tz1Ac6Wb4Df2Gs8Hk9pump",
                "symbol": "GIGACHAD",
                "name": "Giga Solana Culture",
                "category": "MEME",
                "decimals": 6,
                "total_supply": 1_000_000_000,
                "circulating_supply": 960_000_000,
                "created_at": (now - timedelta(days=90)).isoformat(),
                "market_cap_usd": 14_200_000.0,
                "liquidity_usd": 1_450_000.0,
                "current_price_usd": 0.01479,
                "volume_24h_usd": 2_100_000.0,
                "price_change_24h": -11.4,
                "holder_count": 8200,
                "regime": "BULLISH_ACCUMULATION",
            },
            {
                "mint_address": "3Rq8L2mP7K1eW5Uo4Ij6Tz9Ac1Vb3Df5Gs8Hp2pump",
                "symbol": "MOONDROP",
                "name": "Moon Airdrop DAO",
                "category": "COMMUNITY",
                "decimals": 6,
                "total_supply": 100_000_000,
                "circulating_supply": 75_000_000,
                "created_at": (now - timedelta(days=5)).isoformat(),
                "market_cap_usd": 185_000.0,
                "liquidity_usd": 32_000.0,
                "current_price_usd": 0.00246,
                "volume_24h_usd": 48_000.0,
                "price_change_24h": -35.2,
                "holder_count": 280,
                "regime": "DISTRIBUTION",
            },
            {
                "mint_address": "6Nm9P2kL1eR4Uo7Ij5Tz8Ac3Wb1Df4Gs9Hq3pump",
                "symbol": "SOLVIBE",
                "name": "Solana Vibe Terminal",
                "category": "UTILITY",
                "decimals": 6,
                "total_supply": 100_000_000,
                "circulating_supply": 95_000_000,
                "created_at": (now - timedelta(days=19)).isoformat(),
                "market_cap_usd": 1_120_000.0,
                "liquidity_usd": 160_000.0,
                "current_price_usd": 0.01179,
                "volume_24h_usd": 210_000.0,
                "price_change_24h": -0.8,
                "holder_count": 1150,
                "regime": "NEUTRAL",
            },
            {
                "mint_address": "1Wq7P3mL8K2eR5Uo9Ij4Tz1Ac6Vb2Df8Gs3Hp4pump",
                "symbol": "COINFLIP",
                "name": "On-Chain Gaming Protocol",
                "category": "UTILITY",
                "decimals": 6,
                "total_supply": 500_000_000,
                "circulating_supply": 480_000_000,
                "created_at": (now - timedelta(days=32)).isoformat(),
                "market_cap_usd": 2_450_000.0,
                "liquidity_usd": 290_000.0,
                "current_price_usd": 0.00510,
                "volume_24h_usd": 380_000.0,
                "price_change_24h": 8.7,
                "holder_count": 1820,
                "regime": "NEUTRAL",
            },
            {
                "mint_address": "4Zk9M2qP7L1eW3Uo8Ij5Tz6Ac2Vb4Df1Gs9Hr5pump",
                "symbol": "POODLE",
                "name": "Poodle Coin Solana",
                "category": "MEME",
                "decimals": 6,
                "total_supply": 1_000_000_000,
                "circulating_supply": 990_000_000,
                "created_at": (now - timedelta(days=14)).isoformat(),
                "market_cap_usd": 510_000.0,
                "liquidity_usd": 75_000.0,
                "current_price_usd": 0.000515,
                "volume_24h_usd": 94_000.0,
                "price_change_24h": -19.4,
                "holder_count": 620,
                "regime": "BULLISH_ACCUMULATION",
            },
            {
                "mint_address": "9Lk4Q1mP8K3eR2Uo7Ij6Tz5Ac1Wb9Df3Gs2Hq6pump",
                "symbol": "SOLSHIELD",
                "name": "Privacy Shield Protocol",
                "category": "UTILITY",
                "decimals": 6,
                "total_supply": 100_000_000,
                "circulating_supply": 85_000_000,
                "created_at": (now - timedelta(days=70)).isoformat(),
                "market_cap_usd": 6_100_000.0,
                "liquidity_usd": 710_000.0,
                "current_price_usd": 0.07176,
                "volume_24h_usd": 890_000.0,
                "price_change_24h": -4.6,
                "holder_count": 3950,
                "regime": "BREAKOUT_CONSOLIDATION",
            }
        ]
        return tokens

    def generate_token_transfers_and_wallets(
        self, token: Dict[str, Any], count: int = 120
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        Generate on-chain transactions, dynamic wallet states, funding clusters, and LP exclusions.
        """
        mint = token["mint_address"]
        price = token["current_price_usd"]
        regime = token.get("regime", "NEUTRAL")
        now = datetime.now(timezone.utc)

        # 1. Non-economic system wallets (LP pools, burn, router)
        lp_wallet = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8" # Raydium
        burn_wallet = "1nc1nerator11111111111111111111111111111111"
        deployer_wallet = self.generate_solana_address("DEP_")

        wallets_list = [
            {"address": lp_wallet, "first_seen_at": (now - timedelta(days=30)).isoformat(), "funding_wallet": None, "is_excluded": 1, "classification_reason": "RAYDIUM_AMM_POOL", "last_active_at": now.isoformat()},
            {"address": burn_wallet, "first_seen_at": (now - timedelta(days=30)).isoformat(), "funding_wallet": None, "is_excluded": 1, "classification_reason": "BURN_ADDRESS", "last_active_at": now.isoformat()},
            {"address": deployer_wallet, "first_seen_at": (now - timedelta(days=30)).isoformat(), "funding_wallet": None, "is_excluded": 1, "classification_reason": "DEPLOYER_AUTHORITY", "last_active_at": now.isoformat()},
        ]

        # 2. Generate regular trading wallets
        user_wallets = []
        clusters_map = {} # funder_wallet -> list of member wallets

        # Common funder for Sybil cluster testing
        sybil_funder = self.generate_solana_address("FUND_")
        sybil_members = []

        num_wallets = 45
        for i in range(num_wallets):
            addr = self.generate_solana_address(f"W{i:02d}_")
            created_days_ago = self.rng.uniform(1.0, 35.0)
            wallet_created = now - timedelta(days=created_days_ago)
            
            # If regime is CLUSTERED_SYBIL or 15% random chance, group wallets under common funder
            is_sybil = (regime == "CLUSTERED_SYBIL" and i < 15) or (i >= 38 and i < 42)
            if is_sybil:
                funding_w = sybil_funder
                sybil_members.append(addr)
            else:
                funding_w = self.generate_solana_address("FND_") if self.rng.random() < 0.25 else None

            user_wallets.append(addr)
            wallets_list.append({
                "address": addr,
                "first_seen_at": wallet_created.isoformat(),
                "funding_wallet": funding_w,
                "is_excluded": 0,
                "classification_reason": None,
                "last_active_at": now.isoformat()
            })

        if sybil_members:
            clusters_map[sybil_funder] = sybil_members

        # 3. Generate transfers time series reflecting the token regime
        transfers = []
        balances_records = []
        wallet_balances: Dict[str, float] = {w: 0.0 for w in user_wallets}

        # Seed initial balances
        for w in user_wallets:
            init_tokens = self.rng.uniform(10_000, 500_000)
            wallet_balances[w] = init_tokens
            balances_records.append({
                "wallet_address": w,
                "mint_address": mint,
                "timestamp": (now - timedelta(days=14)).isoformat(),
                "balance": init_tokens,
                "usd_value": init_tokens * price * 1.1
            })

        # Generate sequential transfers over past 7 days
        steps = count
        time_spread = 7 * 24 * 3600 # 7 days in seconds
        start_time = now - timedelta(days=7)

        # Regimes dictate who buys and how persistently:
        # BULLISH_ACCUMULATION: existing holders make 3-6 repeated purchases, minimal sells!
        # DISTRIBUTION: large existing holders dump repeatedly to new entrant wallets
        # BREAKOUT_CONSOLIDATION: steady accumulation across multiple independent wallets
        # CLUSTERED_SYBIL: sybil wallets execute synchronized buys
        
        for step in range(steps):
            step_time = start_time + timedelta(seconds=(step / steps) * time_spread + self.rng.uniform(-300, 300))
            if step_time > now:
                step_time = now

            if regime in ["BULLISH_ACCUMULATION", "BREAKOUT_CONSOLIDATION"]:
                # 70% buys from existing holders, repeated purchases
                is_buy = self.rng.random() < 0.75
                # Pick an existing wallet
                wallet = self.rng.choice(user_wallets[:20]) # Top 20 active accumulators
            elif regime == "DISTRIBUTION":
                # 65% sells by existing large holders, small buys by new wallets
                is_buy = self.rng.random() < 0.35
                wallet = self.rng.choice(user_wallets[:10]) # Whales selling
            elif regime == "CLUSTERED_SYBIL":
                is_buy = True
                wallet = self.rng.choice(sybil_members) if sybil_members and self.rng.random() < 0.65 else self.rng.choice(user_wallets)
            else:
                is_buy = self.rng.random() < 0.52
                wallet = self.rng.choice(user_wallets)

            amount_usd = self.rng.uniform(80.0, 3500.0)
            amount_tokens = amount_usd / max(price, 0.000001)

            if is_buy:
                from_addr = lp_wallet
                to_addr = wallet
                tx_type = "BUY"
                wallet_balances[wallet] = wallet_balances.get(wallet, 0.0) + amount_tokens
            else:
                from_addr = wallet
                to_addr = lp_wallet
                tx_type = "SELL"
                current_bal = wallet_balances.get(wallet, 0.0)
                amount_tokens = min(amount_tokens, current_bal * 0.5) # Sell part or all
                wallet_balances[wallet] = max(0.0, current_bal - amount_tokens)

            sig = f"sig_{mint[:6]}_{step}_{self.rng.randint(100000, 999999)}"
            transfers.append({
                "signature": sig,
                "mint_address": mint,
                "from_address": from_addr,
                "to_address": to_addr,
                "amount": amount_tokens,
                "usd_value": amount_usd,
                "timestamp": step_time.isoformat(),
                "tx_type": tx_type,
                "slot": 290000000 + step
            })

            # Record periodic balance point
            if step % 3 == 0:
                balances_records.append({
                    "wallet_address": wallet,
                    "mint_address": mint,
                    "timestamp": step_time.isoformat(),
                    "balance": wallet_balances[wallet],
                    "usd_value": wallet_balances[wallet] * price
                })

        # Add latest balance record for all wallets
        for w, bal in wallet_balances.items():
            balances_records.append({
                "wallet_address": w,
                "mint_address": mint,
                "timestamp": now.isoformat(),
                "balance": bal,
                "usd_value": bal * price
            })

        return wallets_list, transfers, balances_records, clusters_map

    def generate_price_history(self, token: Dict[str, Any], hours_back: int = 168) -> List[Dict[str, Any]]:
        """
        Generate hourly price and liquidity snapshots.
        """
        snapshots = []
        now = datetime.now(timezone.utc)
        current_price = token["current_price_usd"]
        regime = token.get("regime", "NEUTRAL")

        # Reconstruct path backwards
        price = current_price
        for h in range(hours_back):
            ts = now - timedelta(hours=h)
            
            # Volatility drift
            drift = 0.0
            if regime == "BULLISH_ACCUMULATION":
                # Currently consolidating or down over past 24h
                drift = 0.001 if h > 24 else -0.004
            elif regime == "DISTRIBUTION":
                drift = -0.005
            elif regime == "BREAKOUT_CONSOLIDATION":
                drift = 0.0005
            
            noise = self.rng.gauss(0, 0.015)
            past_price = price / (1.0 + drift + noise)
            past_price = max(0.0000001, past_price)

            snapshots.append({
                "mint_address": token["mint_address"],
                "timestamp": ts.isoformat(),
                "price_usd": price,
                "market_cap_usd": price * token["circulating_supply"],
                "liquidity_usd": token["liquidity_usd"] * (price / current_price),
                "volume_usd": token["volume_24h_usd"] * (1.0 + self.rng.uniform(-0.3, 0.3)),
                "holder_count": int(token["holder_count"] * (1.0 - (h * 0.001))),
                "top_10_concentration": 0.42 + (0.05 if regime == "DISTRIBUTION" else -0.03)
            })
            price = past_price

        snapshots.reverse()
        return snapshots
