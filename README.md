# Forex Testing Platform

A Python/Flask-based forex testing platform for testing day testing strategies on Forex.com demo accounts.

## Features

- **Four Testing Strategies**:
  - Scalping (5-10 pips, 5-minute charts)
  - Breakout (1:2-1:3 RR, 15-minute charts)
  - Range Trading (1:1 RR, 1-hour charts)
  - Trend Following (1.5:1 RR, 15-minute charts)

- **Web Dashboard**:
  - Real-time account monitoring
  - Position tracking
  - Trade history
  - One-click strategy execution

- **Risk Management**:
  - 1% risk rule per trade
  - ATR-based stop losses
  - Maximum concurrent positions limit
  - Daily loss limits

- **REST API**:
  - Account endpoints
  - Trade execution
  - Strategy analysis and execution
  - Performance metrics

## Prerequisites

- Docker and Docker Compose
- Forex.com demo account
- API credentials (API key and Account ID)

## Setup

1. **Clone the repository** (if applicable) or navigate to the project directory:

```bash
cd /Users/kjenney/devel/trading
```

2. **Create environment file**:

```bash
cp .env.example .env
```

3. **Edit `.env` file** with your API credentials:

```bash
# Forex.com API Configuration
FOREX_API_KEY=your_api_key_here
FOREX_ACCOUNT_ID=your_account_id_here
FOREX_ENVIRONMENT=practice

# Flask Configuration
SECRET_KEY=your_random_secret_key_here

# Other settings can remain as defaults
```

4. **Build and start services**:

```bash
docker-compose up --build
```

The application will be available at: http://localhost:5000

## Usage

### Web Dashboard

Visit http://localhost:5000 to access the dashboard.

Features:
- View account balance, equity, P&L
- Monitor open positions
- Execute strategies on selected currency pairs
- View recent trades

### API Endpoints

#### Account

```bash
# Get account summary
curl http://localhost:5000/api/account

# Get open positions
curl http://localhost:5000/api/account/positions

# List available instruments
curl http://localhost:5000/api/account/instruments
```

#### Trades

```bash
# List all trades
curl http://localhost:5000/api/trades

# Get specific trade
curl http://localhost:5000/api/trades/1

# Execute manual trade
curl -X POST http://localhost:5000/api/trades \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "EUR_USD",
    "units": 1000,
    "stop_loss": 1.0850,
    "take_profit": 1.0950
  }'

# Close trade
curl -X POST http://localhost:5000/api/trades/<trade_id>/close

# Get open trades from broker
curl http://localhost:5000/api/trades/open
```

#### Strategies

```bash
# List available strategies
curl http://localhost:5000/api/strategies

# Analyze with strategy (no execution)
curl -X POST http://localhost:5000/api/strategies/scalping/analyze \
  -H "Content-Type: application/json" \
  -d '{"instrument": "EUR_USD"}'

# Execute strategy
curl -X POST http://localhost:5000/api/strategies/scalping/run \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "EUR_USD",
    "execute": true
  }'

# Get strategy performance
curl http://localhost:5000/api/strategies/scalping/performance
```

## Trading Strategies

### Scalping
- **Timeframe**: 5-minute charts
- **Indicators**: 20/50 EMA, RSI(9), ATR(14)
- **Entry**: Price crosses 20-EMA with RSI confirmation
- **Target**: 5-10 pips
- **Stop**: 1.5× ATR

### Breakout
- **Timeframe**: 15-minute charts
- **Indicators**: Bollinger Bands, Volume, ATR
- **Entry**: Price breaks consolidation with volume confirmation
- **Target**: 1:2 to 1:3 risk-reward
- **Stop**: 1.5× ATR beyond breakout

### Range Trading
- **Timeframe**: 1-hour charts
- **Indicators**: Support/Resistance, RSI
- **Entry**: Bounces at boundaries with RSI oversold/overbought
- **Target**: Opposite boundary or 1:1 RR
- **Stop**: Beyond boundary with buffer

### Trend Following
- **Timeframe**: 15-minute charts
- **Indicators**: 20/50 EMA, ATR, Fibonacci
- **Entry**: Pullback to EMA or Fib 38.2-61.8%
- **Target**: 1.5:1 risk-reward
- **Stop**: 1.5× ATR below swing

## Risk Management

All strategies implement:
- **1% risk rule**: Never risk more than 1% per trade
- **Position sizing**: Calculated using `Risk / (Stop Loss Pips × Pip Value)`
- **Maximum positions**: 3 concurrent trades (configurable)
- **Stop losses**: ATR-based, adapting to volatility

## Development

### Running without Docker

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export FLASK_APP=run.py
export DATABASE_URL=sqlite:///trading.db
# Set other variables from .env.example
```

4. Initialize database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

5. Run application:
```bash
python run.py
```

### Database Migrations

```bash
# Create new migration
docker-compose exec web flask db migrate -m "Description"

# Apply migrations
docker-compose exec web flask db upgrade

# Rollback
docker-compose exec web flask db downgrade
```

### Testing

```bash
# Run tests (when implemented)
docker-compose exec web pytest

# Test API connection
docker-compose exec web python -c "
from app.services.forex_client import ForexClient
import os
client = ForexClient(
    os.getenv('FOREX_API_KEY'),
    os.getenv('FOREX_ACCOUNT_ID'),
    'practice'
)
print(client.get_account_summary())
"
```

## Project Structure

```
trading/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration
│   ├── models.py             # Database models
│   ├── routes/               # API endpoints
│   │   ├── account.py
│   │   ├── trades.py
│   │   ├── strategies.py
│   │   └── dashboard.py
│   ├── services/
│   │   └── forex_client.py   # Forex.com API client
│   └── strategies/           # Trading strategies
│       ├── base.py
│       ├── scalping.py
│       ├── breakout.py
│       ├── range_trading.py
│       └── trend_following.py
├── static/                   # Static assets
│   ├── css/
│   └── js/
├── templates/                # HTML templates
│   └── dashboard.html
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
└── .env
```

## Monitoring and Logs

```bash
# View logs
docker-compose logs -f web

# View database logs
docker-compose logs -f db

# Access database
docker-compose exec db psql -U trading_user -d trading_db

# View trades in database
docker-compose exec db psql -U trading_user -d trading_db -c "SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;"
```

## Best Practices

1. **Always use demo account** until strategies are proven profitable
2. **Start with analysis mode** - review signals before executing
3. **Monitor during London-NY overlap** (13:00-17:00 UTC) for best liquidity
4. **Focus on major pairs**: EUR/USD, GBP/USD, USD/JPY
5. **Keep leverage low**: Effective leverage 4:1-10:1
6. **Maintain trading journal**: Use the notes field for insights

## Troubleshooting

### API Connection Issues

```bash
# Test API credentials
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api-fxpractice.oanda.com/v3/accounts/YOUR_ACCOUNT_ID/summary
```

### Database Issues

```bash
# Reset database
docker-compose down -v
docker-compose up --build
```

### Port Conflicts

If port 5000 is in use, modify `docker-compose.yml`:
```yaml
ports:
  - "8000:5000"  # Use port 8000 instead
```

## Security Notes

- Never commit `.env` file
- Use demo account only
- Keep API keys secure
- Review all trades before execution in production
- Implement rate limiting for production deployment

## Future Enhancements

- WebSocket for real-time price updates
- Advanced backtesting framework
- Machine learning signal generation
- Multi-timeframe analysis
- Telegram/email notifications
- React/Vue.js frontend
- Portfolio optimization

## License

This project is for educational purposes. Use at your own risk.

## Resources

- [OANDA v20 API Documentation](https://developer.oanda.com/rest-live-v20/introduction/)
- [Forex.com](https://www.forex.com/)
- [CLAUDE.md Trading Guide](./CLAUDE.md)
