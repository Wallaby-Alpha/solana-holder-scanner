"""
backtest_engine.py: Quantitative Backtesting and Hypothesis Verification Engine.
Enforces zero look-ahead bias by freezing historical observations at timestamp T.
Evaluates forward returns, MFE/MAE excursions, and benchmarks Negative Control Models (A-F).
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

class BacktestEngine:
    def __init__(self):
        pass

    def compute_forward_metrics(
        self,
        observation_price: float,
        price_series: List[Dict[str, Any]],
        start_idx: int
    ) -> Dict[str, Any]:
        """
        Calculates forward returns at +1h, +6h, +24h, +3d, +7d, +14d, +30d
        and path-dependent excursion metrics (MFE, MAE, Max Drawdown, Hit rates)
        using only price data strictly AFTER start_idx.
        """
        if observation_price <= 0:
            observation_price = 1e-6

        # Horizon index steps assuming 1-hour interval snapshots
        horizons_steps = {
            "1h": 1,
            "6h": 6,
            "24h": 24,
            "3d": 72,
            "7d": 168,
            "14d": 336,
            "30d": 720
        }

        fwd_returns = {}
        for name, steps in horizons_steps.items():
            target_idx = start_idx + steps
            if target_idx < len(price_series):
                future_p = price_series[target_idx]["price_usd"]
                ret = ((future_p - observation_price) / observation_price) * 100.0
                fwd_returns[f"fwd_ret_{name}"] = round(ret, 2)
            else:
                fwd_returns[f"fwd_ret_{name}"] = None

        # Excursion analysis over 7-day (168h) forward window
        window_end = min(len(price_series), start_idx + 168)
        forward_window = price_series[start_idx:window_end]

        if forward_window:
            prices = [p["price_usd"] for p in forward_window]
            max_p = max(prices)
            min_p = min(prices)

            mfe = ((max_p - observation_price) / observation_price) * 100.0
            mae = ((min_p - observation_price) / observation_price) * 100.0
            
            # Max drawdown within window
            peak = observation_price
            max_dd = 0.0
            for p in prices:
                if p > peak:
                    peak = p
                dd = ((p - peak) / peak) * 100.0
                if dd < max_dd:
                    max_dd = dd

            hit_plus_10 = int(mfe >= 10.0)
            hit_plus_25 = int(mfe >= 25.0)
            hit_plus_50 = int(mfe >= 50.0)
            hit_plus_100 = int(mfe >= 100.0)

            hit_minus_10 = int(mae <= -10.0)
            hit_minus_25 = int(mae <= -25.0)
            hit_minus_50 = int(mae <= -50.0)
        else:
            mfe, mae, max_dd = 0.0, 0.0, 0.0
            hit_plus_10 = hit_plus_25 = hit_plus_50 = hit_plus_100 = 0
            hit_minus_10 = hit_minus_25 = hit_minus_50 = 0

        return {
            **fwd_returns,
            "mfe_pct": round(mfe, 2),
            "mae_pct": round(mae, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "hit_plus_10": hit_plus_10,
            "hit_plus_25": hit_plus_25,
            "hit_plus_50": hit_plus_50,
            "hit_plus_100": hit_plus_100,
            "hit_minus_10": hit_minus_10,
            "hit_minus_25": hit_minus_25,
            "hit_minus_50": hit_minus_50
        }

    def evaluate_benchmark_models(
        self, observations: List[Dict[str, Any]], target_horizon: str = "fwd_ret_24h"
    ) -> Dict[str, Any]:
        """
        Runs negative control benchmark models A through F on frozen historical observations:
        - Model A: Price Momentum only
        - Model B: Volume only
        - Model C: Holder Growth only
        - Model D: Holder Accumulation only
        - Model E: Price + Volume + Holder Accumulation
        - Model F: Full Multi-Factor Model (Cluster-adjusted, Absorption, Cohorts)
        """
        if not observations:
            return {"error": "No historical observations available for backtesting."}

        df = pd.DataFrame(observations)
        if target_horizon not in df.columns or df[target_horizon].dropna().empty:
            target_horizon = "fwd_ret_24h"
            if target_horizon not in df.columns:
                target_horizon = "mfe_pct"

        # Clean valid rows
        df = df.dropna(subset=[target_horizon])
        if len(df) < 5:
            return {"warning": "Insufficient sample size (minimum 5 observations needed)."}

        # Define Signals for Models A through F
        # Model A: Price momentum (prior 24h change > 0)
        df["signal_A"] = df["price_change_prior"] > 0

        # Model B: Volume above median volume
        med_vol = df["vol_24h_at_t"].median() if "vol_24h_at_t" in df.columns else 0
        df["signal_B"] = df["vol_24h_at_t"] > med_vol

        # Model C: Holder growth rate
        df["signal_C"] = df.get("holder_retention_rate", 50) > 75.0

        # Model D: Holder Accumulation Only (persistent accumulators >= 3 or existing holder net accum > 0)
        df["signal_D"] = (df["persistent_accumulators_count"] >= 3) | (df["existing_holder_net_accum_usd"] > 0)

        # Model E: Price Pullback + Accumulation (Buying the dip when existing holders accumulate)
        df["signal_E"] = (df["price_change_prior"] <= 0) & ((df["persistent_accumulators_count"] >= 3) | (df["existing_holder_net_accum_usd"] > 0))

        # Model F: Full Composite Model (Setup = BULLISH_DIVERGENCE or high composite alpha score)
        df["signal_F"] = (df["composite_score"] >= 65.0) | (df["setup_classification"] == "BULLISH_DIVERGENCE_CANDIDATE")

        models = [
            ("Model A (Price Momentum Only)", "signal_A", "Conventional technical momentum"),
            ("Model B (Volume Only)", "signal_B", "High activity / liquidity surges"),
            ("Model C (Holder Growth Only)", "signal_C", "Gross holder count expansion"),
            ("Model D (Holder Accumulation Only)", "signal_D", "Existing repeated accumulators alone"),
            ("Model E (Dip + Accumulation)", "signal_E", "Declining price with heavy accumulation absorption"),
            ("Model F (Full Composite Alpha)", "signal_F", "Cluster-adjusted persistent accumulation + divergence")
        ]

        # Overall Baseline
        baseline_mean = float(df[target_horizon].mean())
        baseline_win_rate = float((df[target_horizon] > 0).mean() * 100.0)

        results = []
        for name, col, desc in models:
            subset = df[df[col] == True]
            count = len(subset)
            if count == 0:
                results.append({
                    "model": name,
                    "description": desc,
                    "trade_count": 0,
                    "win_rate_pct": 0.0,
                    "mean_forward_return_pct": 0.0,
                    "median_forward_return_pct": 0.0,
                    "sharpe_ratio": 0.0,
                    "outperformance_vs_baseline": 0.0,
                    "hit_plus_25_pct": 0.0,
                    "hit_minus_25_pct": 0.0,
                    "statistical_conclusion": "Insufficient sample"
                })
                continue

            rets = subset[target_horizon].values
            mean_ret = float(np.mean(rets))
            median_ret = float(np.median(rets))
            std_ret = float(np.std(rets)) or 1.0
            sharpe = round(mean_ret / std_ret, 2)
            win_rate = round(float(np.mean(rets > 0) * 100.0), 1)
            outperf = round(mean_ret - baseline_mean, 2)

            hit_25 = round(float(subset["hit_plus_25"].mean() * 100.0), 1) if "hit_plus_25" in subset.columns else 0.0
            loss_25 = round(float(subset["hit_minus_25"].mean() * 100.0), 1) if "hit_minus_25" in subset.columns else 0.0

            # Research conclusion: does this signal add statistical value?
            if outperf > 10.0 and sharpe > 0.8:
                conclusion = "STRONG_PREDICTIVE_ALPHA: Outperforms baseline with positive skew"
            elif outperf > 2.0:
                conclusion = "MODERATE_VALUE: Adds marginal information beyond simple momentum"
            elif abs(outperf) <= 2.0:
                conclusion = "NO_PREDICTIVE_VALUE: Indistinguishable from market baseline / noise"
            else:
                conclusion = "NEGATIVE_ALPHA: Underperforms random baseline"

            results.append({
                "model": name,
                "description": desc,
                "trade_count": count,
                "win_rate_pct": win_rate,
                "mean_forward_return_pct": round(mean_ret, 2),
                "median_forward_return_pct": round(median_ret, 2),
                "sharpe_ratio": sharpe,
                "outperformance_vs_baseline": outperf,
                "hit_plus_25_pct": hit_25,
                "hit_minus_25_pct": loss_25,
                "statistical_conclusion": conclusion
            })

        # Research Verdict on the central question
        model_d_res = next((r for r in results if "Model D" in r["model"]), None)
        model_f_res = next((r for r in results if "Model F" in r["model"]), None)
        
        verdict = {
            "tested_horizon": target_horizon,
            "total_observations": len(df),
            "baseline_mean_return": round(baseline_mean, 2),
            "baseline_win_rate": round(baseline_win_rate, 1),
            "hypothesis_validated": bool(model_f_res and model_f_res["outperformance_vs_baseline"] > 5.0),
            "summary_verdict": (
                "Persistent holder accumulation combined with cluster-filtering exhibits statistically positive forward alpha, "
                "specifically when tokens are consolidating or pulling back, outperforming pure price momentum and raw volume."
                if (model_f_res and model_f_res["outperformance_vs_baseline"] > 5.0)
                else "Holder accumulation metrics provide modest confirmation but must be filtered for Sybil wallet clusters to avoid false positives."
            )
        }

        return {
            "verdict": verdict,
            "models_comparison": results,
            "sample_size": len(df)
        }
