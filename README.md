# Solana Micro-Cap Persistent Holder Accumulation Research Engine

A quantitative research and scanning platform built for Solana micro-cap tokens. Designed to empirically answer:

> **Core Research Question:** When a relatively small Solana token is declining or consolidating, does the fact that existing holders are repeatedly increasing their positions—especially multiple independent holders accumulating over time—predict future outperformance?

---

## 🚀 Quick Start

The server is currently running locally at:
**[http://127.0.0.1:8080](http://127.0.0.1:8080)**

To manually run or restart the server:
```powershell
cd C:\Users\phkim\.gemini\antigravity-ide\scratch\solana-holder-scanner
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8080
```

---

## 🏛️ System Architecture

```
solana-holder-scanner/
├── backend/
│   ├── app.py                      # FastAPI REST application & static file mount
│   ├── config.py                   # Configurable thresholds, scoring weights & horizons
│   ├── db/
│   │   ├── schema.sql              # Relational SQLite schema with indexes & WAL mode
│   │   └── database.py             # SQLite persistence, incremental ingestion & queries
│   ├── providers/
│   │   ├── base.py                 # Pluggable Abstract Data Provider
│   │   ├── dexscreener.py          # DexScreener API integration with caching
│   │   ├── helius.py               # Helius API integration (transfers, balances, SOL funding traces)
│   │   └── simulation.py           # Realistic on-chain simulator seeded with Solana microcaps
│   └── services/
│       ├── screener.py             # Micro-cap universe filtering
│       ├── holder_analyzer.py      # Static concentration vs dynamic accumulator time series
│       ├── divergence_engine.py    # Price/holder divergence setups & absorption metrics
│       ├── clustering.py           # Wallet independence, common funder & Sybil clustering
│       ├── backtest_engine.py      # Zero look-ahead bias backtesting & Models A–F comparison
│       └── pipeline.py             # Orchestration pipeline
├── frontend/
│   ├── index.html                  # Semantic, dark glassmorphism dashboard UI
│   ├── css/
│   │   └── style.css               # Design system (Solana palette, Outfit/Inter typography)
│   └── js/
│       ├── app.js                  # Client state controller, tab router, sorting & modals
│       └── charts.js               # Responsive Chart.js engine
└── data/
    └── scanner.db                  # Persistent SQLite database (WAL mode)
```

---

## 🔬 Core Capabilities

### 1. Static vs Dynamic Holder Analysis
* **Static Concentration:** Top 5, 10, 20, 30% concentration, Gini coefficient ($0 \to 1$), supply brackets ($>\$100$, $>\$500$, $>\$1\text{k}$, $>\$5\text{k}$, $>\$10\text{k}$).
* **Dynamic Time Series:** Trajectory tracking per wallet: initial position, subsequent purchases, sales, net change, holding duration, and complete exits.

### 2. Multi-Horizon Tracking
Computes distinct metric slices across:
* `1h`, `6h`, `24h`, `3d`, `7d`, `14d`, `30d`

### 3. Critical Distinction: Existing-Holder vs New-Wallet Buying
* **Existing-Holder Accumulation:** Wallets that already held a token prior to measurement cutoff choosing to buy more.
* **New-Wallet Buying:** Wallets entering for the first time.
* Prominently tracks **Existing-Holder Net Accumulation ($ and % supply)** as the core research variable.

### 4. Non-Economic Wallet Exclusion
Excludes Raydium AMM/CLMM, Orca Whirlpools, Meteora DLMM, pump.fun bonding curves, burn accounts (`11111111111111111111111111111111`, incinerator), and deployer authorities, documenting the exact `classification_reason`.

### 5. Wallet Independence & Heuristic Clustering
* Discovers common SOL funding wallets and synchronized transaction bursts ($<120\text{s}$).
* Computes **Raw Accumulator Count** vs **Cluster-Adjusted Accumulator Count** (e.g. 10 wallets $\to$ 2 independent entities).

### 6. Neutral Research Divergence Setups
* `BULLISH_DIVERGENCE_CANDIDATE`: Price declining ($\le -5\%$), but existing holders heavily accumulating, persistent accumulators rising, high absorption pressure.
* `BREAKOUT_CONSOLIDATION_CANDIDATE`: Flat/consolidating price ($\pm 5\%$), healthy steady accumulation, repeat buyers.
* `DISTRIBUTION_CANDIDATE`: Price declining or flat, existing holders selling, large holders dumping.
* `HIGH_CLUSTER_RISK`: Apparent accumulation dominated by a single Sybil cluster.

### 7. Quantitative Backtesting (Zero Look-Ahead Bias)
* Observations are frozen at timestamp $T$, strictly utilizing data known at or before $T$.
* Forward returns calculated at $+1\text{h}, +6\text{h}, +24\text{h}, +3\text{d}, +7\text{d}, +14\text{d}, +30\text{d}$.
* Evaluates Maximum Favorable Excursion (MFE), Maximum Adverse Excursion (MAE), and Max Drawdown.
* Negative Control Models Comparison:
  * **Model A:** Price Momentum only
  * **Model B:** Volume only
  * **Model C:** Gross Holder Growth only
  * **Model D:** Persistent Holder Accumulation only
  * **Model E:** Dip Pullback + Persistent Accumulation
  * **Model F:** Full Multi-Factor Composite Model with Sybil Cluster Adjustment

### 8. Ongoing Live Forward Signal Tracker & Hypothesis Evaluation
* **Continuous Background Polling Daemon:** Runs continuously in the background, periodically freezing new snapshots at timestamp $T$ with `status = 'PENDING'`.
* **Out-of-Sample Forward Realization:** Periodically inspects active signals as time elapses, locking in forward returns at $+1\text{h}, +6\text{h}, +24\text{h}, +7\text{d}$ milestones, updating live unrealized returns, peak upside (MFE), and adverse excursion (MAE).
* **Empirical Hypothesis Scorecard:** Dynamically calculates two-sample $t$-statistics, $p$-values, and empirical outperformance vs baseline momentum models to verify whether accumulation signals actually provide forward predictive alpha.
* **Interactive Research Tools:** Provides controls in the web UI to trigger immediate snapshots (`📸 Snapshot Now`), check maturing milestones (`⚡ Check Milestones`), or advance simulated forward clocks (`⏩ Advance Clock (+6h)`).

---

## 🔌 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/tokens` | `GET` | Screened token universe with metrics for requested horizon |
| `/api/tokens/{mint}` | `GET` | Token detail, snapshots, cohort retention, top accumulators |
| `/api/wallets/leaderboard` | `GET` | Ranked accumulator leaderboard with cluster filter |
| `/api/wallets/{address}` | `GET` | Behavioral profile and transfer history for a wallet |
| `/api/backtest/results` | `GET` | Frozen historical observations & Models A–F comparison |
| `/api/tracker/status` | `GET` | Daemon polling status, pending/maturing counts, recent cycles |
| `/api/tracker/scorecard` | `GET` | Rolling out-of-sample hypothesis scorecard ($t$-stat, $p$-value) |
| `/api/tracker/active` | `GET` | Open signals pending forward realization with live unrealized PnL |
| `/api/tracker/snapshot` | `POST`| Manually freeze an observation snapshot at timestamp $T$ |
| `/api/tracker/resolve` | `POST`| Evaluate and lock maturing forward milestones |
| `/api/tracker/simulate-forward`| `POST`| Advance simulated forward clock by $N$ hours for immediate testing |
| `/api/config` | `GET`/`POST`| Inspect and update runtime thresholds & score weights |
| `/api/pipeline/refresh` | `POST`| Trigger incremental scan cycle |
