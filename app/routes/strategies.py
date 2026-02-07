from flask import jsonify, request, current_app
from app.routes import strategies_bp
from app.services.forex_client import ForexClient
from app import db
from app.models import Trade, StrategyPerformance
from app.strategies.scalping import ScalpingStrategy
from app.strategies.breakout import BreakoutStrategy
from app.strategies.range_trading import RangeTradingStrategy
from app.strategies.trend_following import TrendFollowingStrategy
from datetime import datetime


# Strategy registry
STRATEGIES = {
    'scalping': ScalpingStrategy,
    'breakout': BreakoutStrategy,
    'range_trading': RangeTradingStrategy,
    'trend_following': TrendFollowingStrategy
}


@strategies_bp.route('', methods=['GET'])
def list_strategies():
    """List all available strategies"""
    strategy_info = []

    for name, strategy_class in STRATEGIES.items():
        # Get performance if available
        perf = StrategyPerformance.query.filter_by(strategy_name=name).first()

        strategy_info.append({
            'name': name,
            'class': strategy_class.__name__,
            'description': strategy_class.__doc__.strip() if strategy_class.__doc__ else '',
            'performance': perf.to_dict() if perf else None
        })

    return jsonify({
        'success': True,
        'strategies': strategy_info
    })


@strategies_bp.route('/<string:strategy_name>/analyze', methods=['POST'])
def analyze_strategy(strategy_name):
    """
    Analyze market conditions with a strategy (no execution)

    Request body:
    {
        "instrument": "EUR_USD"
    }
    """
    try:
        if strategy_name not in STRATEGIES:
            return jsonify({
                'success': False,
                'error': f'Strategy "{strategy_name}" not found'
            }), 404

        data = request.get_json()
        instrument = data.get('instrument', 'EUR_USD')

        # Initialize strategy
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        strategy_class = STRATEGIES[strategy_name]
        strategy = strategy_class(client)

        # Analyze
        signal = strategy.analyze(instrument)

        return jsonify({
            'success': True,
            'strategy': strategy_name,
            'instrument': instrument,
            'signal': signal.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategies_bp.route('/<string:strategy_name>/run', methods=['POST'])
def run_strategy(strategy_name):
    """
    Execute a strategy on specified instrument

    Request body:
    {
        "instrument": "EUR_USD",
        "execute": true  (default: false, only analyze)
    }
    """
    try:
        if strategy_name not in STRATEGIES:
            return jsonify({
                'success': False,
                'error': f'Strategy "{strategy_name}" not found'
            }), 404

        data = request.get_json() or {}
        instrument = data.get('instrument', 'EUR_USD')
        execute = data.get('execute', False)

        # Check max concurrent positions
        open_trades_count = Trade.query.filter_by(status='open').count()
        max_positions = current_app.config['MAX_CONCURRENT_POSITIONS']

        if open_trades_count >= max_positions:
            return jsonify({
                'success': False,
                'error': f'Maximum concurrent positions ({max_positions}) reached'
            }), 400

        # Initialize strategy
        client = ForexClient(
            current_app.config['FOREX_USERNAME'],
            current_app.config['FOREX_PASSWORD'],
            current_app.config['FOREX_APPKEY']
        )

        strategy_class = STRATEGIES[strategy_name]
        strategy = strategy_class(client)

        # Analyze
        signal = strategy.analyze(instrument)

        if signal.action == 'hold' or not execute:
            return jsonify({
                'success': True,
                'strategy': strategy_name,
                'instrument': instrument,
                'signal': signal.to_dict(),
                'executed': False
            })

        # Execute trade
        response = strategy.execute_trade(signal)

        if response and 'orderFillTransaction' in response:
            fill = response['orderFillTransaction']

            # Create trade record
            trade = Trade(
                trade_id=fill['id'],
                instrument=fill['instrument'],
                direction=signal.action,
                units=abs(float(fill['units'])),
                entry_price=float(fill['price']),
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status='open',
                strategy_name=strategy_name,
                entry_time=datetime.utcnow(),
                notes=signal.reason
            )

            db.session.add(trade)
            db.session.commit()

            return jsonify({
                'success': True,
                'strategy': strategy_name,
                'instrument': instrument,
                'signal': signal.to_dict(),
                'executed': True,
                'trade': trade.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Trade execution failed',
                'signal': signal.to_dict(),
                'response': response
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@strategies_bp.route('/<string:strategy_name>/performance', methods=['GET'])
def get_strategy_performance(strategy_name):
    """Get performance metrics for a strategy"""
    try:
        # Get all closed trades for this strategy
        trades = Trade.query.filter_by(
            strategy_name=strategy_name,
            status='closed'
        ).all()

        if not trades:
            return jsonify({
                'success': True,
                'strategy': strategy_name,
                'performance': {
                    'total_trades': 0,
                    'message': 'No closed trades yet'
                }
            })

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # Calculate max drawdown
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0

        for trade in sorted(trades, key=lambda x: x.exit_time):
            cumulative_pnl += trade.pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Update or create performance record
        perf = StrategyPerformance.query.filter_by(strategy_name=strategy_name).first()

        if not perf:
            perf = StrategyPerformance(strategy_name=strategy_name)
            db.session.add(perf)

        perf.total_trades = total_trades
        perf.winning_trades = winning_trades
        perf.losing_trades = losing_trades
        perf.win_rate = win_rate
        perf.total_pnl = total_pnl
        perf.avg_pnl = avg_pnl
        perf.max_drawdown = max_drawdown
        perf.updated_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'strategy': strategy_name,
            'performance': perf.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
