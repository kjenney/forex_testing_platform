from flask import jsonify, current_app
from app.routes import account_bp
from app.services.forex_client import ForexClient
from app import db
from app.models import Account
from datetime import datetime


@account_bp.route('', methods=['GET'])
def get_account():
    """Get account balance, equity, and margin information"""
    try:
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        response = client.get_account_summary()
        account_data = response['account']

        # Update or create account record in database
        account = Account.query.filter_by(account_id=account_data['id']).first()

        if not account:
            account = Account(account_id=account_data['id'])
            db.session.add(account)

        account.balance = float(account_data['balance'])
        account.equity = float(account_data.get('NAV', account_data['balance']))
        account.margin_used = float(account_data.get('marginUsed', 0))
        account.margin_available = float(account_data.get('marginAvailable', 0))
        account.open_trade_count = int(account_data.get('openTradeCount', 0))
        account.unrealized_pl = float(account_data.get('unrealizedPL', 0))
        account.realized_pl = float(account_data.get('pl', 0))
        account.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'account': account.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@account_bp.route('/positions', methods=['GET'])
def get_positions():
    """List all open positions"""
    try:
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        response = client.get_open_positions()
        positions = response.get('positions', [])

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

        return jsonify({
            'success': True,
            'positions': formatted_positions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@account_bp.route('/instruments', methods=['GET'])
def get_instruments():
    """List available trading instruments"""
    try:
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        response = client.get_instruments()
        instruments = response.get('instruments', [])

        # Filter to just forex pairs and format
        forex_instruments = []
        for inst in instruments:
            if inst['type'] == 'CURRENCY':
                forex_instruments.append({
                    'name': inst['name'],
                    'display_name': inst['displayName'],
                    'pip_location': inst['pipLocation'],
                    'margin_rate': inst.get('marginRate', 'N/A')
                })

        return jsonify({
            'success': True,
            'instruments': forex_instruments
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
