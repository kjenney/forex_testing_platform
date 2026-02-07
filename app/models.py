from datetime import datetime
from app import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, nullable=False)
    equity = db.Column(db.Float, nullable=False)
    margin_used = db.Column(db.Float, default=0.0)
    margin_available = db.Column(db.Float, default=0.0)
    open_trade_count = db.Column(db.Integer, default=0)
    unrealized_pl = db.Column(db.Float, default=0.0)
    realized_pl = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'balance': self.balance,
            'equity': self.equity,
            'margin_used': self.margin_used,
            'margin_available': self.margin_available,
            'open_trade_count': self.open_trade_count,
            'unrealized_pl': self.unrealized_pl,
            'realized_pl': self.realized_pl,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Trade(db.Model):
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.String(50), unique=True, nullable=False)
    instrument = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'long' or 'short'
    units = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    pnl = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='open')  # 'open', 'closed', 'cancelled'
    strategy_name = db.Column(db.String(50))
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    exit_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'trade_id': self.trade_id,
            'instrument': self.instrument,
            'direction': self.direction,
            'units': self.units,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'pnl': self.pnl,
            'status': self.status,
            'strategy_name': self.strategy_name,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'notes': self.notes
        }


class Strategy(db.Model):
    __tablename__ = 'strategies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)
    config = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StrategyPerformance(db.Model):
    __tablename__ = 'strategy_performance'

    id = db.Column(db.Integer, primary_key=True)
    strategy_name = db.Column(db.String(50), nullable=False)
    total_trades = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    losing_trades = db.Column(db.Integer, default=0)
    win_rate = db.Column(db.Float, default=0.0)
    total_pnl = db.Column(db.Float, default=0.0)
    avg_pnl = db.Column(db.Float, default=0.0)
    max_drawdown = db.Column(db.Float, default=0.0)
    sharpe_ratio = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'strategy_name': self.strategy_name,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl': self.avg_pnl,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
