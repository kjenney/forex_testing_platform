from flask import jsonify, request, current_app
from app.routes import trades_bp
from app.services.forex_client import ForexClient
from app import db
from app.models import Trade
from datetime import datetime


@trades_bp.route('', methods=['GET'])
def get_trades():
    """List all trades with optional filters"""
    try:
        # Query parameters for filtering
        status = request.args.get('status')
        strategy = request.args.get('strategy')
        instrument = request.args.get('instrument')
        limit = request.args.get('limit', 50, type=int)

        query = Trade.query

        if status:
            query = query.filter_by(status=status)
        if strategy:
            query = query.filter_by(strategy_name=strategy)
        if instrument:
            query = query.filter_by(instrument=instrument)

        trades = query.order_by(Trade.entry_time.desc()).limit(limit).all()

        return jsonify({
            'success': True,
            'trades': [trade.to_dict() for trade in trades]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/<int:trade_id>', methods=['GET'])
def get_trade(trade_id):
    """Get specific trade by ID"""
    try:
        trade = Trade.query.get_or_404(trade_id)

        return jsonify({
            'success': True,
            'trade': trade.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404


@trades_bp.route('', methods=['POST'])
def create_trade():
    """Execute a manual trade"""
    try:
        data = request.get_json()

        required_fields = ['instrument', 'units']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: instrument, units'
            }), 400

        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        # Create order
        response = client.create_market_order(
            instrument=data['instrument'],
            units=float(data['units']),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit')
        )

        # Extract trade information from response
        if 'orderFillTransaction' in response:
            fill = response['orderFillTransaction']

            # Create trade record
            trade = Trade(
                trade_id=fill['id'],
                instrument=fill['instrument'],
                direction='long' if float(fill['units']) > 0 else 'short',
                units=abs(float(fill['units'])),
                entry_price=float(fill['price']),
                stop_loss=data.get('stop_loss'),
                take_profit=data.get('take_profit'),
                status='open',
                strategy_name='manual',
                entry_time=datetime.utcnow(),
                notes=data.get('notes', '')
            )

            db.session.add(trade)
            db.session.commit()

            return jsonify({
                'success': True,
                'trade': trade.to_dict(),
                'response': response
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Order was not filled',
                'response': response
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/<string:trade_id>/close', methods=['POST'])
def close_trade(trade_id):
    """Close a specific trade"""
    try:
        # Find trade in database
        trade = Trade.query.filter_by(trade_id=trade_id).first_or_404()

        if trade.status != 'open':
            return jsonify({
                'success': False,
                'error': 'Trade is not open'
            }), 400

        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        # Close the trade
        response = client.close_trade(trade_id)

        # Update trade record
        if 'orderFillTransaction' in response:
            fill = response['orderFillTransaction']

            trade.exit_price = float(fill['price'])
            trade.pnl = float(fill.get('pl', 0))
            trade.status = 'closed'
            trade.exit_time = datetime.utcnow()

            db.session.commit()

            return jsonify({
                'success': True,
                'trade': trade.to_dict(),
                'response': response
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Trade close failed',
                'response': response
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/open', methods=['GET'])
def get_open_trades():
    """Get all open trades from broker"""
    try:
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        response = client.get_open_trades()
        trades = response.get('trades', [])

        formatted_trades = []
        for t in trades:
            formatted_trades.append({
                'id': t['id'],
                'instrument': t['instrument'],
                'units': float(t['currentUnits']),
                'price': float(t['price']),
                'unrealized_pl': float(t.get('unrealizedPL', 0)),
                'margin_used': float(t.get('marginUsed', 0)),
                'open_time': t['openTime']
            })

        return jsonify({
            'success': True,
            'trades': formatted_trades
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
