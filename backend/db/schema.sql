-- schema.sql: Relational Schema for Solana Persistent Holder Accumulation Engine

CREATE TABLE IF NOT EXISTS tokens (
    mint_address TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    decimals INTEGER NOT NULL DEFAULT 6,
    total_supply REAL NOT NULL DEFAULT 1000000000,
    circulating_supply REAL NOT NULL DEFAULT 1000000000,
    created_at TIMESTAMP NOT NULL,
    deployer_address TEXT,
    dex_pair_address TEXT,
    liquidity_usd REAL DEFAULT 0,
    market_cap_usd REAL DEFAULT 0,
    current_price_usd REAL DEFAULT 0,
    volume_24h_usd REAL DEFAULT 0,
    price_change_24h REAL DEFAULT 0,
    holder_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS token_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    price_usd REAL NOT NULL,
    market_cap_usd REAL,
    liquidity_usd REAL,
    volume_usd REAL,
    holder_count INTEGER,
    top_10_concentration REAL,
    FOREIGN KEY (mint_address) REFERENCES tokens(mint_address)
);

CREATE INDEX IF NOT EXISTS idx_token_snapshots_mint_time ON token_snapshots(mint_address, timestamp);

CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    first_seen_at TIMESTAMP NOT NULL,
    funding_wallet TEXT,
    is_excluded INTEGER DEFAULT 0,
    classification_reason TEXT, -- 'LP_POOL', 'BURN_ADDRESS', 'DEPLOYER', 'EXCHANGE', 'ROUTER', etc.
    last_active_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_clusters (
    cluster_id TEXT PRIMARY KEY,
    primary_funding_wallet TEXT,
    wallet_count INTEGER DEFAULT 1,
    confidence_score REAL DEFAULT 0.5,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_cluster_members (
    wallet_address TEXT PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address),
    FOREIGN KEY (cluster_id) REFERENCES wallet_clusters(cluster_id)
);

CREATE TABLE IF NOT EXISTS transfers (
    signature TEXT PRIMARY KEY,
    mint_address TEXT NOT NULL,
    from_address TEXT NOT NULL,
    to_address TEXT NOT NULL,
    amount REAL NOT NULL,
    usd_value REAL DEFAULT 0,
    timestamp TIMESTAMP NOT NULL,
    tx_type TEXT DEFAULT 'TRANSFER', -- 'BUY', 'SELL', 'TRANSFER', 'MINT', 'BURN'
    slot INTEGER,
    FOREIGN KEY (mint_address) REFERENCES tokens(mint_address)
);

CREATE INDEX IF NOT EXISTS idx_transfers_mint_time ON transfers(mint_address, timestamp);
CREATE INDEX IF NOT EXISTS idx_transfers_to ON transfers(to_address);
CREATE INDEX IF NOT EXISTS idx_transfers_from ON transfers(from_address);

CREATE TABLE IF NOT EXISTS wallet_token_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    balance REAL NOT NULL,
    usd_value REAL DEFAULT 0,
    UNIQUE(wallet_address, mint_address, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_wtb_wallet_mint ON wallet_token_balances(wallet_address, mint_address);

CREATE TABLE IF NOT EXISTS token_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    time_horizon TEXT NOT NULL, -- '1h', '6h', '24h', '3d', '7d', '14d', '30d'
    
    -- Holder statistics
    total_holders INTEGER NOT NULL,
    holder_growth_rate REAL DEFAULT 0,
    median_holder_balance REAL DEFAULT 0,
    mean_holder_balance REAL DEFAULT 0,
    p75_holder_balance REAL DEFAULT 0,
    p90_holder_balance REAL DEFAULT 0,
    holders_above_100_usd INTEGER DEFAULT 0,
    holders_above_500_usd INTEGER DEFAULT 0,
    holders_above_1k_usd INTEGER DEFAULT 0,
    holders_above_5k_usd INTEGER DEFAULT 0,
    holders_above_10k_usd INTEGER DEFAULT 0,
    
    -- Concentration
    top_5_percent REAL DEFAULT 0,
    top_10_percent REAL DEFAULT 0,
    top_20_percent REAL DEFAULT 0,
    top_30_percent REAL DEFAULT 0,
    gini_coefficient REAL DEFAULT 0,
    delta_top_10_concentration REAL DEFAULT 0,
    
    -- Accumulation dynamics
    net_accumulators_count INTEGER DEFAULT 0,
    persistent_accumulators_count INTEGER DEFAULT 0,
    cluster_adjusted_accumulators_count INTEGER DEFAULT 0,
    pct_meaningful_holders_accumulating REAL DEFAULT 0,
    usd_value_accumulated REAL DEFAULT 0,
    tokens_accumulated REAL DEFAULT 0,
    pct_circulating_supply_accumulated REAL DEFAULT 0,
    avg_accumulation_usd REAL DEFAULT 0,
    median_accumulation_usd REAL DEFAULT 0,
    
    repeat_buyers_2plus INTEGER DEFAULT 0,
    repeat_buyers_3plus INTEGER DEFAULT 0,
    repeat_buyers_5plus INTEGER DEFAULT 0,
    
    -- Distribution dynamics
    net_sellers_count INTEGER DEFAULT 0,
    usd_value_sold REAL DEFAULT 0,
    pct_circulating_supply_sold REAL DEFAULT 0,
    full_exits_count INTEGER DEFAULT 0,
    reduced_gt_25pct_count INTEGER DEFAULT 0,
    reduced_gt_50pct_count INTEGER DEFAULT 0,
    reduced_gt_75pct_count INTEGER DEFAULT 0,
    
    -- Existing-holder accumulation vs New wallets (CRITICAL)
    existing_holder_net_accum_usd REAL DEFAULT 0,
    existing_holder_net_accum_tokens REAL DEFAULT 0,
    existing_holder_accum_pct_supply REAL DEFAULT 0,
    new_wallet_net_accum_usd REAL DEFAULT 0,
    
    -- Absorption & Pressure
    accumulation_distribution_pressure REAL DEFAULT 0,
    accum_relative_to_volume REAL DEFAULT 0,
    accum_relative_to_supply REAL DEFAULT 0,
    
    -- Price & Divergence setup
    price_change_horizon REAL DEFAULT 0,
    divergence_setup TEXT DEFAULT 'NEUTRAL', -- 'BULLISH_DIVERGENCE', 'DISTRIBUTION', 'BREAKOUT_CONSOLIDATION', 'NEUTRAL'
    holder_accumulation_score REAL DEFAULT 0,
    
    FOREIGN KEY (mint_address) REFERENCES tokens(mint_address)
);

CREATE INDEX IF NOT EXISTS idx_metrics_mint_time_horizon ON token_metrics(mint_address, timestamp, time_horizon);

CREATE TABLE IF NOT EXISTS cohort_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint_address TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    cohort_bracket TEXT NOT NULL, -- '<24h', '1-3d', '3-7d', '7-30d', '>30d'
    wallet_count INTEGER DEFAULT 0,
    retention_rate REAL DEFAULT 0,
    net_accum_usd REAL DEFAULT 0,
    net_distrib_usd REAL DEFAULT 0,
    avg_position_change_pct REAL DEFAULT 0,
    FOREIGN KEY (mint_address) REFERENCES tokens(mint_address)
);

CREATE TABLE IF NOT EXISTS backtest_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mint_address TEXT NOT NULL,
    observation_time TIMESTAMP NOT NULL,
    time_horizon TEXT NOT NULL,
    
    -- Frozen features at observation time T (Zero Look-Ahead)
    price_at_t REAL NOT NULL,
    mcap_at_t REAL,
    vol_24h_at_t REAL,
    price_change_prior REAL,
    existing_holder_net_accum_usd REAL,
    persistent_accumulators_count INTEGER,
    cluster_adjusted_accumulators_count INTEGER,
    accumulation_pressure REAL,
    accum_relative_to_volume REAL,
    holder_retention_rate REAL,
    concentration_top_10 REAL,
    composite_score REAL,
    setup_classification TEXT,
    
    -- Future Price Realizations at T + Horizon
    fwd_ret_1h REAL,
    fwd_ret_6h REAL,
    fwd_ret_24h REAL,
    fwd_ret_3d REAL,
    fwd_ret_7d REAL,
    fwd_ret_14d REAL,
    fwd_ret_30d REAL,
    
    -- Excursion statistics over 7-day window
    mfe_pct REAL, -- Max Favorable Excursion
    mae_pct REAL, -- Max Adverse Excursion
    max_drawdown_pct REAL,
    
    -- Hit triggers
    hit_plus_10 INTEGER DEFAULT 0,
    hit_plus_25 INTEGER DEFAULT 0,
    hit_plus_50 INTEGER DEFAULT 0,
    hit_plus_100 INTEGER DEFAULT 0,
    hit_minus_10 INTEGER DEFAULT 0,
    hit_minus_25 INTEGER DEFAULT 0,
    hit_minus_50 INTEGER DEFAULT 0,

    -- Ongoing Forward Tracking & State Realization
    status TEXT DEFAULT 'RESOLVED', -- 'PENDING', 'MATURING', 'RESOLVED'
    source TEXT DEFAULT 'HISTORICAL_SEED', -- 'LIVE_SCAN', 'HISTORICAL_SEED'
    current_unrealized_return REAL DEFAULT 0.0,
    latest_observed_price REAL,
    last_evaluated_at TIMESTAMP,
    is_resolved_1h INTEGER DEFAULT 1,
    is_resolved_6h INTEGER DEFAULT 1,
    is_resolved_24h INTEGER DEFAULT 1,
    is_resolved_7d INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_backtest_mint_obs ON backtest_observations(mint_address, observation_time);
CREATE INDEX IF NOT EXISTS idx_backtest_status ON backtest_observations(status);

CREATE TABLE IF NOT EXISTS tracker_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TIMESTAMP NOT NULL,
    tokens_evaluated INTEGER DEFAULT 0,
    new_observations_created INTEGER DEFAULT 0,
    matured_observations_updated INTEGER DEFAULT 0,
    active_tracking_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0
);
