import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///trading.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Forex.com GAIN Capital API
    FOREX_USERNAME = os.getenv('FOREX_USERNAME')
    FOREX_PASSWORD = os.getenv('FOREX_PASSWORD')
    FOREX_APPKEY = os.getenv('FOREX_APPKEY')

    # Trading Configuration
    DEFAULT_RISK_PERCENT = float(os.getenv('DEFAULT_RISK_PERCENT', 1.0))
    MAX_DAILY_LOSS_PERCENT = float(os.getenv('MAX_DAILY_LOSS_PERCENT', 3.0))
    TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'EUR_USD,GBP_USD,USD_JPY').split(',')
    MAX_CONCURRENT_POSITIONS = int(os.getenv('MAX_CONCURRENT_POSITIONS', 3))

    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
