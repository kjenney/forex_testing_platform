// Dashboard JavaScript

const API_BASE = '/api';
const REFRESH_INTERVAL = 5000; // 5 seconds

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Format number
function formatNumber(value, decimals = 2) {
    return Number(value).toFixed(decimals);
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Update account metrics
function updateAccountMetrics(account) {
    document.getElementById('balance').textContent = formatCurrency(account.balance);
    document.getElementById('equity').textContent = formatCurrency(account.equity);

    const unrealizedPL = document.getElementById('unrealizedPL');
    unrealizedPL.textContent = formatCurrency(account.unrealized_pl);
    unrealizedPL.className = 'metric-value ' + (account.unrealized_pl >= 0 ? 'positive' : 'negative');

    document.getElementById('marginUsed').textContent = formatCurrency(account.margin_used);
    document.getElementById('openTrades').textContent = account.open_trade_count;
}

// Update today's P&L
function updateTodayPL(todayPL) {
    const elem = document.getElementById('todayPL');
    elem.textContent = formatCurrency(todayPL);
    elem.className = 'metric-value ' + (todayPL >= 0 ? 'positive' : 'negative');
}

// Update positions table
function updatePositions(positions) {
    const tbody = document.getElementById('positionsBody');

    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-data">No open positions</td></tr>';
        return;
    }

    let html = '';
    positions.forEach(pos => {
        const plClass = pos.unrealized_pl >= 0 ? 'pnl-positive' : 'pnl-negative';
        html += `
            <tr>
                <td>${pos.instrument.replace('_', '/')}</td>
                <td>${formatNumber(pos.long_units, 0)}</td>
                <td>${formatNumber(pos.short_units, 0)}</td>
                <td class="${plClass}">${formatCurrency(pos.unrealized_pl)}</td>
                <td>${formatCurrency(pos.margin_used)}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// Update trades table
function updateTrades(trades) {
    const tbody = document.getElementById('tradesBody');

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">No recent trades</td></tr>';
        return;
    }

    let html = '';
    trades.forEach(trade => {
        const directionClass = trade.direction === 'long' ? 'direction-long' : 'direction-short';
        const statusClass = `status-${trade.status}`;
        const plClass = trade.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';

        html += `
            <tr>
                <td>${formatDate(trade.entry_time)}</td>
                <td>${trade.instrument.replace('_', '/')}</td>
                <td class="${directionClass}">${trade.direction.toUpperCase()}</td>
                <td>${formatNumber(trade.units, 0)}</td>
                <td>${formatNumber(trade.entry_price, 5)}</td>
                <td>${trade.exit_price ? formatNumber(trade.exit_price, 5) : '--'}</td>
                <td class="${plClass}">${formatCurrency(trade.pnl)}</td>
                <td class="${statusClass}">${trade.status.toUpperCase()}</td>
                <td>${trade.strategy_name || '--'}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// Fetch dashboard data
async function fetchDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/summary`);
        const data = await response.json();

        if (data.success) {
            updateAccountMetrics(data.account);
            updateTodayPL(data.today_pnl);
            updatePositions(data.positions);
            updateTrades(data.recent_trades);

            // Update last updated time
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        } else {
            console.error('Failed to fetch dashboard data:', data.error);
        }
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
    }
}

// Execute strategy
async function executeStrategy(strategyName, instrument, analyze = true) {
    const resultDiv = document.getElementById('strategyResult');

    try {
        // Disable all strategy buttons
        document.querySelectorAll('.strategy-btn').forEach(btn => {
            btn.disabled = true;
        });

        resultDiv.textContent = `${analyze ? 'Analyzing' : 'Executing'} ${strategyName} strategy for ${instrument.replace('_', '/')}...`;
        resultDiv.className = 'strategy-result info';

        const response = await fetch(`${API_BASE}/strategies/${strategyName}/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                instrument: instrument,
                execute: !analyze
            })
        });

        const data = await response.json();

        if (data.success) {
            const signal = data.signal;

            if (signal.action === 'hold') {
                resultDiv.textContent = `No ${strategyName} setup found for ${instrument.replace('_', '/')}. Reason: ${signal.reason}`;
                resultDiv.className = 'strategy-result info';
            } else if (data.executed) {
                resultDiv.innerHTML = `
                    <strong>Trade Executed!</strong><br>
                    Strategy: ${strategyName}<br>
                    Instrument: ${instrument.replace('_', '/')}<br>
                    Action: ${signal.action.toUpperCase()}<br>
                    Units: ${formatNumber(Math.abs(signal.units), 0)}<br>
                    Entry: ${formatNumber(data.trade.entry_price, 5)}<br>
                    Stop Loss: ${formatNumber(signal.stop_loss, 5)}<br>
                    Take Profit: ${formatNumber(signal.take_profit, 5)}<br>
                    Reason: ${signal.reason}
                `;
                resultDiv.className = 'strategy-result success';

                // Refresh dashboard data
                setTimeout(fetchDashboardData, 1000);
            } else {
                resultDiv.innerHTML = `
                    <strong>Signal Generated (Analysis Mode)</strong><br>
                    Strategy: ${strategyName}<br>
                    Instrument: ${instrument.replace('_', '/')}<br>
                    Action: ${signal.action.toUpperCase()}<br>
                    Reason: ${signal.reason}<br>
                    <button onclick="executeStrategy('${strategyName}', '${instrument}', false)" class="execute-btn">Execute Trade</button>
                `;
                resultDiv.className = 'strategy-result info';
            }
        } else {
            resultDiv.textContent = `Error: ${data.error}`;
            resultDiv.className = 'strategy-result error';
        }
    } catch (error) {
        resultDiv.textContent = `Error: ${error.message}`;
        resultDiv.className = 'strategy-result error';
    } finally {
        // Re-enable strategy buttons
        document.querySelectorAll('.strategy-btn').forEach(btn => {
            btn.disabled = false;
        });
    }
}

// Initialize dashboard
function init() {
    // Fetch initial data
    fetchDashboardData();

    // Set up auto-refresh
    setInterval(fetchDashboardData, REFRESH_INTERVAL);

    // Set up strategy button handlers
    document.querySelectorAll('.strategy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const strategyName = btn.dataset.strategy;
            const instrument = document.getElementById('instrumentSelect').value;
            executeStrategy(strategyName, instrument, true);
        });
    });
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
