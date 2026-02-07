from flask import render_template, jsonify, current_app
from app.routes import dashboard_bp
from app.services.forex_client import ForexClient
from app.models import Trade, Account
from app import db


@dashboard_bp.route('/', methods=['GET'])
def index():
    """Render the main dashboard"""
    return render_template('dashboard.html')


@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary data (account + positions + recent trades)"""
    try:
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        # Get account info
        account_response = client.get_account_summary()
        account_data = account_response['account']

        # Get open positions
        positions_response = client.get_open_positions()
        positions = positions_response.get('positions', [])

        formatted_positions = []
        for pos in positions:
            long_units = float(pos['long']['units'])
            short_units = float(pos['short']['units'])

            if long_units != 0 or short_units != 0:
                formatted_positions.append({
                    'instrument': pos['instrument'],
                    'long_units': long_units,
                    'short_units': short_units,
                    'unrealized_pl': float(pos.get('unrealizedPL', 0)),
                    'margin_used': float(pos.get('marginUsed', 0))
                })

        # Get recent trades from database
        recent_trades = Trade.query.order_by(
            Trade.entry_time.desc()
        ).limit(10).all()

        # Calculate today's P&L
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        today_closed_trades = Trade.query.filter(
            Trade.exit_time >= today_start,
            Trade.status == 'closed'
        ).all()

        today_pnl = sum(t.pnl for t in today_closed_trades)

        # Count open trades
        open_trades_count = Trade.query.filter_by(status='open').count()

        return jsonify({
            'success': True,
            'account': {
                'balance': float(account_data['balance']),
                'equity': float(account_data.get('NAV', account_data['balance'])),
                'margin_used': float(account_data.get('marginUsed', 0)),
                'margin_available': float(account_data.get('marginAvailable', 0)),
                'unrealized_pl': float(account_data.get('unrealizedPL', 0)),
                'open_trade_count': int(account_data.get('openTradeCount', 0))
            },
            'positions': formatted_positions,
            'recent_trades': [trade.to_dict() for trade in recent_trades],
            'today_pnl': today_pnl,
            'open_trades_count': open_trades_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
