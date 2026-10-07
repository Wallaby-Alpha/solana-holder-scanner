"""
database.py: SQLite Persistence and Ingestion Engine
Handles WAL mode, migrations, incremental queries, and transactional writes.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

class Database:
    def __init__(self, db_path: str = "data/scanner.db"):
        self.db_path = db_path
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            # Check if backtest_observations table exists and migrate columns
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_observations';")
            if cursor.fetchone():
                cursor_cols = conn.execute("PRAGMA table_info(backtest_observations);")
                existing_cols = {row["name"] for row in cursor_cols.fetchall()}
                new_cols = [
                    ("status", "TEXT DEFAULT 'RESOLVED'"),
                    ("source", "TEXT DEFAULT 'HISTORICAL_SEED'"),
                    ("current_unrealized_return", "REAL DEFAULT 0.0"),
                    ("latest_observed_price", "REAL"),
                    ("last_evaluated_at", "TIMESTAMP"),
                    ("is_resolved_1h", "INTEGER DEFAULT 1"),
                    ("is_resolved_6h", "INTEGER DEFAULT 1"),
                    ("is_resolved_24h", "INTEGER DEFAULT 1"),
                    ("is_resolved_7d", "INTEGER DEFAULT 1"),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.execute(f"ALTER TABLE backtest_observations ADD COLUMN {col_name} {col_type};")

            schema_path = Path(__file__).parent / "schema.sql"
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                conn.executescript(schema_sql)

    # Token Ops
    def upsert_token(self, token: Dict[str, Any]):
        sql = """
        INSERT INTO tokens (
            mint_address, symbol, name, decimals, total_supply, circulating_supply,
            created_at, deployer_address, dex_pair_address, liquidity_usd,
            market_cap_usd, current_price_usd, volume_24h_usd, price_change_24h,
            holder_count, is_active, last_updated_at
        ) VALUES (
            :mint_address, :symbol, :name, :decimals, :total_supply, :circulating_supply,
            :created_at, :deployer_address, :dex_pair_address, :liquidity_usd,
            :market_cap_usd, :current_price_usd, :volume_24h_usd, :price_change_24h,
            :holder_count, :is_active, CURRENT_TIMESTAMP
        )
        ON CONFLICT(mint_address) DO UPDATE SET
            symbol = excluded.symbol,
            name = excluded.name,
            liquidity_usd = excluded.liquidity_usd,
            market_cap_usd = excluded.market_cap_usd,
            current_price_usd = excluded.current_price_usd,
            volume_24h_usd = excluded.volume_24h_usd,
            price_change_24h = excluded.price_change_24h,
            holder_count = excluded.holder_count,
            last_updated_at = CURRENT_TIMESTAMP;
        """
        token_data = {
            "mint_address": token.get("mint_address"),
            "symbol": token.get("symbol", "UNKNOWN"),
            "name": token.get("name", "Unknown Token"),
            "decimals": token.get("decimals", 6),
            "total_supply": token.get("total_supply", 1_000_000_000.0),
            "circulating_supply": token.get("circulating_supply", 1_000_000_000.0),
            "created_at": token.get("created_at", datetime.now(timezone.utc).isoformat()),
            "deployer_address": token.get("deployer_address"),
            "dex_pair_address": token.get("dex_pair_address"),
            "liquidity_usd": token.get("liquidity_usd", 0.0),
            "market_cap_usd": token.get("market_cap_usd", 0.0),
            "current_price_usd": token.get("current_price_usd", 0.0),
            "volume_24h_usd": token.get("volume_24h_usd", 0.0),
            "price_change_24h": token.get("price_change_24h", 0.0),
            "holder_count": token.get("holder_count", 0),
            "is_active": token.get("is_active", 1)
        }
        with self.get_connection() as conn:
            conn.execute(sql, token_data)

    def get_all_tokens(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tokens WHERE is_active = 1 ORDER BY market_cap_usd DESC")
            return [dict(r) for r in cursor.fetchall()]

    def get_token(self, mint_address: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tokens WHERE mint_address = ?", (mint_address,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # Snapshot Ops
    def insert_token_snapshot(self, snapshot: Dict[str, Any]):
        sql = """
        INSERT INTO token_snapshots (
            mint_address, timestamp, price_usd, market_cap_usd, liquidity_usd,
            volume_usd, holder_count, top_10_concentration
        ) VALUES (
            :mint_address, :timestamp, :price_usd, :market_cap_usd, :liquidity_usd,
            :volume_usd, :holder_count, :top_10_concentration
        )
        """
        with self.get_connection() as conn:
            conn.execute(sql, snapshot)

    def get_token_snapshots(self, mint_address: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM token_snapshots WHERE mint_address = ? ORDER BY timestamp ASC LIMIT ?",
                (mint_address, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    # Wallets & Exclusions
    def upsert_wallet(self, wallet: Dict[str, Any]):
        sql = """
        INSERT INTO wallets (address, first_seen_at, funding_wallet, is_excluded, classification_reason, last_active_at)
        VALUES (:address, :first_seen_at, :funding_wallet, :is_excluded, :classification_reason, :last_active_at)
        ON CONFLICT(address) DO UPDATE SET
            last_active_at = excluded.last_active_at,
            funding_wallet = COALESCE(excluded.funding_wallet, wallets.funding_wallet);
        """
        with self.get_connection() as conn:
            conn.execute(sql, wallet)

    def is_wallet_excluded(self, address: str) -> Tuple[bool, Optional[str]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT is_excluded, classification_reason FROM wallets WHERE address = ?", (address,))
            row = cursor.fetchone()
            if row and row["is_excluded"] == 1:
                return True, row["classification_reason"]
            return False, None

    # Transfers
    def insert_transfers_batch(self, transfers: List[Dict[str, Any]]):
        sql = """
        INSERT OR IGNORE INTO transfers (
            signature, mint_address, from_address, to_address, amount, usd_value, timestamp, tx_type, slot
        ) VALUES (
            :signature, :mint_address, :from_address, :to_address, :amount, :usd_value, :timestamp, :tx_type, :slot
        )
        """
        with self.get_connection() as conn:
            conn.executemany(sql, transfers)

    def get_transfers_for_token(self, mint_address: str, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            if since_timestamp:
                cursor = conn.execute(
                    "SELECT * FROM transfers WHERE mint_address = ? AND timestamp >= ? ORDER BY timestamp ASC",
                    (mint_address, since_timestamp)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM transfers WHERE mint_address = ? ORDER BY timestamp ASC",
                    (mint_address,)
                )
            return [dict(r) for r in cursor.fetchall()]

    # Wallet Balances
    def upsert_wallet_balance(self, record: Dict[str, Any]):
        sql = """
        INSERT INTO wallet_token_balances (wallet_address, mint_address, timestamp, balance, usd_value)
        VALUES (:wallet_address, :mint_address, :timestamp, :balance, :usd_value)
        ON CONFLICT(wallet_address, mint_address, timestamp) DO UPDATE SET
            balance = excluded.balance,
            usd_value = excluded.usd_value;
        """
        with self.get_connection() as conn:
            conn.execute(sql, record)

    def get_latest_balances_for_token(self, mint_address: str) -> List[Dict[str, Any]]:
        sql = """
        SELECT wtb.*, w.is_excluded, w.classification_reason, w.funding_wallet, wcm.cluster_id
        FROM wallet_token_balances wtb
        JOIN (
            SELECT wallet_address, MAX(timestamp) as max_ts
            FROM wallet_token_balances
            WHERE mint_address = ?
            GROUP BY wallet_address
        ) latest ON wtb.wallet_address = latest.wallet_address AND wtb.timestamp = latest.max_ts
        LEFT JOIN wallets w ON wtb.wallet_address = w.address
        LEFT JOIN wallet_cluster_members wcm ON wtb.wallet_address = wcm.wallet_address
        WHERE wtb.mint_address = ? AND (w.is_excluded IS NULL OR w.is_excluded = 0)
        ORDER BY wtb.balance DESC
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (mint_address, mint_address))
            return [dict(r) for r in cursor.fetchall()]

    # Clusters
    def upsert_cluster(self, cluster: Dict[str, Any], member_addresses: List[str]):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO wallet_clusters (cluster_id, primary_funding_wallet, wallet_count, confidence_score, reason)
            VALUES (?, ?, ?, ?, ?)
            """, (cluster["cluster_id"], cluster.get("primary_funding_wallet"), len(member_addresses), cluster.get("confidence_score", 0.5), cluster.get("reason", "COMMON_FUNDER")))
            
            for addr in member_addresses:
                conn.execute("""
                INSERT OR REPLACE INTO wallet_cluster_members (wallet_address, cluster_id)
                VALUES (?, ?)
                """, (addr, cluster["cluster_id"]))

    def get_clusters_for_token(self, mint_address: str) -> List[Dict[str, Any]]:
        sql = """
        SELECT wc.*, GROUP_CONCAT(wcm.wallet_address) as members
        FROM wallet_clusters wc
        JOIN wallet_cluster_members wcm ON wc.cluster_id = wcm.cluster_id
        JOIN wallet_token_balances wtb ON wcm.wallet_address = wtb.wallet_address
        WHERE wtb.mint_address = ?
        GROUP BY wc.cluster_id
        HAVING COUNT(DISTINCT wcm.wallet_address) > 1
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (mint_address,))
            return [dict(r) for r in cursor.fetchall()]

    # Metrics
    def insert_token_metrics(self, metrics: Dict[str, Any]):
        sql = """
        INSERT INTO token_metrics (
            mint_address, timestamp, time_horizon, total_holders, holder_growth_rate,
            median_holder_balance, mean_holder_balance, p75_holder_balance, p90_holder_balance,
            holders_above_100_usd, holders_above_500_usd, holders_above_1k_usd,
            holders_above_5k_usd, holders_above_10k_usd,
            top_5_percent, top_10_percent, top_20_percent, top_30_percent,
            gini_coefficient, delta_top_10_concentration,
            net_accumulators_count, persistent_accumulators_count, cluster_adjusted_accumulators_count,
            pct_meaningful_holders_accumulating, usd_value_accumulated, tokens_accumulated,
            pct_circulating_supply_accumulated, avg_accumulation_usd, median_accumulation_usd,
            repeat_buyers_2plus, repeat_buyers_3plus, repeat_buyers_5plus,
            net_sellers_count, usd_value_sold, pct_circulating_supply_sold,
            full_exits_count, reduced_gt_25pct_count, reduced_gt_50pct_count, reduced_gt_75pct_count,
            existing_holder_net_accum_usd, existing_holder_net_accum_tokens,
            existing_holder_accum_pct_supply, new_wallet_net_accum_usd,
            accumulation_distribution_pressure, accum_relative_to_volume, accum_relative_to_supply,
            price_change_horizon, divergence_setup, holder_accumulation_score
        ) VALUES (
            :mint_address, :timestamp, :time_horizon, :total_holders, :holder_growth_rate,
            :median_holder_balance, :mean_holder_balance, :p75_holder_balance, :p90_holder_balance,
            :holders_above_100_usd, :holders_above_500_usd, :holders_above_1k_usd,
            :holders_above_5k_usd, :holders_above_10k_usd,
            :top_5_percent, :top_10_percent, :top_20_percent, :top_30_percent,
            :gini_coefficient, :delta_top_10_concentration,
            :net_accumulators_count, :persistent_accumulators_count, :cluster_adjusted_accumulators_count,
            :pct_meaningful_holders_accumulating, :usd_value_accumulated, :tokens_accumulated,
            :pct_circulating_supply_accumulated, :avg_accumulation_usd, :median_accumulation_usd,
            :repeat_buyers_2plus, :repeat_buyers_3plus, :repeat_buyers_5plus,
            :net_sellers_count, :usd_value_sold, :pct_circulating_supply_sold,
            :full_exits_count, :reduced_gt_25pct_count, :reduced_gt_50pct_count, :reduced_gt_75pct_count,
            :existing_holder_net_accum_usd, :existing_holder_net_accum_tokens,
            :existing_holder_accum_pct_supply, :new_wallet_net_accum_usd,
            :accumulation_distribution_pressure, :accum_relative_to_volume, :accum_relative_to_supply,
            :price_change_horizon, :divergence_setup, :holder_accumulation_score
        )
        """
        with self.get_connection() as conn:
            conn.execute(sql, metrics)

    def get_latest_metrics(self, mint_address: str, time_horizon: str = "24h") -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM token_metrics WHERE mint_address = ? AND time_horizon = ? ORDER BY timestamp DESC LIMIT 1",
                (mint_address, time_horizon)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_metrics_history(self, mint_address: str, time_horizon: str = "24h", limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM token_metrics WHERE mint_address = ? AND time_horizon = ? ORDER BY timestamp ASC LIMIT ?",
                (mint_address, time_horizon, limit)
            )
            return [dict(r) for r in cursor.fetchall()]

    def insert_cohort_metrics(self, records: List[Dict[str, Any]]):
        sql = """
        INSERT INTO cohort_metrics (mint_address, timestamp, cohort_bracket, wallet_count, retention_rate, net_accum_usd, net_distrib_usd, avg_position_change_pct)
        VALUES (:mint_address, :timestamp, :cohort_bracket, :wallet_count, :retention_rate, :net_accum_usd, :net_distrib_usd, :avg_position_change_pct)
        """
        with self.get_connection() as conn:
            conn.executemany(sql, records)

    def get_latest_cohorts(self, mint_address: str) -> List[Dict[str, Any]]:
        sql = """
        SELECT cm.* FROM cohort_metrics cm
        JOIN (
            SELECT mint_address, MAX(timestamp) as max_ts
            FROM cohort_metrics
            WHERE mint_address = ?
            GROUP BY mint_address
        ) latest ON cm.mint_address = latest.mint_address AND cm.timestamp = latest.max_ts
        WHERE cm.mint_address = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (mint_address, mint_address))
            return [dict(r) for r in cursor.fetchall()]

    # Backtest & Live Observations
    def insert_backtest_observation(self, obs: Dict[str, Any]) -> int:
        sql = """
        INSERT INTO backtest_observations (
            mint_address, observation_time, time_horizon,
            price_at_t, mcap_at_t, vol_24h_at_t, price_change_prior,
            existing_holder_net_accum_usd, persistent_accumulators_count, cluster_adjusted_accumulators_count,
            accumulation_pressure, accum_relative_to_volume, holder_retention_rate,
            concentration_top_10, composite_score, setup_classification,
            fwd_ret_1h, fwd_ret_6h, fwd_ret_24h, fwd_ret_3d, fwd_ret_7d, fwd_ret_14d, fwd_ret_30d,
            mfe_pct, mae_pct, max_drawdown_pct,
            hit_plus_10, hit_plus_25, hit_plus_50, hit_plus_100,
            hit_minus_10, hit_minus_25, hit_minus_50,
            status, source, current_unrealized_return, latest_observed_price, last_evaluated_at,
            is_resolved_1h, is_resolved_6h, is_resolved_24h, is_resolved_7d
        ) VALUES (
            :mint_address, :observation_time, :time_horizon,
            :price_at_t, :mcap_at_t, :vol_24h_at_t, :price_change_prior,
            :existing_holder_net_accum_usd, :persistent_accumulators_count, :cluster_adjusted_accumulators_count,
            :accumulation_pressure, :accum_relative_to_volume, :holder_retention_rate,
            :concentration_top_10, :composite_score, :setup_classification,
            :fwd_ret_1h, :fwd_ret_6h, :fwd_ret_24h, :fwd_ret_3d, :fwd_ret_7d, :fwd_ret_14d, :fwd_ret_30d,
            :mfe_pct, :mae_pct, :max_drawdown_pct,
            :hit_plus_10, :hit_plus_25, :hit_plus_50, :hit_plus_100,
            :hit_minus_10, :hit_minus_25, :hit_minus_50,
            :status, :source, :current_unrealized_return, :latest_observed_price, :last_evaluated_at,
            :is_resolved_1h, :is_resolved_6h, :is_resolved_24h, :is_resolved_7d
        )
        """
        data = {
            "mint_address": obs.get("mint_address"),
            "observation_time": obs.get("observation_time"),
            "time_horizon": obs.get("time_horizon", "24h"),
            "price_at_t": obs.get("price_at_t"),
            "mcap_at_t": obs.get("mcap_at_t"),
            "vol_24h_at_t": obs.get("vol_24h_at_t"),
            "price_change_prior": obs.get("price_change_prior", 0.0),
            "existing_holder_net_accum_usd": obs.get("existing_holder_net_accum_usd", 0.0),
            "persistent_accumulators_count": obs.get("persistent_accumulators_count", 0),
            "cluster_adjusted_accumulators_count": obs.get("cluster_adjusted_accumulators_count", 0),
            "accumulation_pressure": obs.get("accumulation_pressure", 1.0),
            "accum_relative_to_volume": obs.get("accum_relative_to_volume", 0.0),
            "holder_retention_rate": obs.get("holder_retention_rate", 50.0),
            "concentration_top_10": obs.get("concentration_top_10", 0.0),
            "composite_score": obs.get("composite_score", 50.0),
            "setup_classification": obs.get("setup_classification", "NEUTRAL"),
            "fwd_ret_1h": obs.get("fwd_ret_1h"),
            "fwd_ret_6h": obs.get("fwd_ret_6h"),
            "fwd_ret_24h": obs.get("fwd_ret_24h"),
            "fwd_ret_3d": obs.get("fwd_ret_3d"),
            "fwd_ret_7d": obs.get("fwd_ret_7d"),
            "fwd_ret_14d": obs.get("fwd_ret_14d"),
            "fwd_ret_30d": obs.get("fwd_ret_30d"),
            "mfe_pct": obs.get("mfe_pct", 0.0),
            "mae_pct": obs.get("mae_pct", 0.0),
            "max_drawdown_pct": obs.get("max_drawdown_pct", 0.0),
            "hit_plus_10": obs.get("hit_plus_10", 0),
            "hit_plus_25": obs.get("hit_plus_25", 0),
            "hit_plus_50": obs.get("hit_plus_50", 0),
            "hit_plus_100": obs.get("hit_plus_100", 0),
            "hit_minus_10": obs.get("hit_minus_10", 0),
            "hit_minus_25": obs.get("hit_minus_25", 0),
            "hit_minus_50": obs.get("hit_minus_50", 0),
            "status": obs.get("status", "RESOLVED"),
            "source": obs.get("source", "HISTORICAL_SEED"),
            "current_unrealized_return": obs.get("current_unrealized_return", 0.0),
            "latest_observed_price": obs.get("latest_observed_price", obs.get("price_at_t")),
            "last_evaluated_at": obs.get("last_evaluated_at", datetime.now(timezone.utc).isoformat()),
            "is_resolved_1h": obs.get("is_resolved_1h", 1),
            "is_resolved_6h": obs.get("is_resolved_6h", 1),
            "is_resolved_24h": obs.get("is_resolved_24h", 1),
            "is_resolved_7d": obs.get("is_resolved_7d", 1),
        }
        with self.get_connection() as conn:
            cursor = conn.execute(sql, data)
            return cursor.lastrowid

    def get_all_backtest_observations(self, horizon: str = "24h") -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM backtest_observations WHERE time_horizon = ? ORDER BY observation_time DESC",
                (horizon,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_pending_observations(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM backtest_observations WHERE status IN ('PENDING', 'MATURING') ORDER BY observation_time ASC"
            )
            return [dict(r) for r in cursor.fetchall()]

    def update_observation_forward_stats(self, obs_id: int, updates: Dict[str, Any]):
        set_clauses = [f"{k} = :{k}" for k in updates.keys()]
        sql = f"UPDATE backtest_observations SET {', '.join(set_clauses)} WHERE id = :obs_id"
        params = {**updates, "obs_id": obs_id}
        with self.get_connection() as conn:
            conn.execute(sql, params)

    def record_tracker_run(self, run_info: Dict[str, Any]):
        sql = """
        INSERT INTO tracker_runs (
            run_timestamp, tokens_evaluated, new_observations_created,
            matured_observations_updated, active_tracking_count, duration_ms
        ) VALUES (
            :run_timestamp, :tokens_evaluated, :new_observations_created,
            :matured_observations_updated, :active_tracking_count, :duration_ms
        )
        """
        with self.get_connection() as conn:
            conn.execute(sql, run_info)

    def get_recent_tracker_runs(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tracker_runs ORDER BY run_timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_tracker_counts(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM backtest_observations WHERE status = 'PENDING'")
            pending = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM backtest_observations WHERE status = 'MATURING'")
            maturing = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM backtest_observations WHERE status = 'RESOLVED'")
            resolved = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM backtest_observations")
            total = c.fetchone()[0]
            return {
                "pending": pending,
                "maturing": maturing,
                "resolved": resolved,
                "total": total
            }
