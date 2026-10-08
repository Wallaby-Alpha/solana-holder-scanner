"""
streamlit_app.py: Interactive Research Dashboard for Solana Micro-Cap Holder Accumulation.
Features:
- Live Alpha Scorecard & Hypothesis Testing (H0 vs H1)
- Interactive Excursion Charts (MFE / MAE / Drawdowns)
- Live In-Flight Forward Return Tracker
- Token Screener & Accumulator Deep Dive
- Sybil Cluster Analysis & Accumulator Leaderboard
"""

import os
import sqlite3
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

# Set Streamlit page config
st.set_page_config(
    page_title="Solana Micro-Cap Alpha Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme styling custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0b0f19;
    }
    .metric-card {
        background: rgba(18, 24, 38, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 12px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        font-family: 'Courier New', monospace;
    }
    .stat-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
    }
    .badge-green { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
    .badge-amber { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
    .badge-cyan  { background: rgba(6, 182, 212, 0.2); color: #06b6d4; border: 1px solid #06b6d4; }
</style>
""", unsafe_allow_html=True)

# Database path detection
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "scanner.db")
API_BASE = "http://127.0.0.1:80"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        # Check alternate local port 8080 fallback
        alt_path = os.path.join(os.getcwd(), "data", "scanner.db")
        if os.path.exists(alt_path):
            return sqlite3.connect(alt_path)
    return sqlite3.connect(DB_PATH)

def query_db(query: str, params=()):
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database Query Error: {e}")
        return pd.DataFrame()

# Sidebar Navigation
st.sidebar.title("⚡ Solana Alpha Lab")
st.sidebar.caption("Holder Accumulation Empirical Research System")

# Status check
daemon_status = "Unknown"
try:
    resp = requests.get(f"{API_BASE}/api/tracker/status", timeout=2)
    if resp.status_code == 200:
        data = resp.json()
        if data.get("is_daemon_running"):
            daemon_status = "🟢 24/7 Daemon Active"
        else:
            daemon_status = "🟡 Daemon Stopped"
except Exception:
    # Try port 8080 fallback
    try:
        resp = requests.get("http://127.0.0.1:8080/api/tracker/status", timeout=2)
        if resp.status_code == 200:
            API_BASE = "http://127.0.0.1:8080"
            daemon_status = "🟢 24/7 Daemon Active (:8080)"
    except Exception:
        daemon_status = "⚪ Daemon Offline"

st.sidebar.markdown(f"**Daemon Status:** {daemon_status}")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation View",
    [
        "📊 Alpha Scorecard & Hypothesis Test",
        "📡 Live In-Flight Forward Tracker",
        "🎯 Excursion Lab (MFE / MAE / Drawdown)",
        "🔍 Token Screener & Cohort Deep Dive",
        "👥 Accumulator Leaderboard & Sybil Clusters",
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Live Manual Actions")
col_b1, col_b2 = st.sidebar.columns(2)

if col_b1.button("📸 Snapshot Now"):
    try:
        r = requests.post(f"{API_BASE}/api/tracker/snapshot", timeout=5)
        st.sidebar.success(r.json().get("message", "Snapshot taken!"))
        st.rerun()
    except Exception as ex:
        st.sidebar.error(f"Failed: {ex}")

if col_b2.button("🔄 Resolve"):
    try:
        r = requests.post(f"{API_BASE}/api/tracker/resolve", timeout=5)
        st.sidebar.success(r.json().get("message", "Resolved!"))
        st.rerun()
    except Exception as ex:
        st.sidebar.error(f"Failed: {ex}")

if st.sidebar.button("⏩ Advance Clock (+6h Sim)"):
    try:
        r = requests.post(f"{API_BASE}/api/tracker/simulate-forward?hours=6.0", timeout=5)
        st.sidebar.success("Advanced simulated clock by 6 hours!")
        st.rerun()
    except Exception as ex:
        st.sidebar.error(f"Failed: {ex}")


# -------------------------------------------------------------
# VIEW 1: ALPHA SCORECARD & HYPOTHESIS TEST
# -------------------------------------------------------------
if menu == "📊 Alpha Scorecard & Hypothesis Test":
    st.title("📊 Empirical Alpha Scorecard & Hypothesis Testing")
    st.markdown("""
    **Core Question:** When a Solana micro-cap consolidates or pulls back, does repeated accumulation 
    by existing, independent holders predict subsequent outperformance?
    """)

    # Fetch scorecard data from API
    scorecard = {}
    try:
        r = requests.get(f"{API_BASE}/api/tracker/scorecard", timeout=3)
        if r.status_code == 200:
            scorecard = r.json()
    except Exception:
        pass

    obs_df = query_db("SELECT * FROM forward_observations")
    
    if obs_df.empty:
        st.warning("No observations collected yet. Run a snapshot to start collecting data.")
    else:
        total_obs = len(obs_df)
        high_accum = obs_df[obs_df["persistent_accumulators_count"] >= 3]
        dip_accum = obs_df[(obs_df["price_change_prior"] <= 0) & (obs_df["persistent_accumulators_count"] >= 2)]
        
        # Calculate returns
        obs_df["eval_return"] = obs_df["fwd_ret_24h"].fillna(obs_df["current_unrealized_return"]).fillna(0.0)
        baseline_ret = obs_df["eval_return"].mean()
        baseline_win = (obs_df["eval_return"] > 0).mean() * 100.0

        high_ret = high_accum["eval_return"].mean() if not high_accum.empty else 0.0
        high_win = ((high_accum["eval_return"] > 0).mean() * 100.0) if not high_accum.empty else 0.0
        alpha_spread = high_ret - baseline_ret
        win_edge = high_win - baseline_win

        # Hypothesis test numbers
        t_stat = scorecard.get("hypothesis_test", {}).get("t_statistic", 0.0)
        p_val = scorecard.get("hypothesis_test", {}).get("p_value", 1.0)
        is_sig = scorecard.get("hypothesis_test", {}).get("statistically_significant", False)
        verdict = scorecard.get("verdict", "Sample size accumulating.")

        # Top Metric Cards
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Sample (N)", f"{total_obs}", f"{len(high_accum)} in High Accum")
        col2.metric("Market Baseline Return", f"{baseline_ret:.2f}%", f"{baseline_win:.1f}% Win Rate")
        col3.metric("High Accum Return", f"{high_ret:.2f}%", f"{high_win:.1f}% Win Rate")
        col4.metric("Alpha Spread", f"{alpha_spread:+.2f}%", f"{win_edge:+.1f}% Win Rate Edge")
        col5.metric("Student's t-test", f"p = {p_val:.4f}", f"t = {t_stat:.2f}")

        # Hypothesis Banner
        st.markdown("---")
        if is_sig:
            st.success(f"🏆 **HYPOTHESIS CONFIRMED (p < 0.05):** {verdict}")
        else:
            st.info(f"⚖️ **HYPOTHESIS STATUS (p = {p_val:.4f}):** {verdict} *(Null Hypothesis H0 cannot be rejected at 95% confidence yet. More samples accumulating 24/7).*")

        # Visual Comparison Bar Chart
        st.subheader("Model Performance Comparison")
        
        mom_df = obs_df[obs_df["price_change_prior"] > 0]
        mom_ret = mom_df["eval_return"].mean() if not mom_df.empty else 0.0
        mom_win = ((mom_df["eval_return"] > 0).mean() * 100.0) if not mom_df.empty else 0.0

        dip_ret = dip_accum["eval_return"].mean() if not dip_accum.empty else 0.0
        dip_win = ((dip_accum["eval_return"] > 0).mean() * 100.0) if not dip_accum.empty else 0.0

        models_data = [
            {"Model": "Baseline (All Tokens)", "Mean Return (%)": baseline_ret, "Win Rate (%)": baseline_win, "N": total_obs},
            {"Model": "Model A (Persistent Accum)", "Mean Return (%)": high_ret, "Win Rate (%)": high_win, "N": len(high_accum)},
            {"Model": "Model E (Dip + Accumulation)", "Mean Return (%)": dip_ret, "Win Rate (%)": dip_win, "N": len(dip_accum)},
            {"Model": "Model C (Momentum Only)", "Mean Return (%)": mom_ret, "Win Rate (%)": mom_win, "N": len(mom_df)},
        ]
        compare_df = pd.DataFrame(models_data)

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_ret = px.bar(
                compare_df, 
                x="Model", 
                y="Mean Return (%)", 
                color="Mean Return (%)",
                color_continuous_scale=["#ef4444", "#06b6d4", "#10b981"],
                title="Forward 24h Mean Return by Model"
            )
            fig_ret.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ret, use_container_width=True)

        with col_c2:
            fig_win = px.bar(
                compare_df, 
                x="Model", 
                y="Win Rate (%)", 
                color="Win Rate (%)",
                color_continuous_scale="Viridis",
                title="Win Rate (%) Comparison"
            )
            fig_win.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_win, use_container_width=True)

        st.dataframe(compare_df, use_container_width=True)


# -------------------------------------------------------------
# VIEW 2: LIVE IN-FLIGHT FORWARD TRACKER
# -------------------------------------------------------------
elif menu == "📡 Live In-Flight Forward Tracker":
    st.title("📡 Live In-Flight Forward Return Tracker")
    st.markdown("Zero lookahead bias monitoring: Tracks tokens frozen at timestamp $T$ and logs forward price realizations.")

    obs_df = query_db("""
        SELECT 
            fo.id,
            t.symbol,
            t.name,
            fo.observation_time,
            fo.status,
            fo.setup_classification,
            fo.price_at_t,
            fo.latest_observed_price,
            fo.current_unrealized_return,
            fo.fwd_ret_1h,
            fo.fwd_ret_6h,
            fo.fwd_ret_24h,
            fo.fwd_ret_7d,
            fo.mfe_pct,
            fo.mae_pct,
            fo.persistent_accumulators_count,
            fo.cluster_adjusted_accumulators_count
        FROM forward_observations fo
        JOIN tokens t ON fo.mint_address = t.mint_address
        ORDER BY fo.observation_time DESC
    """)

    if obs_df.empty:
        st.info("No active observations. Click 'Snapshot Now' in the sidebar to start tracking live candidates.")
    else:
        # Status Filter
        status_filter = st.selectbox("Filter Status", ["ALL", "PENDING", "MATURING", "RESOLVED"])
        filtered_df = obs_df if status_filter == "ALL" else obs_df[obs_df["status"] == status_filter]

        st.markdown(f"**Showing {len(filtered_df)} observations**")
        
        # Color formatted display dataframe
        st.dataframe(
            filtered_df.style.format({
                "price_at_t": "${:.6f}",
                "latest_observed_price": "${:.6f}",
                "current_unrealized_return": "{:+.2f}%",
                "fwd_ret_1h": lambda x: f"{x:+.2f}%" if pd.notnull(x) else "⏳ Pending",
                "fwd_ret_6h": lambda x: f"{x:+.2f}%" if pd.notnull(x) else "⏳ Pending",
                "fwd_ret_24h": lambda x: f"{x:+.2f}%" if pd.notnull(x) else "⏳ Pending",
                "fwd_ret_7d": lambda x: f"{x:+.2f}%" if pd.notnull(x) else "⏳ Pending",
                "mfe_pct": "+{:.1f}%",
                "mae_pct": "{:.1f}%",
            }),
            use_container_width=True,
            height=450
        )

        # Recent Runs Log
        st.subheader("📋 Collection Daemon Run Logs")
        runs_df = query_db("SELECT * FROM tracker_runs ORDER BY run_timestamp DESC LIMIT 10")
        if not runs_df.empty:
            st.dataframe(runs_df, use_container_width=True)


# -------------------------------------------------------------
# VIEW 3: EXCURSION LAB (MFE / MAE / DRAWDOWNS)
# -------------------------------------------------------------
elif menu == "🎯 Excursion Lab (MFE / MAE / Drawdown)":
    st.title("🎯 Excursion Lab (MFE vs MAE Realities)")
    st.markdown("Micro-caps are volatile. This lab plots the Maximum Favorable Excursion (run-up) vs Maximum Adverse Excursion (drawdown).")

    obs_df = query_db("""
        SELECT 
            fo.*,
            t.symbol
        FROM forward_observations fo
        JOIN tokens t ON fo.mint_address = t.mint_address
    """)

    if not obs_df.empty:
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            fig_scatter = px.scatter(
                obs_df,
                x="mae_pct",
                y="mfe_pct",
                color="setup_classification",
                size="persistent_accumulators_count",
                hover_name="symbol",
                labels={"mae_pct": "Max Adverse Excursion (Drawdown %)", "mfe_pct": "Max Favorable Excursion (Run-up %)"},
                title="MFE vs MAE Scatter by Setup"
            )
            fig_scatter.add_hline(y=10, line_dash="dash", line_color="#10b981", annotation_text="+10% Target")
            fig_scatter.add_vline(x=-15, line_dash="dash", line_color="#ef4444", annotation_text="-15% Risk Stop")
            fig_scatter.update_layout(template="plotly_dark")
            st.plotly_chart(fig_scatter, use_container_width=True)

        with col_e2:
            fig_hist = px.histogram(
                obs_df,
                x="mfe_pct",
                color="setup_classification",
                nbins=20,
                title="Distribution of Upside Excursions (MFE %)"
            )
            fig_hist.update_layout(template="plotly_dark")
            st.plotly_chart(fig_hist, use_container_width=True)


# -------------------------------------------------------------
# VIEW 4: TOKEN SCREENER & COHORT DEEP DIVE
# -------------------------------------------------------------
elif menu == "🔍 Token Screener & Cohort Deep Dive":
    st.title("🔍 Token Screener & Accumulator Deep Dive")
    tokens_df = query_db("SELECT * FROM tokens ORDER BY market_cap_usd DESC")
    
    if not tokens_df.empty:
        selected_symbol = st.selectbox("Select Token to Deep Dive", tokens_df["symbol"].tolist())
        selected_token = tokens_df[tokens_df["symbol"] == selected_symbol].iloc[0]
        mint = selected_token["mint_address"]

        st.markdown(f"### **{selected_token['name']} (${selected_symbol})** — `{mint}`")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        col_t1.metric("Market Cap", f"${selected_token['market_cap_usd']:,.0f}")
        col_t2.metric("24h Volume", f"${selected_token['volume_24h_usd']:,.0f}")
        col_t3.metric("Price", f"${selected_token['current_price_usd']:.6f}")
        col_t4.metric("24h Change", f"{selected_token['price_change_24h']:+.2f}%")

        # Price History Chart
        snaps = query_db("SELECT * FROM token_snapshots WHERE mint_address = ? ORDER BY timestamp ASC", (mint,))
        if not snaps.empty:
            snaps["time"] = pd.to_datetime(snaps["timestamp"])
            fig_p = px.line(snaps, x="time", y="price_usd", title=f"${selected_symbol} Price History")
            fig_p.update_layout(template="plotly_dark")
            st.plotly_chart(fig_p, use_container_width=True)

        # Holder Cohorts
        st.subheader("👥 Retention & Cohort Dynamics")
        cohorts = query_db("SELECT * FROM holder_cohorts WHERE mint_address = ?", (mint,))
        if not cohorts.empty:
            st.dataframe(cohorts, use_container_width=True)


# -------------------------------------------------------------
# VIEW 5: ACCUMULATOR LEADERBOARD & SYBIL CLUSTERS
# -------------------------------------------------------------
elif menu == "👥 Accumulator Leaderboard & Sybil Clusters":
    st.title("👥 Accumulator Wallet Leaderboard & Sybil Risk")
    st.markdown("Identifies the most persistent accumulating wallets while flagging Sybil clusters funded by the same root wallet.")

    exclude_sybil = st.checkbox("Filter out clustered/Sybil wallets", value=False)
    
    query = """
        SELECT 
            wb.wallet_address,
            t.symbol,
            wb.balance,
            wb.cluster_id,
            wb.is_deployer,
            wb.is_liquidity_pool
        FROM wallet_balances wb
        JOIN tokens t ON wb.mint_address = t.mint_address
        WHERE wb.is_liquidity_pool = 0 AND wb.is_burn_address = 0
    """
    if exclude_sybil:
        query += " AND wb.cluster_id IS NULL"

    query += " ORDER BY wb.balance DESC LIMIT 50"
    wallets_df = query_db(query)
    
    if not wallets_df.empty:
        st.dataframe(wallets_df, use_container_width=True)

    st.subheader("🔗 Sybil Cluster Detections")
    clusters_df = query_db("SELECT * FROM wallet_clusters")
    if not clusters_df.empty:
        st.dataframe(clusters_df, use_container_width=True)
    else:
        st.info("No suspicious wallet clusters detected.")

st.markdown("---")
st.caption("Solana Micro-Cap Holder Accumulation Empirical Research Lab | Built for 24/7 DigitalOcean Execution")
