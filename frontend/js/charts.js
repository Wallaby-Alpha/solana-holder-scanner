/**
 * charts.js: Interactive Charting Engine using Chart.js
 * Renders Price vs Accumulation, Holder Dynamics, Cohort Retention, and Backtest Excursions.
 */

window.AppCharts = (function() {
    let priceChartInstance = null;
    let holderBehaviorChartInstance = null;
    let cohortChartInstance = null;
    let concentrationChartInstance = null;
    let excursionChartInstance = null;
    let modelReturnsChartInstance = null;

    const chartTheme = {
        color: '#94a3b8',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        font: { family: 'Inter', size: 11 }
    };

    function renderPriceDivergenceChart(canvasId, snapshots, currentMetrics) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (priceChartInstance) priceChartInstance.destroy();

        if (!snapshots || snapshots.length === 0) return;

        // Extract labels and price series
        const labels = snapshots.map(s => {
            const d = new Date(s.timestamp);
            return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:00`;
        });
        const prices = snapshots.map(s => s.price_usd);
        const volumes = snapshots.map(s => (s.volume_usd || 0) / 1000); // in $k

        priceChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Price (USD)',
                        data: prices,
                        borderColor: '#38bdf8',
                        backgroundColor: 'rgba(56, 189, 248, 0.08)',
                        fill: true,
                        tension: 0.25,
                        yAxisID: 'yPrice',
                        pointRadius: 1,
                        borderWidth: 2
                    },
                    {
                        label: 'Volume ($k)',
                        data: volumes,
                        type: 'bar',
                        backgroundColor: 'rgba(153, 69, 255, 0.25)',
                        borderColor: 'rgba(153, 69, 255, 0.6)',
                        borderWidth: 1,
                        yAxisID: 'yVol'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: chartTheme.color, font: chartTheme.font } },
                    tooltip: { backgroundColor: '#111827', titleColor: '#fff', bodyColor: '#cbd5e1' }
                },
                scales: {
                    x: { ticks: { color: chartTheme.color, maxTicksLimit: 8 }, grid: { color: chartTheme.borderColor } },
                    yPrice: {
                        position: 'left',
                        ticks: { color: '#38bdf8' },
                        grid: { color: chartTheme.borderColor }
                    },
                    yVol: {
                        position: 'right',
                        ticks: { color: '#c084fc' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    function renderHolderBehaviorChart(canvasId, currentMetrics) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (holderBehaviorChartInstance) holderBehaviorChartInstance.destroy();

        const existUsd = currentMetrics ? currentMetrics.existing_holder_net_accum_usd || 0 : 1200;
        const newUsd = currentMetrics ? currentMetrics.new_wallet_net_accum_usd || 0 : 800;
        const soldUsd = currentMetrics ? currentMetrics.usd_value_sold || 0 : 500;

        holderBehaviorChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Existing Holders Inflow', 'New Entrants Inflow', 'Holder Outflows (Sells)'],
                datasets: [{
                    label: 'Net Volume ($ USD)',
                    data: [existUsd, newUsd, -soldUsd],
                    backgroundColor: [
                        'rgba(20, 241, 149, 0.65)', // Existing holders: Bright Solana Green
                        'rgba(56, 189, 248, 0.65)', // New entrants: Cyan
                        'rgba(244, 63, 94, 0.65)'   // Outflows: Rose
                    ],
                    borderColor: [
                        '#14f195',
                        '#38bdf8',
                        '#f43f5e'
                    ],
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { backgroundColor: '#111827', titleColor: '#fff', bodyColor: '#cbd5e1' }
                },
                scales: {
                    x: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } },
                    y: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } }
                }
            }
        });
    }

    function renderCohortRetentionChart(canvasId, cohorts) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (cohortChartInstance) cohortChartInstance.destroy();

        if (!cohorts || cohorts.length === 0) {
            cohorts = [
                { cohort_bracket: '<24h', retention_rate: 65, wallet_count: 14 },
                { cohort_bracket: '1-3d', retention_rate: 74, wallet_count: 22 },
                { cohort_bracket: '3-7d', retention_rate: 81, wallet_count: 35 },
                { cohort_bracket: '7-30d', retention_rate: 86, wallet_count: 48 },
                { cohort_bracket: '>30d', retention_rate: 92, wallet_count: 18 }
            ];
        }

        const labels = cohorts.map(c => c.cohort_bracket);
        const retention = cohorts.map(c => c.retention_rate);

        cohortChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Retention Rate (%)',
                    data: retention,
                    backgroundColor: 'rgba(16, 185, 129, 0.55)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } },
                    y: { min: 0, max: 100, ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } }
                },
                plugins: {
                    legend: { labels: { color: chartTheme.color } }
                }
            }
        });
    }

    function renderConcentrationChart(canvasId, metrics) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (concentrationChartInstance) concentrationChartInstance.destroy();

        const top5 = metrics ? metrics.top_5_percent || 32 : 32;
        const top10 = metrics ? metrics.top_10_percent || 45 : 45;
        const top20 = metrics ? metrics.top_20_percent || 62 : 62;
        const top30 = metrics ? metrics.top_30_percent || 74 : 74;

        concentrationChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Top 5', 'Top 10', 'Top 20', 'Top 30'],
                datasets: [{
                    label: '% of Circulating Supply Held',
                    data: [top5, top10, top20, top30],
                    borderColor: '#9945ff',
                    backgroundColor: 'rgba(153, 69, 255, 0.15)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 2,
                    pointBackgroundColor: '#9945ff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } },
                    y: { min: 0, max: 100, ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } }
                },
                plugins: {
                    legend: { labels: { color: chartTheme.color } }
                }
            }
        });
    }

    function renderExcursionChart(canvasId, observations) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (excursionChartInstance) excursionChartInstance.destroy();

        if (!observations || observations.length === 0) return;

        const dataPoints = observations.map(o => ({
            x: o.mae_pct || 0,
            y: o.mfe_pct || 0,
            r: Math.min(12, Math.max(4, (o.composite_score || 50) / 10))
        }));

        excursionChartInstance = new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: 'Observations (MFE vs MAE %)',
                    data: dataPoints,
                    backgroundColor: 'rgba(20, 241, 149, 0.45)',
                    borderColor: '#14f195',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: chartTheme.color } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return `MAE (Drawdown): ${ctx.raw.x}% | MFE (Upside): +${ctx.raw.y}%`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Max Adverse Excursion / Drawdown (%)', color: chartTheme.color },
                        ticks: { color: chartTheme.color },
                        grid: { color: chartTheme.borderColor }
                    },
                    y: {
                        title: { display: true, text: 'Max Favorable Excursion / Upside (%)', color: chartTheme.color },
                        ticks: { color: chartTheme.color },
                        grid: { color: chartTheme.borderColor }
                    }
                }
            }
        });
    }

    function renderModelReturnsChart(canvasId, models) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        if (modelReturnsChartInstance) modelReturnsChartInstance.destroy();

        if (!models || models.length === 0) return;

        const labels = models.map(m => m.model.split(' (')[0]);
        const returns = models.map(m => m.mean_forward_return_pct);

        modelReturnsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mean Forward Return (%)',
                    data: returns,
                    backgroundColor: returns.map(r => r >= 0 ? 'rgba(16, 185, 129, 0.65)' : 'rgba(244, 63, 94, 0.65)'),
                    borderColor: returns.map(r => r >= 0 ? '#10b981' : '#f43f5e'),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } },
                    y: { ticks: { color: chartTheme.color }, grid: { color: chartTheme.borderColor } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    return {
        renderPriceDivergenceChart,
        renderHolderBehaviorChart,
        renderCohortRetentionChart,
        renderConcentrationChart,
        renderExcursionChart,
        renderModelReturnsChart
    };
})();
