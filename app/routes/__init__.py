from flask import Blueprint

account_bp = Blueprint('account', __name__)
trades_bp = Blueprint('trades', __name__)
strategies_bp = Blueprint('strategies', __name__)
dashboard_bp = Blueprint('dashboard', __name__)

from app.routes import account, trades, strategies, dashboard
