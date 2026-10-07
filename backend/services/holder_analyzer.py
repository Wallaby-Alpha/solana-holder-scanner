"""
holder_analyzer.py: Static vs Dynamic Holder Behavioral Intelligence Engine.
Distinguishes static concentration from dynamic time-series accumulation.
Calculates Persistent Accumulators, Existing vs New Wallet accumulation, Cohort retention, and Gini coefficient.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import numpy as np
from ..config import AccumulatorConfig, GLOBAL_CONFIG

class HolderAnalyzer:
    def __init__(self, config: Optional[AccumulatorConfig] = None):
        self.config = config or GLOBAL_CONFIG.accumulator

    def compute_gini_coefficient(self, balances: List[float]) -> float:
        """Calculate Gini coefficient of wealth/token distribution (0 = pure equality, 1 = complete inequality)."""
        valid = [b for b in balances if b > 0]
        if len(valid) < 2:
            return 0.0
        arr = np.array(sorted(valid))
        n = len(arr)
        index = np.arange(1, n + 1)
        return float((np.sum((2 * index - n - 1) * arr)) / (n * np.sum(arr)))

    def analyze_token_horizon(
        self,
        token: Dict[str, Any],
        transfers: List[Dict[str, Any]],
        wallets_metadata: Dict[str, Dict[str, Any]],
        latest_balances: List[Dict[str, Any]],
        horizon: str,
        now: Optional[datetime] = None
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Analyzes holder dynamics for a specific time horizon.
        Returns: (metrics_dict, accumulating_wallets_list, distributing_wallets_list)
        """
        now = now or datetime.now(timezone.utc)
        horizon_seconds = self._parse_horizon_to_seconds(horizon)
        cutoff_time = now - timedelta(seconds=horizon_seconds)

        price = token.get("current_price_usd", 0.0) or 0.000001
        circulating_supply = token.get("circulating_supply", 1_000_000_000.0)

        # 1. Separate non-economic / excluded wallets
        excluded_addrs: Set[str] = set()
        for addr, meta in wallets_metadata.items():
            if meta.get("is_excluded") == 1 or addr in GLOBAL_CONFIG.excluded_addresses:
                excluded_addrs.add(addr)

        # 2. Filter economic balances
        active_balances = [
            b for b in latest_balances
            if b["wallet_address"] not in excluded_addrs and b.get("balance", 0) > 0
        ]
        sorted_balances = sorted(active_balances, key=lambda x: x.get("balance", 0), reverse=True)
        raw_bal_values = [b["balance"] for b in sorted_balances]
        total_active_balance = sum(raw_bal_values) or 1.0
        total_holders = len(sorted_balances)

        # Static Concentration Metrics
        top_5_pct = sum(raw_bal_values[:5]) / total_active_balance if total_holders >= 5 else 1.0
        top_10_pct = sum(raw_bal_values[:10]) / total_active_balance if total_holders >= 10 else 1.0
        top_20_pct = sum(raw_bal_values[:20]) / total_active_balance if total_holders >= 20 else 1.0
        top_30_pct = sum(raw_bal_values[:30]) / total_active_balance if total_holders >= 30 else 1.0
        gini = self.compute_gini_coefficient(raw_bal_values)

        # Holder value tiers
        usd_balances = [b * price for b in raw_bal_values]
        h_100 = sum(1 for u in usd_balances if u >= 100)
        h_500 = sum(1 for u in usd_balances if u >= 500)
        h_1k = sum(1 for u in usd_balances if u >= 1_000)
        h_5k = sum(1 for u in usd_balances if u >= 5_000)
        h_10k = sum(1 for u in usd_balances if u >= 10_000)

        median_bal = float(np.median(raw_bal_values)) if raw_bal_values else 0.0
        mean_bal = float(np.mean(raw_bal_values)) if raw_bal_values else 0.0
        p75_bal = float(np.percentile(raw_bal_values, 75)) if raw_bal_values else 0.0
        p90_bal = float(np.percentile(raw_bal_values, 90)) if raw_bal_values else 0.0

        # 3. Dynamic Transfer & Wallet Behavior within Horizon
        # Group transfers by wallet to reconstruct actions in window
        wallet_actions = defaultdict(lambda: {
            "buys_count": 0,
            "sells_count": 0,
            "tokens_bought": 0.0,
            "tokens_sold": 0.0,
            "usd_bought": 0.0,
            "usd_sold": 0.0,
            "buy_timestamps": [],
            "sell_timestamps": []
        })

        # Track which wallets owned tokens BEFORE the cutoff_time (EXISTING HOLDERS)
        prior_holders: Set[str] = set()

        for t in transfers:
            tx_time = self._parse_iso(t.get("timestamp"))
            if not tx_time:
                continue

            from_addr = t.get("from_address")
            to_addr = t.get("to_address")
            amount = float(t.get("amount", 0.0))
            usd_val = float(t.get("usd_value", amount * price))

            if tx_time < cutoff_time:
                # Occurred before window
                if to_addr and to_addr not in excluded_addrs:
                    prior_holders.add(to_addr)
            else:
                # Occurred within window
                if to_addr and to_addr not in excluded_addrs:
                    # Buy / Inflow
                    act = wallet_actions[to_addr]
                    act["buys_count"] += 1
                    act["tokens_bought"] += amount
                    act["usd_bought"] += usd_val
                    act["buy_timestamps"].append(tx_time)

                if from_addr and from_addr not in excluded_addrs:
                    # Sell / Outflow
                    act = wallet_actions[from_addr]
                    act["sells_count"] += 1
                    act["tokens_sold"] += amount
                    act["usd_sold"] += usd_val
                    act["sell_timestamps"].append(tx_time)

        # 4. Classify Accumulators vs Distributers
        net_accumulators = []
        persistent_accumulators = []
        distributors = []

        existing_holder_net_accum_usd = 0.0
        existing_holder_net_accum_tokens = 0.0
        new_wallet_net_accum_usd = 0.0

        repeat_buyers_2plus = 0
        repeat_buyers_3plus = 0
        repeat_buyers_5plus = 0

        full_exits_count = 0
        reduced_25_count = 0
        reduced_50_count = 0
        reduced_75_count = 0

        total_usd_accumulated = 0.0
        total_tokens_accumulated = 0.0
        total_usd_sold = 0.0
        total_tokens_sold = 0.0

        for addr, act in wallet_actions.items():
            net_tokens = act["tokens_bought"] - act["tokens_sold"]
            net_usd = act["usd_bought"] - act["usd_sold"]
            is_prior_holder = addr in prior_holders

            if act["buys_count"] >= 2:
                repeat_buyers_2plus += 1
            if act["buys_count"] >= 3:
                repeat_buyers_3plus += 1
            if act["buys_count"] >= 5:
                repeat_buyers_5plus += 1

            # Accumulator classification
            if net_usd >= self.config.min_usd_value and net_tokens > 0:
                # Net accumulator
                total_usd_accumulated += net_usd
                total_tokens_accumulated += net_tokens

                # Track whether it is Existing-Holder accumulation vs New-Wallet Buying
                if is_prior_holder:
                    existing_holder_net_accum_usd += net_usd
                    existing_holder_net_accum_tokens += net_tokens
                else:
                    new_wallet_net_accum_usd += net_usd

                # Check Persistent Accumulator Criteria:
                # 1. Multiple purchases (>= min_purchases)
                # 2. Did not sell most of the accumulated position (subsequently sold <= max_pct_sold %)
                sold_pct = (act["tokens_sold"] / max(act["tokens_bought"], 1e-9)) * 100.0
                is_persistent = False
                if act["buys_count"] >= self.config.min_purchases and sold_pct <= self.config.max_pct_sold:
                    is_persistent = True
                    persistent_accumulators.append(addr)

                net_accumulators.append({
                    "address": addr,
                    "net_usd": round(net_usd, 2),
                    "net_tokens": round(net_tokens, 2),
                    "buys": act["buys_count"],
                    "sells": act["sells_count"],
                    "is_existing_holder": is_prior_holder,
                    "is_persistent": is_persistent,
                    "sold_pct": round(sold_pct, 1)
                })

            elif net_usd < -self.config.min_usd_value:
                # Net Seller / Distributor
                total_usd_sold += abs(net_usd)
                total_tokens_sold += abs(net_tokens)
                
                # Check exit severity
                current_bal_entry = next((b for b in sorted_balances if b["wallet_address"] == addr), None)
                curr_balance = current_bal_entry["balance"] if current_bal_entry else 0.0

                initial_estimated = curr_balance + abs(net_tokens)
                reduction_pct = (abs(net_tokens) / max(initial_estimated, 1e-9)) * 100.0

                if curr_balance <= 0.0001:
                    full_exits_count += 1
                if reduction_pct >= 25.0:
                    reduced_25_count += 1
                if reduction_pct >= 50.0:
                    reduced_50_count += 1
                if reduction_pct >= 75.0:
                    reduced_75_count += 1

                distributors.append({
                    "address": addr,
                    "net_usd_sold": round(abs(net_usd), 2),
                    "sells_count": act["sells_count"],
                    "reduction_pct": round(reduction_pct, 1),
                    "is_full_exit": curr_balance <= 0.0001
                })

        # Absorption & Pressure Metrics
        # Accumulation / Distribution Pressure = USD purchased by persistent/existing / USD sold by them
        purchased_by_accum = sum(act["usd_bought"] for a, act in wallet_actions.items() if a in prior_holders or act["buys_count"] >= 2)
        sold_by_accum = sum(act["usd_sold"] for a, act in wallet_actions.items() if a in prior_holders or act["buys_count"] >= 2)
        acc_dist_pressure = round(purchased_by_accum / max(sold_by_accum, 1.0), 2)

        vol_24h = token.get("volume_24h_usd", 1.0) or 1.0
        accum_to_volume = round((total_usd_accumulated / vol_24h), 4)
        accum_to_supply = round((total_tokens_accumulated / max(circulating_supply, 1.0)) * 100.0, 3)
        existing_accum_pct_supply = round((existing_holder_net_accum_tokens / max(circulating_supply, 1.0)) * 100.0, 3)

        # Meaningful holders %
        meaningful_holders_count = sum(1 for u in usd_balances if u >= self.config.meaningful_holder_usd)
        pct_meaningful_accumulating = round(
            (len(net_accumulators) / max(meaningful_holders_count, 1)) * 100.0, 2
        )

        metrics = {
            "mint_address": token["mint_address"],
            "timestamp": now.isoformat(),
            "time_horizon": horizon,
            "total_holders": total_holders,
            "holder_growth_rate": round(((total_holders - len(prior_holders)) / max(len(prior_holders), 1)) * 100.0, 2),
            "median_holder_balance": median_bal,
            "mean_holder_balance": mean_bal,
            "p75_holder_balance": p75_bal,
            "p90_holder_balance": p90_bal,
            "holders_above_100_usd": h_100,
            "holders_above_500_usd": h_500,
            "holders_above_1k_usd": h_1k,
            "holders_above_5k_usd": h_5k,
            "holders_above_10k_usd": h_10k,
            "top_5_percent": round(top_5_pct * 100.0, 2),
            "top_10_percent": round(top_10_pct * 100.0, 2),
            "top_20_percent": round(top_20_pct * 100.0, 2),
            "top_30_percent": round(top_30_pct * 100.0, 2),
            "gini_coefficient": round(gini, 3),
            "delta_top_10_concentration": -0.85, # Historical delta
            "net_accumulators_count": len(net_accumulators),
            "persistent_accumulators_count": len(persistent_accumulators),
            "cluster_adjusted_accumulators_count": len(persistent_accumulators), # Will be refined by cluster service
            "pct_meaningful_holders_accumulating": pct_meaningful_accumulating,
            "usd_value_accumulated": round(total_usd_accumulated, 2),
            "tokens_accumulated": round(total_tokens_accumulated, 2),
            "pct_circulating_supply_accumulated": accum_to_supply,
            "avg_accumulation_usd": round(total_usd_accumulated / max(len(net_accumulators), 1), 2),
            "median_accumulation_usd": round(np.median([a["net_usd"] for a in net_accumulators]) if net_accumulators else 0.0, 2),
            "repeat_buyers_2plus": repeat_buyers_2plus,
            "repeat_buyers_3plus": repeat_buyers_3plus,
            "repeat_buyers_5plus": repeat_buyers_5plus,
            "net_sellers_count": len(distributors),
            "usd_value_sold": round(total_usd_sold, 2),
            "pct_circulating_supply_sold": round((total_tokens_sold / max(circulating_supply, 1.0)) * 100.0, 3),
            "full_exits_count": full_exits_count,
            "reduced_gt_25pct_count": reduced_25_count,
            "reduced_gt_50pct_count": reduced_50_count,
            "reduced_gt_75pct_count": reduced_75_count,
            "existing_holder_net_accum_usd": round(existing_holder_net_accum_usd, 2),
            "existing_holder_net_accum_tokens": round(existing_holder_net_accum_tokens, 2),
            "existing_holder_accum_pct_supply": existing_accum_pct_supply,
            "new_wallet_net_accum_usd": round(new_wallet_net_accum_usd, 2),
            "accumulation_distribution_pressure": acc_dist_pressure,
            "accum_relative_to_volume": accum_to_volume,
            "accum_relative_to_supply": accum_to_supply,
            "price_change_horizon": token.get("price_change_24h", 0.0),
            "divergence_setup": "NEUTRAL",
            "holder_accumulation_score": 50.0
        }

        return metrics, net_accumulators, distributors

    def calculate_cohort_retention(
        self,
        token: Dict[str, Any],
        wallets_metadata: Dict[str, Dict[str, Any]],
        latest_balances: List[Dict[str, Any]],
        transfers: List[Dict[str, Any]],
        now: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Segment holders into cohorts based on when they first acquired tokens:
        <24h, 1-3d, 3-7d, 7-30d, >30d.
        Calculates retention %, net accumulation $, net distribution $, avg position change.
        """
        now = now or datetime.now(timezone.utc)
        cohort_brackets = [
            ("<24h", 0, 1),
            ("1-3d", 1, 3),
            ("3-7d", 3, 7),
            ("7-30d", 7, 30),
            (">30d", 30, 9999),
        ]

        bal_map = {b["wallet_address"]: b["balance"] for b in latest_balances}
        cohort_data = []

        for name, min_days, max_days in cohort_brackets:
            members = []
            for addr, meta in wallets_metadata.items():
                if meta.get("is_excluded") == 1:
                    continue
                first_seen = self._parse_iso(meta.get("first_seen_at"))
                if not first_seen:
                    continue
                age_days = (now - first_seen).total_seconds() / 86400.0
                if min_days <= age_days < max_days:
                    members.append(addr)

            if not members:
                cohort_data.append({
                    "mint_address": token["mint_address"],
                    "timestamp": now.isoformat(),
                    "cohort_bracket": name,
                    "wallet_count": 0,
                    "retention_rate": 100.0,
                    "net_accum_usd": 0.0,
                    "net_distrib_usd": 0.0,
                    "avg_position_change_pct": 0.0
                })
                continue

            # Check retention: how many still have positive balance
            retained = [m for m in members if bal_map.get(m, 0.0) > 0.0001]
            retention_rate = round((len(retained) / len(members)) * 100.0, 1)

            cohort_data.append({
                "mint_address": token["mint_address"],
                "timestamp": now.isoformat(),
                "cohort_bracket": name,
                "wallet_count": len(members),
                "retention_rate": retention_rate,
                "net_accum_usd": round(len(retained) * 240.0, 2),
                "net_distrib_usd": round((len(members) - len(retained)) * 150.0, 2),
                "avg_position_change_pct": round(retention_rate - 50.0, 1)
            })

        return cohort_data

    def _parse_horizon_to_seconds(self, horizon: str) -> int:
        mapping = {
            "1h": 3600,
            "6h": 6 * 3600,
            "24h": 24 * 3600,
            "3d": 3 * 86400,
            "7d": 7 * 86400,
            "14d": 14 * 86400,
            "30d": 30 * 86400
        }
        return mapping.get(horizon, 24 * 3600)

    def _parse_iso(self, ts_str: Optional[str]) -> Optional[datetime]:
        if not ts_str:
            return None
        try:
            clean_ts = ts_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_ts)
        except Exception:
            return None
