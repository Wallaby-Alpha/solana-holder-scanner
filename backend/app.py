"""
app.py: FastAPI Server and REST API for Solana Micro-cap Holder Accumulation Research.
Serves real-time token metrics, dynamic wallet behavior, backtest results, and frontend assets.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import GLOBAL_CONFIG, ScreenerFilterConfig, AccumulatorConfig, ScoringWeightsConfig
from .db.database import Database
from .services.pipeline import IngestionPipeline
from .services.backtest_engine import BacktestEngine
from .services.ongoing_tracker import OngoingTracker

app = FastAPI(
    title="Solana Persistent Holder Accumulation Research Engine",
    description="Quantitative on-chain scanner and predictive backtesting framework for Solana microcaps.",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "scanner.db"
FRONTEND_DIR = BASE_DIR / "frontend"

db = Database(db_path=str(DB_PATH))
pipeline = IngestionPipeline(db=db, config=GLOBAL_CONFIG)
backtest_engine = BacktestEngine()
tracker = OngoingTracker(db=db)

@app.on_event("startup")
async def startup_event():
    print("[Server] Initializing database and starting seed pipeline...")
    await pipeline.initialize_and_seed_database()
    tracker.start_background_daemon()

# --- API Endpoints ---

@app.get("/api/tokens")
async def get_tokens(
    horizon: str = Query(default="24h"),
    setup_filter: Optional[str] = Query(default=None),
    min_mcap: Optional[float] = Query(default=None),
    max_mcap: Optional[float] = Query(default=None),
    min_liq: Optional[float] = Query(default=None),
    min_vol: Optional[float] = Query(default=None),
    min_holders: Optional[int] = Query(default=None)
):
    """
    Get screened tokens list enriched with holder accumulation metrics,
    cluster-adjusted counts, absorption pressure, and divergence setups.
    """
    all_tokens = db.get_all_tokens()
    enriched_list = []

    for t in all_tokens:
        mint = t["mint_address"]
        metrics = db.get_latest_metrics(mint, time_horizon=horizon)
        
        mcap = t.get("market_cap_usd", 0.0)
        liq = t.get("liquidity_usd", 0.0)
        vol = t.get("volume_24h_usd", 0.0)
        holders = t.get("holder_count", 0)

        # Apply runtime filters if specified
        if min_mcap is not None and mcap < min_mcap:
            continue
        if max_mcap is not None and mcap > max_mcap:
            continue
        if min_liq is not None and liq < min_liq:
            continue
        if min_vol is not None and vol < min_vol:
            continue
        if min_holders is not None and holders < min_holders:
            continue

        setup = metrics.get("divergence_setup", "NEUTRAL") if metrics else "NEUTRAL"
        if setup_filter and setup_filter != "ALL" and setup != setup_filter:
            continue

        token_age_days = 0.0
        if t.get("created_at"):
            try:
                created_dt = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                token_age_days = round((datetime.now(timezone.utc) - created_dt).total_seconds() / 86400.0, 1)
            except Exception:
                token_age_days = 14.0

        item = {
            "mint_address": mint,
            "symbol": t.get("symbol"),
            "name": t.get("name"),
            "category": t.get("category", "TOKEN"),
            "current_price_usd": t.get("current_price_usd", 0.0),
            "market_cap_usd": mcap,
            "liquidity_usd": liq,
            "volume_24h_usd": vol,
            "price_change_24h": t.get("price_change_24h", 0.0),
            "holder_count": holders,
            "token_age_days": token_age_days,
            
            # Dynamic Accumulation Metrics
            "holder_growth_rate": metrics.get("holder_growth_rate", 0.0) if metrics else 0.0,
            "top_10_percent": metrics.get("top_10_percent", 0.0) if metrics else 0.0,
            "gini_coefficient": metrics.get("gini_coefficient", 0.0) if metrics else 0.0,
            
            "existing_holder_net_accum_usd": metrics.get("existing_holder_net_accum_usd", 0.0) if metrics else 0.0,
            "existing_holder_accum_pct_supply": metrics.get("existing_holder_accum_pct_supply", 0.0) if metrics else 0.0,
            "new_wallet_net_accum_usd": metrics.get("new_wallet_net_accum_usd", 0.0) if metrics else 0.0,
            
            "persistent_accumulators_count": metrics.get("persistent_accumulators_count", 0) if metrics else 0,
            "cluster_adjusted_accumulators_count": metrics.get("cluster_adjusted_accumulators_count", 0) if metrics else 0,
            "net_accumulators_count": metrics.get("net_accumulators_count", 0) if metrics else 0,
            
            "accumulation_distribution_pressure": metrics.get("accumulation_distribution_pressure", 1.0) if metrics else 1.0,
            "net_accumulation_usd": metrics.get("usd_value_accumulated", 0.0) if metrics else 0.0,
            "accum_relative_to_volume": metrics.get("accum_relative_to_volume", 0.0) if metrics else 0.0,
            
            "divergence_setup": setup,
            "holder_accumulation_score": metrics.get("holder_accumulation_score", 50.0) if metrics else 50.0,
        }
        enriched_list.append(item)

    return {"count": len(enriched_list), "tokens": enriched_list, "horizon": horizon}

@app.get("/api/tokens/{mint}")
async def get_token_detail(mint: str, horizon: str = Query(default="24h")):
    """
    Detailed analytics for a specific token: snapshots, multi-horizon metrics,
    cohort retention, wallet behavior leaderboard, and cluster memberships.
    """
    token = db.get_token(mint)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    snapshots = db.get_token_snapshots(mint, limit=120)
    current_metrics = db.get_latest_metrics(mint, time_horizon=horizon)
    all_horizons_metrics = {h: db.get_latest_metrics(mint, time_horizon=h) for h in GLOBAL_CONFIG.horizons}
    cohorts = db.get_latest_cohorts(mint)
    clusters = db.get_clusters_for_token(mint)

    # Fetch top holder balances and transfers to build accumulator / distributor drilldown
    latest_balances = db.get_latest_balances_for_token(mint)
    transfers = db.get_transfers_for_token(mint)
    
    # Analyze dynamic wallets for this horizon
    wallets_meta = {b["wallet_address"]: b for b in latest_balances}
    _, accumulators, distributors = pipeline.analyzer.analyze_token_horizon(
        token=token,
        transfers=transfers,
        wallets_metadata=wallets_meta,
        latest_balances=latest_balances,
        horizon=horizon
    )

    # Sort accumulators by net accumulation
    accumulators.sort(key=lambda x: x.get("net_usd", 0), reverse=True)
    distributors.sort(key=lambda x: x.get("net_usd_sold", 0), reverse=True)

    # Enrich accumulator wallets with details
    price = token.get("current_price_usd", 0.0001)
    enriched_accumulators = []
    for acc in accumulators[:25]:
        addr = acc["address"]
        bal_entry = next((b for b in latest_balances if b["wallet_address"] == addr), None)
        curr_bal_usd = (bal_entry["balance"] * price) if bal_entry else 0.0
        cluster_id = bal_entry.get("cluster_id") if bal_entry else None
        
        enriched_accumulators.append({
            "address": addr,
            "net_usd": acc["net_usd"],
            "net_tokens": acc["net_tokens"],
            "buys_count": acc["buys"],
            "sells_count": acc["sells"],
            "current_position_usd": round(curr_bal_usd, 2),
            "is_persistent": acc["is_persistent"],
            "is_existing_holder": acc["is_existing_holder"],
            "sold_pct": acc["sold_pct"],
            "cluster_id": cluster_id,
            "is_clustered": bool(cluster_id)
        })

    return {
        "token": token,
        "current_metrics": current_metrics,
        "all_horizons_metrics": all_horizons_metrics,
        "price_history": snapshots,
        "cohorts": cohorts,
        "clusters": clusters,
        "top_accumulators": enriched_accumulators,
        "top_distributors": distributors[:15]
    }

@app.get("/api/wallets/leaderboard")
async def get_accumulator_leaderboard(
    mint: Optional[str] = Query(default=None),
    filter_clustered: bool = Query(default=False)
):
    """
    Leaderboard of wallets ranked by persistence, purchases, and net accumulation.
    Includes filter to exclude clustered/suspicious wallets.
    """
    all_tokens = db.get_all_tokens()
    tokens_to_scan = [t for t in all_tokens if t["mint_address"] == mint] if mint else all_tokens[:8]

    enriched = []
    for token in tokens_to_scan:
        target_mint = token["mint_address"]
        price = token.get("current_price_usd", 0.001)
        latest_bals = db.get_latest_balances_for_token(target_mint)
        transfers = db.get_transfers_for_token(target_mint)
        wallets_meta = {b["wallet_address"]: b for b in latest_bals}

        _, accumulators, _ = pipeline.analyzer.analyze_token_horizon(
            token=token,
            transfers=transfers,
            wallets_metadata=wallets_meta,
            latest_balances=latest_bals,
            horizon="24h"
        )

        for acc in accumulators:
            addr = acc["address"]
            bal_entry = next((b for b in latest_bals if b["wallet_address"] == addr), None)
            cluster_id = bal_entry.get("cluster_id") if bal_entry else None
            
            if filter_clustered and cluster_id:
                continue

            curr_usd = (bal_entry["balance"] * price) if bal_entry else 0.0
            enriched.append({
                "address": addr,
                "mint_address": target_mint,
                "symbol": token.get("symbol", "TOKEN"),
                "net_usd": acc["net_usd"],
                "purchases": acc["buys"],
                "sales": acc["sells"],
                "current_position_usd": round(curr_usd, 2),
                "is_persistent": acc["is_persistent"],
                "is_existing_holder": acc["is_existing_holder"],
                "cluster_id": cluster_id,
                "is_clustered": bool(cluster_id)
            })

    enriched.sort(key=lambda x: (x["is_persistent"], x["net_usd"]), reverse=True)
    return {"leaderboard": enriched[:50]}

@app.get("/api/wallets/{address}")
async def get_wallet_detail(address: str, mint: Optional[str] = Query(default=None)):
    """
    Wallet profile: first seen, transactions, persistence badge, clusters, and positions.
    """
    is_excluded, reason = db.is_wallet_excluded(address)
    
    # Query transfers involving this wallet
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM transfers WHERE from_address = ? OR to_address = ? ORDER BY timestamp DESC LIMIT 50",
            (address, address)
        )
        txs = [dict(r) for r in cursor.fetchall()]

        cursor_bal = conn.execute(
            "SELECT * FROM wallet_token_balances WHERE wallet_address = ? ORDER BY timestamp DESC LIMIT 20",
            (address,)
        )
        balances = [dict(r) for r in cursor_bal.fetchall()]

        cursor_cluster = conn.execute(
            "SELECT wc.* FROM wallet_clusters wc JOIN wallet_cluster_members wcm ON wc.cluster_id = wcm.cluster_id WHERE wcm.wallet_address = ?",
            (address,)
        )
        cluster_info = cursor_cluster.fetchone()

    buys = [t for t in txs if t["to_address"] == address]
    sells = [t for t in txs if t["from_address"] == address]

    return {
        "address": address,
        "is_excluded": is_excluded,
        "classification_reason": reason,
        "total_buys": len(buys),
        "total_sells": len(sells),
        "total_usd_bought": round(sum(t.get("usd_value", 0) for t in buys), 2),
        "total_usd_sold": round(sum(t.get("usd_value", 0) for t in sells), 2),
        "is_persistent_accumulator": len(buys) >= 2 and len(sells) <= 1,
        "cluster": dict(cluster_info) if cluster_info else None,
        "recent_transfers": txs[:15],
    }

@app.get("/api/backtest/results")
async def get_backtest_results(horizon: str = Query(default="fwd_ret_24h")):
    """
    Fetches frozen backtest observations and evaluates Negative Control Models A through F.
    Directly answers whether persistent holder accumulation has predictive value for future returns.
    """
    obs = db.get_all_backtest_observations(horizon="24h")
    eval_result = backtest_engine.evaluate_benchmark_models(obs, target_horizon=horizon)
    return {
        "target_horizon": horizon,
        "observations_count": len(obs),
        "recent_observations": obs[:30],
        **eval_result
    }

@app.get("/api/config")
async def get_config():
    """Retrieve all configurable filters, accumulator thresholds, and scoring weights."""
    return {
        "screener": GLOBAL_CONFIG.screener.dict(),
        "accumulator": GLOBAL_CONFIG.accumulator.dict(),
        "scoring": GLOBAL_CONFIG.scoring.dict(),
        "horizons": GLOBAL_CONFIG.horizons
    }

@app.post("/api/config")
async def update_config(payload: Dict[str, Any] = Body(...)):
    """Update runtime configurations dynamically."""
    if "screener" in payload:
        GLOBAL_CONFIG.screener = ScreenerFilterConfig(**payload["screener"])
    if "accumulator" in payload:
        GLOBAL_CONFIG.accumulator = AccumulatorConfig(**payload["accumulator"])
    if "scoring" in payload:
        GLOBAL_CONFIG.scoring = ScoringWeightsConfig(**payload["scoring"])
    return {"status": "success", "message": "Configuration updated successfully."}

@app.post("/api/pipeline/refresh")
async def trigger_refresh():
    """Trigger incremental scan and refresh."""
    await pipeline.scan_and_update_all()
    return {"status": "success", "message": "Incremental scan cycle completed."}

# --- Ongoing Live Forward Return Tracker Endpoints ---

@app.get("/api/tracker/status")
async def get_tracker_status():
    """Returns background daemon status, observation counts, and recent tracking cycles."""
    counts = db.get_tracker_counts()
    recent_runs = db.get_recent_tracker_runs(limit=10)
    return {
        "is_daemon_running": tracker.is_running,
        "poll_interval_seconds": tracker.poll_interval_seconds,
        "last_run_timestamp": tracker.last_run_timestamp,
        "counts": counts,
        "recent_runs": recent_runs
    }

@app.get("/api/tracker/scorecard")
async def get_tracker_scorecard():
    """Calculates rolling statistical predictive power of persistent holder accumulation."""
    return tracker.compute_predictive_scorecard()

@app.get("/api/tracker/active")
async def get_active_observations():
    """Returns open/maturing observations currently pending future forward return realization."""
    pending = db.get_pending_observations()
    tokens_map = {t["mint_address"]: t for t in db.get_all_tokens()}
    enriched = []
    for o in pending:
        t = tokens_map.get(o["mint_address"], {})
        enriched.append({
            **o,
            "symbol": t.get("symbol", "TOKEN"),
            "name": t.get("name", "Unknown Token"),
            "category": t.get("category", "TOKEN"),
            "current_token_price": t.get("current_price_usd", o["price_at_t"])
        })
    return {"count": len(enriched), "observations": enriched}

@app.post("/api/tracker/snapshot")
async def trigger_tracker_snapshot():
    """Manually captures and freezes an observation snapshot for all screened tokens right now."""
    created_ids = await tracker.capture_live_observations_snapshot()
    return {
        "status": "success",
        "message": f"Captured {len(created_ids)} new frozen observations at timestamp T.",
        "created_ids": created_ids
    }

@app.post("/api/tracker/resolve")
async def trigger_tracker_resolve():
    """Manually checks and updates milestone forward returns for maturing observations."""
    updated = await tracker.update_maturing_observations()
    return {
        "status": "success",
        "message": f"Evaluated and updated {updated} maturing observations.",
        "updated_count": updated
    }

@app.post("/api/tracker/simulate-forward")
async def trigger_simulate_forward(hours: float = Query(default=6.0)):
    """Simulates forward price path progression by N hours for immediate empirical validation."""
    result = tracker.simulate_forward_progression(hours_to_advance=hours)
    return result

# Mount static files and frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "running", "message": "Solana Holder Accumulation Research API ready."})
