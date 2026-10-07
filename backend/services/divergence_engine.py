"""
divergence_engine.py: Price vs Holder Behavior Divergence and Absorption Analytics.
Identifies quantitative research setups (Bullish Divergence, Distribution, Breakout Consolidation)
and computes configurable composite Holder Accumulation Score.
"""

from typing import Dict, Any, Optional
from ..config import ScoringWeightsConfig, GLOBAL_CONFIG

class DivergenceEngine:
    def __init__(self, weights: Optional[ScoringWeightsConfig] = None):
        self.weights = weights or GLOBAL_CONFIG.scoring

    def evaluate_divergence_setup(
        self,
        metrics: Dict[str, Any],
        price_change_pct: float,
        volume_trend: float = 1.0
    ) -> str:
        """
        Classifies current setup into research categories without promotional bias:
        - 'BULLISH_DIVERGENCE_CANDIDATE'
        - 'DISTRIBUTION_CANDIDATE'
        - 'BREAKOUT_CONSOLIDATION_CANDIDATE'
        - 'HIGH_CLUSTER_RISK'
        - 'NEUTRAL'
        """
        persistent_count = metrics.get("persistent_accumulators_count", 0)
        cluster_adjusted_count = metrics.get("cluster_adjusted_accumulators_count", persistent_count)
        existing_accum_usd = metrics.get("existing_holder_net_accum_usd", 0.0)
        pressure = metrics.get("accumulation_distribution_pressure", 1.0)
        net_sellers = metrics.get("net_sellers_count", 0)
        
        # Check cluster risk first
        if persistent_count >= 8 and (cluster_adjusted_count / max(persistent_count, 1)) < 0.35:
            return "HIGH_CLUSTER_RISK"

        # Bullish Divergence Candidate:
        # Price is down (e.g. <= -5%), but existing holders are actively accumulating,
        # persistent accumulators are rising, and absorption pressure is high (>= 1.5).
        if price_change_pct <= -5.0 and existing_accum_usd > 1000.0 and pressure >= 1.5 and persistent_count >= 3:
            return "BULLISH_DIVERGENCE_CANDIDATE"

        # Breakout Consolidation Candidate:
        # Price flat/consolidating (-5% to +5%), healthy accumulation, repeat buyers
        if -5.0 <= price_change_pct <= 5.0 and existing_accum_usd > 800.0 and persistent_count >= 3:
            return "BREAKOUT_CONSOLIDATION_CANDIDATE"

        # Distribution Candidate:
        # Price declining or flat, existing holders selling off, accumulators low or absent, sellers dominate
        if price_change_pct < 0.0 and (existing_accum_usd < 0.0 or pressure < 0.7) and net_sellers > persistent_count:
            return "DISTRIBUTION_CANDIDATE"

        return "NEUTRAL"

    def compute_holder_accumulation_score(
        self,
        metrics: Dict[str, Any],
        weights: Optional[ScoringWeightsConfig] = None
    ) -> float:
        """
        Calculates configurable composite Holder Accumulation Score (0 to 100).
        All sub-component weights are configurable.
        """
        w = weights or self.weights

        # 1. Existing-holder accumulation component (normalized 0-100)
        exist_usd = max(0.0, metrics.get("existing_holder_net_accum_usd", 0.0))
        s_exist = min(100.0, (exist_usd / 5000.0) * 100.0)

        # 2. Persistent accumulator count (normalized 0-100)
        persist_count = metrics.get("persistent_accumulators_count", 0)
        s_persist = min(100.0, (persist_count / 15.0) * 100.0)

        # 3. Repeat buyers component
        repeat_2plus = metrics.get("repeat_buyers_2plus", 0)
        s_repeat = min(100.0, (repeat_2plus / 20.0) * 100.0)

        # 4. Accumulation relative to volume
        acc_vol = metrics.get("accum_relative_to_volume", 0.0)
        s_acc_vol = min(100.0, (acc_vol / 0.10) * 100.0) # 10% of vol is max score

        # 5. Accumulation relative to supply
        acc_supply = metrics.get("pct_circulating_supply_accumulated", 0.0)
        s_acc_supply = min(100.0, (acc_supply / 2.0) * 100.0) # 2% of circ supply is max

        # 6. Retention rate
        retention = metrics.get("pct_meaningful_holders_accumulating", 50.0)
        s_retention = min(100.0, retention * 2.0)

        # 7. Concentration improvement (delta concentration: negative is healthier distribution)
        delta_conc = metrics.get("delta_top_10_concentration", 0.0)
        s_conc = 50.0 - (delta_conc * 10.0)
        s_conc = max(0.0, min(100.0, s_conc))

        # 8. Cluster independence
        raw_cnt = max(metrics.get("persistent_accumulators_count", 1), 1)
        cluster_cnt = metrics.get("cluster_adjusted_accumulators_count", raw_cnt)
        indep_ratio = cluster_cnt / raw_cnt
        s_cluster = indep_ratio * 100.0

        # Weighted composite score
        score = (
            w.weight_existing_holder_accum * s_exist +
            w.weight_persistent_accum_count * s_persist +
            w.weight_repeat_buyers * s_repeat +
            w.weight_accum_to_volume * s_acc_vol +
            w.weight_accum_to_supply * s_acc_supply +
            w.weight_cohort_retention * s_retention +
            w.weight_concentration_improvement * s_conc +
            w.weight_cluster_independence * s_cluster
        )

        return round(max(0.0, min(100.0, score)), 1)
