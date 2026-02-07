from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object('app.config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)

    with app.app_context():
        from app.routes import account_bp, trades_bp, strategies_bp, dashboard_bp

        app.register_blueprint(dashboard_bp)
        app.register_blueprint(account_bp, url_prefix='/api/account')
        app.register_blueprint(trades_bp, url_prefix='/api/trades')
        app.register_blueprint(strategies_bp, url_prefix='/api/strategies')

    return app
