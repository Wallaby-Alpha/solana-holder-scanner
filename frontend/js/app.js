/**
 * app.js: Main Client Application Controller
 * Manages UI state, data fetching, sorting, filtering, modals, and tab navigation.
 */

(function () {
    const state = {
        currentHorizon: '24h',
        currentTab: 'tab-screener',
        tokens: [],
        sortColumn: 'holder_accumulation_score',
        sortAsc: false,
        setupFilter: 'ALL',
        searchQuery: '',
        selectedMint: null,
        tokenDetail: null,
        leaderboardData: [],
        filterClusteredLeaderboard: false,
        backtestData: null,
        backtestHorizon: 'fwd_ret_24h'
    };

    // DOM Elements
    const elements = {
        navTabs: document.querySelectorAll('.nav-tab'),
        tabViews: document.querySelectorAll('.tab-view'),
        horizonBtns: document.querySelectorAll('.horizon-btn'),
        tokensTableBody: document.getElementById('tokens-table-body'),
        filterSetupSelect: document.getElementById('filter-setup-select'),
        searchTokenInput: document.getElementById('search-token-input'),
        btnOpenConfig: document.getElementById('btn-open-config'),
        btnRefreshScan: document.getElementById('btn-refresh-scan'),
        configModalBackdrop: document.getElementById('config-modal-backdrop'),
        btnCloseModal: document.getElementById('btn-close-modal'),
        btnCancelConfig: document.getElementById('btn-cancel-config'),
        btnSaveConfig: document.getElementById('btn-save-config'),
        walletModalBackdrop: document.getElementById('wallet-modal-backdrop'),
        btnCloseWalletModal: document.getElementById('btn-close-wallet-modal'),
        walletModalBody: document.getElementById('wallet-modal-body'),
        toggleFilterClustered: document.getElementById('toggle-filter-clustered'),
        leaderboardTableBody: document.getElementById('leaderboard-table-body'),
        backtestHorizonSelect: document.getElementById('backtest-horizon-select'),
        btnRecomputeBacktest: document.getElementById('btn-recompute-backtest'),
        modelsTableBody: document.getElementById('models-table-body'),
        tbodyObservationsLog: document.getElementById('tbody-observations-log'),
        verdictTitle: document.getElementById('verdict-title'),
        verdictText: document.getElementById('verdict-text'),
        // KPIs
        valTrackedTokens: document.getElementById('val-tracked-tokens'),
        valBullishSetups: document.getElementById('val-bullish-setups'),
        valBreakoutSetups: document.getElementById('val-breakout-setups'),
        valPersistentAccumulators: document.getElementById('val-persistent-accumulators'),
        valClusterEntities: document.getElementById('val-cluster-entities'),
        // Ongoing Tracker Elements
        btnTrackerSnapshot: document.getElementById('btn-tracker-snapshot'),
        btnTrackerResolve: document.getElementById('btn-tracker-resolve'),
        btnTrackerSimulate: document.getElementById('btn-tracker-simulate'),
        trackerDaemonStatus: document.getElementById('tracker-daemon-status'),
        trackerLastRun: document.getElementById('tracker-last-run'),
        trackerPendingCount: document.getElementById('tracker-pending-count'),
        trackerTotalObs: document.getElementById('tracker-total-obs'),
        trackerOutperfVal: document.getElementById('tracker-outperf-val'),
        trackerPVal: document.getElementById('tracker-p-val'),
        trackerVerdictTitle: document.getElementById('tracker-verdict-title'),
        trackerVerdictText: document.getElementById('tracker-verdict-text'),
        trackerScorecardTbody: document.getElementById('tracker-scorecard-tbody'),
        tbodyActiveSignals: document.getElementById('tbody-active-signals')
    };

    // =========================================================================
    // INITIALIZATION
    // =========================================================================
    async function init() {
        bindEvents();
        await fetchTokens();
        await fetchBacktestResults();
    }

    function bindEvents() {
        // Tab switching
        elements.navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-tab');
                switchTab(targetTab);
            });
        });

        // Horizon selection
        elements.horizonBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                elements.horizonBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.currentHorizon = btn.getAttribute('data-horizon');
                fetchTokens();
                if (state.selectedMint) {
                    fetchTokenDetail(state.selectedMint);
                }
            });
        });

        // Filters & Search
        if (elements.filterSetupSelect) {
            elements.filterSetupSelect.addEventListener('change', (e) => {
                state.setupFilter = e.target.value;
                renderTokensTable();
            });
        }

        if (elements.searchTokenInput) {
            elements.searchTokenInput.addEventListener('input', (e) => {
                state.searchQuery = e.target.value.toLowerCase().trim();
                renderTokensTable();
            });
        }

        // Table column sorting
        document.querySelectorAll('#tokens-data-table th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.getAttribute('data-sort');
                if (state.sortColumn === col) {
                    state.sortAsc = !state.sortAsc;
                } else {
                    state.sortColumn = col;
                    state.sortAsc = false;
                }
                renderTokensTable();
            });
        });

        // Config Modal
        if (elements.btnOpenConfig) {
            elements.btnOpenConfig.addEventListener('click', openConfigModal);
        }
        if (elements.btnCloseModal) {
            elements.btnCloseModal.addEventListener('click', closeConfigModal);
        }
        if (elements.btnCancelConfig) {
            elements.btnCancelConfig.addEventListener('click', closeConfigModal);
        }
        if (elements.btnSaveConfig) {
            elements.btnSaveConfig.addEventListener('click', saveConfig);
        }

        // Wallet Modal Close
        if (elements.btnCloseWalletModal) {
            elements.btnCloseWalletModal.addEventListener('click', closeWalletModal);
        }
        window.addEventListener('click', (e) => {
            if (e.target === elements.configModalBackdrop) closeConfigModal();
            if (e.target === elements.walletModalBackdrop) closeWalletModal();
        });

        // Rescan / Refresh
        if (elements.btnRefreshScan) {
            elements.btnRefreshScan.addEventListener('click', triggerRescan);
        }

        // Leaderboard filter
        if (elements.toggleFilterClustered) {
            elements.toggleFilterClustered.addEventListener('change', (e) => {
                state.filterClusteredLeaderboard = e.target.checked;
                fetchLeaderboard();
            });
        }

        // Backtest controls
        if (elements.backtestHorizonSelect) {
            elements.backtestHorizonSelect.addEventListener('change', (e) => {
                state.backtestHorizon = e.target.value;
                fetchBacktestResults();
            });
        }
        if (elements.btnRecomputeBacktest) {
            elements.btnRecomputeBacktest.addEventListener('click', fetchBacktestResults);
        }

        // Live Ongoing Tracker Controls
        if (elements.btnTrackerSnapshot) {
            elements.btnTrackerSnapshot.addEventListener('click', handleTrackerSnapshot);
        }
        if (elements.btnTrackerResolve) {
            elements.btnTrackerResolve.addEventListener('click', handleTrackerResolve);
        }
        if (elements.btnTrackerSimulate) {
            elements.btnTrackerSimulate.addEventListener('click', handleTrackerSimulate);
        }
    }

    function switchTab(tabId) {
        state.currentTab = tabId;
        elements.navTabs.forEach(tab => {
            tab.classList.toggle('active', tab.getAttribute('data-tab') === tabId);
        });
        elements.tabViews.forEach(view => {
            view.classList.toggle('active', view.id === tabId);
        });

        if (tabId === 'tab-leaderboard') {
            fetchLeaderboard();
        } else if (tabId === 'tab-backtest') {
            fetchBacktestResults();
        } else if (tabId === 'tab-tracker') {
            fetchTrackerData();
        }
    }

    // =========================================================================
    // DATA FETCHING & RENDERING: SCREENER
    // =========================================================================
    async function fetchTokens() {
        try {
            const url = `/api/tokens?horizon=${state.currentHorizon}`;
            const res = await fetch(url);
            const data = await res.json();
            state.tokens = data.tokens || [];
            
            updateKPICards();
            renderTokensTable();

            // Set default deep dive token if none selected
            if (!state.selectedMint && state.tokens.length > 0) {
                // Prioritize Bullish Divergence token
                const bullToken = state.tokens.find(t => t.divergence_setup === 'BULLISH_DIVERGENCE_CANDIDATE') || state.tokens[0];
                selectTokenForDeepDive(bullToken.mint_address);
            }
        } catch (err) {
            console.error('Error fetching tokens:', err);
        }
    }

    function updateKPICards() {
        if (!state.tokens) return;
        const total = state.tokens.length;
        const bullish = state.tokens.filter(t => t.divergence_setup === 'BULLISH_DIVERGENCE_CANDIDATE').length;
        const breakout = state.tokens.filter(t => t.divergence_setup === 'BREAKOUT_CONSOLIDATION_CANDIDATE').length;
        const persistentSum = state.tokens.reduce((acc, t) => acc + (t.persistent_accumulators_count || 0), 0);
        const clusterSum = state.tokens.reduce((acc, t) => acc + (t.cluster_adjusted_accumulators_count || 0), 0);

        if (elements.valTrackedTokens) elements.valTrackedTokens.textContent = total;
        if (elements.valBullishSetups) elements.valBullishSetups.textContent = bullish;
        if (elements.valBreakoutSetups) elements.valBreakoutSetups.textContent = breakout;
        if (elements.valPersistentAccumulators) elements.valPersistentAccumulators.textContent = persistentSum;
        if (elements.valClusterEntities) elements.valClusterEntities.textContent = clusterSum;
    }

    function renderTokensTable() {
        const tbody = elements.tokensTableBody;
        if (!tbody) return;
        tbody.innerHTML = '';

        // Filter
        let filtered = state.tokens.filter(t => {
            if (state.setupFilter !== 'ALL' && t.divergence_setup !== state.setupFilter) return false;
            if (state.searchQuery) {
                const q = state.searchQuery;
                const matchSym = (t.symbol || '').toLowerCase().includes(q);
                const matchName = (t.name || '').toLowerCase().includes(q);
                const matchMint = (t.mint_address || '').toLowerCase().includes(q);
                if (!matchSym && !matchName && !matchMint) return false;
            }
            return true;
        });

        // Sort
        filtered.sort((a, b) => {
            let valA = a[state.sortColumn];
            let valB = b[state.sortColumn];
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            if (valA < valB) return state.sortAsc ? -1 : 1;
            if (valA > valB) return state.sortAsc ? 1 : -1;
            return 0;
        });

        if (filtered.length === 0) {
            tbody.innerHTML = `<tr><td colspan="16" style="text-align:center; padding: 24px; color: var(--text-muted);">No micro-caps found matching current filters.</td></tr>`;
            return;
        }

        filtered.forEach(t => {
            const tr = document.createElement('tr');
            
            // Format Price Change
            const pChg = t.price_change_24h || 0;
            const pChgClass = pChg >= 0 ? 'text-bull' : 'text-bear';
            const pChgStr = (pChg >= 0 ? '+' : '') + pChg.toFixed(1) + '%';

            // Setup Badge
            const setupBadge = getSetupBadgeHTML(t.divergence_setup);
            const scoreClass = t.holder_accumulation_score >= 70 ? 'score-high' : (t.holder_accumulation_score >= 45 ? 'score-mid' : 'score-low');

            tr.innerHTML = `
                <td>
                    <strong>${t.symbol}</strong>
                    <div style="font-size:0.7rem; color:var(--text-muted);">${t.token_age_days || 14}d old</div>
                </td>
                <td>$${formatPrice(t.current_price_usd)}</td>
                <td class="${pChgClass}">${pChgStr}</td>
                <td>$${formatNumber(t.market_cap_usd)}</td>
                <td>$${formatNumber(t.liquidity_usd)}</td>
                <td>$${formatNumber(t.volume_24h_usd)}</td>
                <td>${t.holder_count}</td>
                <td>${(t.top_10_percent || 0).toFixed(1)}%</td>
                <td class="highlight-col">+$${formatNumber(t.existing_holder_net_accum_usd)}</td>
                <td>${(t.existing_holder_accum_pct_supply || 0).toFixed(2)}%</td>
                <td><strong>${t.persistent_accumulators_count}</strong></td>
                <td><span style="color:var(--sol-purple); font-weight:600;">${t.cluster_adjusted_accumulators_count}</span></td>
                <td>${(t.accumulation_distribution_pressure || 1.0).toFixed(1)}x</td>
                <td><span class="score-pill ${scoreClass}">${(t.holder_accumulation_score || 50).toFixed(1)}</span></td>
                <td>${setupBadge}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="window.selectDeepDiveToken('${t.mint_address}')">
                        🔬 Analyze
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    function getSetupBadgeHTML(setup) {
        switch (setup) {
            case 'BULLISH_DIVERGENCE_CANDIDATE':
                return `<span class="setup-badge badge-bullish-divergence">BULLISH DIVERGENCE</span>`;
            case 'BREAKOUT_CONSOLIDATION_CANDIDATE':
                return `<span class="setup-badge badge-breakout-consolidation">BREAKOUT CONSOLIDATION</span>`;
            case 'DISTRIBUTION_CANDIDATE':
                return `<span class="setup-badge badge-distribution">DISTRIBUTION RISK</span>`;
            case 'HIGH_CLUSTER_RISK':
                return `<span class="setup-badge badge-sybil-risk">SYBIL CLUSTER RISK</span>`;
            default:
                return `<span class="setup-badge badge-neutral">NEUTRAL</span>`;
        }
    }

    // =========================================================================
    // DATA FETCHING & RENDERING: TOKEN DEEP DIVE
    // =========================================================================
    window.selectDeepDiveToken = function(mint) {
        state.selectedMint = mint;
        switchTab('tab-deepdive');
        fetchTokenDetail(mint);
    };

    async function fetchTokenDetail(mint) {
        try {
            const url = `/api/tokens/${mint}?horizon=${state.currentHorizon}`;
            const res = await fetch(url);
            const data = await res.json();
            state.tokenDetail = data;
            renderTokenDetail(data);
        } catch (err) {
            console.error('Error fetching token detail:', err);
        }
    }

    function renderTokenDetail(data) {
        const token = data.token;
        const metrics = data.current_metrics;
        
        // Header
        document.getElementById('deepdive-symbol').textContent = token.symbol;
        document.getElementById('deepdive-name').textContent = token.name;
        document.getElementById('deepdive-category').textContent = token.category || 'TOKEN';
        document.getElementById('deepdive-mint').textContent = token.mint_address;

        const setupBadge = document.getElementById('deepdive-setup-badge');
        if (setupBadge) {
            setupBadge.className = 'badge';
            setupBadge.innerHTML = getSetupBadgeHTML(metrics ? metrics.divergence_setup : 'NEUTRAL');
        }

        // Metrics Strip
        document.getElementById('strip-price').textContent = `$${formatPrice(token.current_price_usd)}`;
        const pChg = token.price_change_24h || 0;
        const pChgEl = document.getElementById('strip-price-chg');
        pChgEl.textContent = (pChg >= 0 ? '+' : '') + pChg.toFixed(1) + '%';
        pChgEl.className = 'strip-val ' + (pChg >= 0 ? 'text-bull' : 'text-bear');
        document.getElementById('strip-mcap').textContent = `$${formatNumber(token.market_cap_usd)}`;
        document.getElementById('strip-score').textContent = (metrics ? metrics.holder_accumulation_score : 50).toFixed(1);
        document.getElementById('strip-pressure').textContent = `${(metrics ? metrics.accumulation_distribution_pressure : 1.0).toFixed(1)}x`;

        // Render Charts
        window.AppCharts.renderPriceDivergenceChart('chart-price-divergence', data.price_history, metrics);
        window.AppCharts.renderHolderBehaviorChart('chart-holder-behavior', metrics);
        window.AppCharts.renderCohortRetentionChart('chart-cohort-retention', data.cohorts);
        window.AppCharts.renderConcentrationChart('chart-concentration', metrics);

        // Render Top Accumulators Table
        const tbodyAcc = document.getElementById('tbody-token-accumulators');
        tbodyAcc.innerHTML = '';
        (data.top_accumulators || []).forEach(acc => {
            const tr = document.createElement('tr');
            const clusterLabel = acc.is_clustered ? `<span style="color:var(--sol-purple)">Cluster: ${acc.cluster_id}</span>` : `<span style="color:var(--color-bull)">Independent</span>`;
            tr.innerHTML = `
                <td>
                    <code style="cursor:pointer; color:var(--text-accent);" onclick="window.viewWalletDetail('${acc.address}')">${shortenAddress(acc.address)}</code>
                </td>
                <td>${acc.buys_count}</td>
                <td>${acc.sells_count}</td>
                <td class="text-bull">+$${formatNumber(acc.net_usd)}</td>
                <td>$${formatNumber(acc.current_position_usd)}</td>
                <td>${acc.is_persistent ? '<span class="score-pill score-high">PERSISTENT</span>' : 'Standard'}</td>
                <td>${clusterLabel}</td>
            `;
            tbodyAcc.appendChild(tr);
        });

        // Render Top Distributors Table
        const tbodyDist = document.getElementById('tbody-token-distributors');
        tbodyDist.innerHTML = '';
        (data.top_distributors || []).forEach(dist => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <code style="cursor:pointer; color:var(--text-accent);" onclick="window.viewWalletDetail('${dist.address}')">${shortenAddress(dist.address)}</code>
                </td>
                <td>${dist.sells_count}</td>
                <td class="text-bear">-$${formatNumber(dist.net_usd_sold)}</td>
                <td>${dist.reduction_pct}%</td>
                <td>${dist.is_full_exit ? '<span class="score-pill score-low">FULL EXIT</span>' : 'Partial'}</td>
            `;
            tbodyDist.appendChild(tr);
        });

        // Render Clusters
        const clusterContainer = document.getElementById('cluster-details-container');
        clusterContainer.innerHTML = '';
        const clusters = data.clusters || [];
        if (clusters.length === 0) {
            clusterContainer.innerHTML = `<div style="color:var(--text-muted); padding:10px;">No suspicious or co-funded wallet clusters detected for this token. Wallets exhibit high independence.</div>`;
        } else {
            clusters.forEach(c => {
                const members = (c.members || '').split(',');
                const card = document.createElement('div');
                card.className = 'cluster-card';
                card.innerHTML = `
                    <div class="cluster-card-title">
                        <span>Cluster: ${c.cluster_id}</span>
                        <span>${members.length} Wallets</span>
                    </div>
                    <div class="cluster-card-body">
                        <div><strong>Reason:</strong> ${c.reason || 'COMMON_FUNDER'}</div>
                        <div><strong>Primary Funder:</strong> ${shortenAddress(c.primary_funding_wallet)}</div>
                        <div style="margin-top:4px;"><strong>Confidence:</strong> ${(c.confidence_score * 100).toFixed(0)}%</div>
                    </div>
                `;
                clusterContainer.appendChild(card);
            });
        }
    }

    // =========================================================================
    // DATA FETCHING & RENDERING: LEADERBOARD
    // =========================================================================
    async function fetchLeaderboard() {
        try {
            const mint = state.selectedMint || '';
            const url = `/api/wallets/leaderboard?mint=${mint}&filter_clustered=${state.filterClusteredLeaderboard}`;
            const res = await fetch(url);
            const data = await res.json();
            renderLeaderboard(data.leaderboard || []);
        } catch (err) {
            console.error('Error fetching leaderboard:', err);
        }
    }

    function renderLeaderboard(wallets) {
        const tbody = elements.leaderboardTableBody;
        if (!tbody) return;
        tbody.innerHTML = '';

        if (wallets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 24px; color:var(--text-muted);">No accumulating wallets match the criteria.</td></tr>`;
            return;
        }

        wallets.forEach(w => {
            const tr = document.createElement('tr');
            const persistenceBadge = w.is_persistent ? `<span class="score-pill score-high">PERSISTENT ACCUMULATOR</span>` : `<span class="score-pill score-mid">NET ACCUMULATOR</span>`;
            const clusterStatus = w.is_clustered ? `<span style="color:var(--sol-purple);">Clustered (${w.cluster_id})</span>` : `<span style="color:var(--color-bull)">Independent</span>`;
            
            tr.innerHTML = `
                <td><code>${shortenAddress(w.address)}</code></td>
                <td><strong>${w.symbol || 'TOKEN'}</strong></td>
                <td>${w.purchases}</td>
                <td>${w.sales}</td>
                <td class="text-bull">+$${formatNumber(w.net_usd)}</td>
                <td>$${formatNumber(w.current_position_usd)}</td>
                <td>${persistenceBadge}</td>
                <td>${w.is_existing_holder ? '✅ Existing' : '🆕 New Entrant'}</td>
                <td>${clusterStatus}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="window.viewWalletDetail('${w.address}')">
                        Inspect
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // =========================================================================
    // DATA FETCHING & RENDERING: BACKTEST LAB (MODELS A-F)
    // =========================================================================
    async function fetchBacktestResults() {
        try {
            const url = `/api/backtest/results?horizon=${state.backtestHorizon}`;
            const res = await fetch(url);
            const data = await res.json();
            state.backtestData = data;
            renderBacktestView(data);
        } catch (err) {
            console.error('Error fetching backtest results:', err);
        }
    }

    function renderBacktestView(data) {
        if (!data) return;

        // Verdict banner
        const verdict = data.verdict || {};
        if (elements.verdictTitle) {
            elements.verdictTitle.textContent = verdict.hypothesis_validated ?
                "HYPOTHESIS VALIDATED: PERSISTENT HOLDER ACCUMULATION GENERATES STATISTICAL ALPHA" :
                "RESEARCH CONCLUSION: HOLDER ACCUMULATION REQUIRES SYBIL-CLUSTER FILTERING";
        }
        if (elements.verdictText) {
            elements.verdictText.textContent = verdict.summary_verdict || "Statistical evaluation complete.";
        }

        // Models table (Models A through F)
        const tbodyModels = elements.modelsTableBody;
        if (tbodyModels) {
            tbodyModels.innerHTML = '';
            (data.models_comparison || []).forEach(m => {
                const tr = document.createElement('tr');
                const outperf = m.outperformance_vs_baseline;
                const outperfClass = outperf > 0 ? 'text-bull' : (outperf < 0 ? 'text-bear' : '');
                const outperfStr = (outperf > 0 ? '+' : '') + outperf.toFixed(1) + '%';
                
                tr.innerHTML = `
                    <td><strong>${m.model}</strong></td>
                    <td style="color:var(--text-muted); font-size:0.75rem;">${m.description}</td>
                    <td>${m.trade_count}</td>
                    <td>${m.win_rate_pct}%</td>
                    <td class="${m.mean_forward_return_pct >= 0 ? 'text-bull' : 'text-bear'}">${m.mean_forward_return_pct >= 0 ? '+' : ''}${m.mean_forward_return_pct}%</td>
                    <td>${m.median_forward_return_pct >= 0 ? '+' : ''}${m.median_forward_return_pct}%</td>
                    <td><strong>${m.sharpe_ratio}</strong></td>
                    <td class="${outperfClass} highlight-col">${outperfStr}</td>
                    <td class="text-bull">${m.hit_plus_25_pct}%</td>
                    <td class="text-bear">${m.hit_minus_25_pct}%</td>
                    <td><span class="score-pill ${outperf > 5 ? 'score-high' : 'score-mid'}">${m.statistical_conclusion.split(':')[0]}</span></td>
                `;
                tbodyModels.appendChild(tr);
            });
        }

        // Excursion & Comparative Charts
        window.AppCharts.renderExcursionChart('chart-excursion-distribution', data.recent_observations);
        window.AppCharts.renderModelReturnsChart('chart-model-returns', data.models_comparison);

        // Observations log
        const tbodyObs = elements.tbodyObservationsLog;
        if (tbodyObs) {
            tbodyObs.innerHTML = '';
            (data.recent_observations || []).slice(0, 15).forEach(o => {
                const tr = document.createElement('tr');
                const fwd24 = o.fwd_ret_24h !== null ? ((o.fwd_ret_24h >= 0 ? '+' : '') + o.fwd_ret_24h + '%') : 'N/A';
                const fwd7d = o.fwd_ret_7d !== null ? ((o.fwd_ret_7d >= 0 ? '+' : '') + o.fwd_ret_7d + '%') : 'N/A';
                
                tr.innerHTML = `
                    <td>${formatDate(o.observation_time)}</td>
                    <td><code>${shortenAddress(o.mint_address)}</code></td>
                    <td>$${formatPrice(o.price_at_t)}</td>
                    <td class="${o.price_change_prior >= 0 ? 'text-bull' : 'text-bear'}">${(o.price_change_prior >= 0 ? '+' : '')}${o.price_change_prior}%</td>
                    <td class="text-bull">+$${formatNumber(o.existing_holder_net_accum_usd)}</td>
                    <td>${o.persistent_accumulators_count}</td>
                    <td>${(o.accumulation_pressure || 1.0).toFixed(1)}x</td>
                    <td>${getSetupBadgeHTML(o.setup_classification)}</td>
                    <td class="${o.fwd_ret_24h >= 0 ? 'text-bull' : 'text-bear'}">${fwd24}</td>
                    <td class="${o.fwd_ret_7d >= 0 ? 'text-bull' : 'text-bear'}">${fwd7d}</td>
                    <td class="text-bull">+${o.mfe_pct}%</td>
                    <td class="text-bear">${o.mae_pct}%</td>
                `;
                tbodyObs.appendChild(tr);
            });
        }
    }

    // =========================================================================
    // WALLET DRILLDOWN & CONFIG MODALS
    // =========================================================================
    window.viewWalletDetail = async function(address) {
        try {
            const res = await fetch(`/api/wallets/${address}`);
            const data = await res.json();
            
            const body = elements.walletModalBody;
            body.innerHTML = `
                <div style="margin-bottom:16px;">
                    <div style="font-size:0.75rem; color:var(--text-muted);">WALLET ADDRESS</div>
                    <code style="font-size:0.95rem; color:#fff; word-break:break-all;">${data.address}</code>
                </div>
                <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom:18px;">
                    <div class="kpi-card">
                        <span class="kpi-title">Total Purchases</span>
                        <span class="kpi-value">${data.total_buys}</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-title">Total Sales</span>
                        <span class="kpi-value">${data.total_sells}</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-title">Total Bought</span>
                        <span class="kpi-value text-bull">$${formatNumber(data.total_usd_bought)}</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-title">Total Sold</span>
                        <span class="kpi-value text-bear">$${formatNumber(data.total_usd_sold)}</span>
                    </div>
                </div>
                <div style="margin-bottom:14px; background:rgba(0,0,0,0.3); padding:12px; border-radius:8px;">
                    <div><strong>Behavioral Classification:</strong> ${data.is_persistent_accumulator ? '<span class="score-pill score-high">PERSISTENT ACCUMULATOR</span>' : '<span class="score-pill score-mid">STANDARD PARTICIPANT</span>'}</div>
                    <div style="margin-top:6px;"><strong>Excluded Non-Economic Account:</strong> ${data.is_excluded ? `<span style="color:var(--color-bear)">YES (${data.classification_reason})</span>` : 'NO (Active Economic Participant)'}</div>
                    <div style="margin-top:6px;"><strong>Cluster Affiliation:</strong> ${data.cluster ? `<span style="color:var(--sol-purple)">Affiliated with ${data.cluster.cluster_id} (${data.cluster.reason})</span>` : '<span style="color:var(--color-bull)">Independent Unclustered Wallet</span>'}</div>
                </div>
                <h4 style="margin-bottom:8px; color:var(--text-secondary);">Recent On-Chain Transfers</h4>
                <div class="table-container small-table">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Type</th>
                                <th>Amount ($)</th>
                                <th>Counterparty</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.recent_transfers || []).map(t => `
                                <tr>
                                    <td>${formatDate(t.timestamp)}</td>
                                    <td>${t.to_address === data.address ? '<span class="text-bull">BUY / INFLOW</span>' : '<span class="text-bear">SELL / OUTFLOW</span>'}</td>
                                    <td>$${formatNumber(t.usd_value)}</td>
                                    <td><code>${shortenAddress(t.to_address === data.address ? t.from_address : t.to_address)}</code></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;

            elements.walletModalBackdrop.style.display = 'flex';
        } catch (err) {
            console.error('Error fetching wallet detail:', err);
        }
    };

    function closeWalletModal() {
        elements.walletModalBackdrop.style.display = 'none';
    }

    function openConfigModal() {
        elements.configModalBackdrop.style.display = 'flex';
    }

    function closeConfigModal() {
        elements.configModalBackdrop.style.display = 'none';
    }

    async function saveConfig() {
        const payload = {
            screener: {
                min_market_cap: parseFloat(document.getElementById('cfg-min-mcap').value) || 25000,
                max_market_cap: parseFloat(document.getElementById('cfg-max-mcap').value) || 25000000,
                min_liquidity: parseFloat(document.getElementById('cfg-min-liq').value) || 10000,
                min_volume_24h: parseFloat(document.getElementById('cfg-min-vol').value) || 15000,
                min_holders: parseInt(document.getElementById('cfg-min-holders').value) || 80
            },
            accumulator: {
                min_purchases: parseInt(document.getElementById('cfg-min-buys').value) || 2,
                min_usd_value: parseFloat(document.getElementById('cfg-min-usd').value) || 100,
                min_pct_increase: parseFloat(document.getElementById('cfg-min-pct-inc').value) || 15,
                max_pct_sold: parseFloat(document.getElementById('cfg-max-sold-pct').value) || 20
            },
            scoring: {
                weight_existing_holder_accum: parseFloat(document.getElementById('cfg-w-exist').value) || 0.25,
                weight_persistent_accum_count: parseFloat(document.getElementById('cfg-w-persist').value) || 0.20,
                weight_repeat_buyers: parseFloat(document.getElementById('cfg-w-repeat').value) || 0.15,
                weight_accum_to_volume: parseFloat(document.getElementById('cfg-w-vol').value) || 0.10,
                weight_accum_to_supply: parseFloat(document.getElementById('cfg-w-supply').value) || 0.10,
                weight_cohort_retention: parseFloat(document.getElementById('cfg-w-retention').value) || 0.10
            }
        };

        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            closeConfigModal();
            fetchTokens();
        } catch (err) {
            console.error('Error saving config:', err);
        }
    }

    async function triggerRescan() {
        try {
            elements.btnRefreshScan.textContent = '🔄 Rescanning...';
            elements.btnRefreshScan.disabled = true;
            await fetch('/api/pipeline/refresh', { method: 'POST' });
            await fetchTokens();
            if (state.selectedMint) fetchTokenDetail(state.selectedMint);
            await fetchBacktestResults();
        } catch (err) {
            console.error('Rescan failed:', err);
        } finally {
            elements.btnRefreshScan.textContent = '🔄 Rescan Network';
            elements.btnRefreshScan.disabled = false;
        }
    }

    // =========================================================================
    // LIVE ONGOING TRACKER & SCORECARD
    // =========================================================================
    async function fetchTrackerData() {
        try {
            const [statusRes, scoreRes, activeRes] = await Promise.all([
                fetch('/api/tracker/status').then(r => r.json()),
                fetch('/api/tracker/scorecard').then(r => r.json()),
                fetch('/api/tracker/active').then(r => r.json())
            ]);
            renderTrackerData(statusRes, scoreRes, activeRes);
        } catch (err) {
            console.error('Error fetching tracker data:', err);
        }
    }

    function renderTrackerData(statusData, scorecard, activeSignals) {
        // Status Strip KPIs
        if (elements.trackerDaemonStatus) {
            elements.trackerDaemonStatus.textContent = statusData.is_daemon_running ? 'ACTIVE (5m)' : 'PAUSED';
            elements.trackerDaemonStatus.className = 'kpi-value ' + (statusData.is_daemon_running ? 'text-bull' : 'text-warn');
        }
        if (elements.trackerPendingCount) {
            elements.trackerPendingCount.textContent = (statusData.counts ? statusData.counts.pending + statusData.counts.maturing : 0);
        }
        if (elements.trackerTotalObs) {
            elements.trackerTotalObs.textContent = (statusData.counts ? statusData.counts.total : 0);
        }
        if (elements.trackerLastRun && statusData.last_run_timestamp) {
            elements.trackerLastRun.textContent = 'Last cycle: ' + formatDate(statusData.last_run_timestamp);
        }

        // Scorecard Header
        const test = scorecard.hypothesis_test || {};
        const outperf = test.outperformance_vs_baseline || 0.0;
        if (elements.trackerOutperfVal) {
            elements.trackerOutperfVal.textContent = (outperf >= 0 ? '+' : '') + outperf.toFixed(2) + '%';
            elements.trackerOutperfVal.className = 'kpi-value ' + (outperf >= 0 ? 'text-bull' : 'text-bear');
        }
        if (elements.trackerPVal) {
            elements.trackerPVal.textContent = `p-value: ${test.p_value ?? '0.50'} (t=${test.t_statistic ?? 0})`;
        }

        // Verdict Banner
        if (elements.trackerVerdictTitle) {
            elements.trackerVerdictTitle.textContent = test.statistically_significant ?
                "HYPOTHESIS VALIDATED: OUT-OF-SAMPLE ACCUMULATION DELIVERS STATISTICALLY SIGNIFICANT ALPHA" :
                "ONGOING RESEARCH: ACCUMULATING OUT-OF-SAMPLE OBSERVATIONS";
        }
        if (elements.trackerVerdictText) {
            elements.trackerVerdictText.textContent = scorecard.verdict || "Tracking active forward signals to measure predictive value...";
        }

        // Comparative Models Table
        const tbodyScore = elements.trackerScorecardTbody;
        if (tbodyScore) {
            tbodyScore.innerHTML = '';
            const models = [
                { name: 'Model D: High Persistent Accumulation', data: scorecard.high_accumulation_model, desc: 'Existing holders repeatedly increasing position' },
                { name: 'Model E: Dip Pullback + Accumulation', data: scorecard.dip_accumulation_model, desc: 'Accumulation absorption during consolidation/dips' },
                { name: 'Model A: Conventional Price Momentum', data: scorecard.momentum_baseline_model, desc: 'Technical momentum alone (prior 24h gainers)' },
                { name: 'Model S: Sybil Clustered Wallets', data: scorecard.sybil_clustered_model, desc: 'High cluster risk / common funding bot farms' }
            ];

            models.forEach(m => {
                const d = m.data || {};
                const tr = document.createElement('tr');
                const asym = d.mae_avg !== 0 ? (d.mfe_avg / Math.abs(d.mae_avg)).toFixed(2) + 'x' : 'N/A';
                tr.innerHTML = `
                    <td>
                        <strong>${m.name}</strong>
                        <div style="font-size:0.7rem; color:var(--text-muted);">${m.desc}</div>
                    </td>
                    <td>${d.count || 0}</td>
                    <td>${d.win_rate || 0}%</td>
                    <td class="${(d.mean_return || 0) >= 0 ? 'text-bull' : 'text-bear'} highlight-col">${(d.mean_return || 0) >= 0 ? '+' : ''}${d.mean_return || 0}%</td>
                    <td><strong>${d.sharpe || 0}</strong></td>
                    <td class="text-bull">+${d.mfe_avg || 0}%</td>
                    <td class="text-bear">${d.mae_avg || 0}%</td>
                    <td><span class="score-pill ${parseFloat(asym) >= 1.5 ? 'score-high' : 'score-mid'}">${asym}</span></td>
                `;
                tbodyScore.appendChild(tr);
            });
        }

        // Active Watchlist Table
        const tbodyActive = elements.tbodyActiveSignals;
        if (tbodyActive) {
            tbodyActive.innerHTML = '';
            const list = activeSignals.observations || [];
            if (list.length === 0) {
                tbodyActive.innerHTML = `<tr><td colspan="11" style="text-align:center; padding: 24px; color:var(--text-muted);">No open forward signals currently pending. Click "Snapshot Now" to freeze current market state.</td></tr>`;
                return;
            }

            list.forEach(o => {
                const tr = document.createElement('tr');
                const uRet = o.current_unrealized_return || 0.0;
                const uClass = uRet >= 0 ? 'text-bull' : 'text-bear';
                const uStr = (uRet >= 0 ? '+' : '') + uRet.toFixed(2) + '%';
                
                tr.innerHTML = `
                    <td><strong>${o.symbol || 'TOKEN'}</strong></td>
                    <td>${formatDate(o.observation_time)}</td>
                    <td>$${formatPrice(o.price_at_t)}</td>
                    <td>${getSetupBadgeHTML(o.setup_classification)}</td>
                    <td><strong>${o.persistent_accumulators_count}</strong></td>
                    <td><span style="color:var(--sol-purple)">${o.cluster_adjusted_accumulators_count}</span></td>
                    <td>$${formatPrice(o.latest_observed_price || o.price_at_t)}</td>
                    <td class="${uClass} highlight-col"><strong>${uStr}</strong></td>
                    <td class="text-bull">+${(o.mfe_pct || 0).toFixed(1)}%</td>
                    <td class="text-bear">${(o.mae_pct || 0).toFixed(1)}%</td>
                    <td><span class="score-pill ${o.status === 'MATURING' ? 'score-mid' : 'score-high'}">${o.status}</span></td>
                `;
                tbodyActive.appendChild(tr);
            });
        }
    }

    async function handleTrackerSnapshot() {
        try {
            elements.btnTrackerSnapshot.textContent = '📸 Freezing T...';
            elements.btnTrackerSnapshot.disabled = true;
            await fetch('/api/tracker/snapshot', { method: 'POST' });
            await fetchTrackerData();
        } catch (err) {
            console.error('Snapshot failed:', err);
        } finally {
            elements.btnTrackerSnapshot.textContent = '📸 Snapshot Now';
            elements.btnTrackerSnapshot.disabled = false;
        }
    }

    async function handleTrackerResolve() {
        try {
            elements.btnTrackerResolve.textContent = '⚡ Checking...';
            elements.btnTrackerResolve.disabled = true;
            await fetch('/api/tracker/resolve', { method: 'POST' });
            await fetchTrackerData();
        } catch (err) {
            console.error('Resolve check failed:', err);
        } finally {
            elements.btnTrackerResolve.textContent = '⚡ Check Milestones';
            elements.btnTrackerResolve.disabled = false;
        }
    }

    async function handleTrackerSimulate() {
        try {
            elements.btnTrackerSimulate.textContent = '⏩ Advancing +6h...';
            elements.btnTrackerSimulate.disabled = true;
            await fetch('/api/tracker/simulate-forward?hours=6.0', { method: 'POST' });
            await fetchTrackerData();
        } catch (err) {
            console.error('Simulate forward failed:', err);
        } finally {
            elements.btnTrackerSimulate.textContent = '⏩ Advance Clock (+6h)';
            elements.btnTrackerSimulate.disabled = false;
        }
    }

    // =========================================================================
    // UTILITY HELPERS
    // =========================================================================
    function formatNumber(num) {
        if (!num && num !== 0) return '0';
        if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
        if (num >= 1_000) return (num / 1_000).toFixed(1) + 'k';
        return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
    }

    function formatPrice(p) {
        if (!p) return '0.00';
        if (p < 0.0001) return p.toExponential(3);
        if (p < 1.0) return p.toFixed(6);
        return p.toFixed(3);
    }

    function formatDate(ts) {
        if (!ts) return '';
        const d = new Date(ts);
        return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    }

    function shortenAddress(addr) {
        if (!addr) return '';
        if (addr.length <= 12) return addr;
        return `${addr.slice(0, 5)}...${addr.slice(-4)}`;
    }

    // Start on DOM ready
    document.addEventListener('DOMContentLoaded', init);
})();
