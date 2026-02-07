# Quick Start Guide

## Get Your API Credentials

1. Sign up for a Forex.com demo account at https://www.forex.com/
2. You'll need:
   - **Username** - Your Forex.com login username
   - **Password** - Your Forex.com login password
   - **AppKey** - Contact Forex.com support or check API settings to get this

## Setup (5 minutes)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your credentials
# Required fields:
#   FOREX_USERNAME=your_forex_username
#   FOREX_PASSWORD=your_forex_password
#   FOREX_APPKEY=your_appkey_from_forex
#   SECRET_KEY=any_random_string_here

# 3. Start the platform
docker-compose up -d --build
```

## Access the Platform

Open http://localhost:5000 in your browser.

## First Test

1. **View Account**: The dashboard will show your demo account balance
2. **Select a Pair**: Choose EUR/USD from the dropdown
3. **Analyze Strategy**: Click "Scalping" button to analyze market conditions
4. **Review Signal**: The system will show if there's a trading setup
5. **Execute Trade** (optional): If you want to execute, click the "Execute Trade" button in the result

## Strategy Quick Reference

| Strategy | Timeframe | Target | Win Rate | Best For |
|----------|-----------|--------|----------|----------|
| **Scalping** | 5-min | 5-10 pips | 55-75% | London-NY overlap, high activity |
| **Breakout** | 15-min | 1:2-1:3 RR | 40-55% | Session opens, volatility spikes |
| **Range Trading** | 1-hour | 1:1 RR | 60-80% | Asian session, quiet periods |
| **Trend Following** | 15-min | 1.5:1 RR | 30-50% | Trending markets, clear direction |

## Current Market Context (Feb 2026)

Per the CLAUDE.md guide:
- **USD Weakness**: EUR/USD at 1.18-1.20, consider selling USD rallies
- **Market Mode**: Ranging with event-driven spikes
- **Best Strategy**: Range trading + event trading around news
- **Caution**: JPY shorts near 157-160 (intervention zone)

## Best Trading Times (UTC)

- **13:00-17:00**: London-NY overlap (BEST - highest liquidity)
- **08:00-17:00**: London session (Good - 38% of volume)
- **00:00-09:00**: Asian session (Range trading only)
- **20:00-00:00**: AVOID (dead zone)

## Risk Management Reminders

- Each trade risks **1% of account balance**
- Maximum **3 concurrent positions**
- Daily loss limit: **3-5%** of account
- Stop losses are **ATR-based** (adapts to volatility)

## Common Commands

```bash
# View logs
docker-compose logs -f web

# Stop platform
docker-compose down

# Restart platform
docker-compose restart web

# Reset database (WARNING: deletes all trades)
docker-compose down -v
docker-compose up --build

# View trades in database
docker-compose exec db psql -U trading_user -d trading_db -c "SELECT instrument, direction, entry_price, pnl, status FROM trades ORDER BY entry_time DESC LIMIT 10;"
```

## API Testing

```bash
# Check account
curl http://localhost:5000/api/account

# Analyze EUR/USD with scalping strategy
curl -X POST http://localhost:5000/api/strategies/scalping/analyze \
  -H "Content-Type: application/json" \
  -d '{"instrument": "EUR_USD"}'

# Get strategy performance
curl http://localhost:5000/api/strategies/scalping/performance
```

## Troubleshooting

**Can't connect to API?**
```bash
# Test your credentials directly
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api-fxpractice.oanda.com/v3/accounts/YOUR_ACCOUNT_ID/summary
```

**Port 5000 already in use?**
- Change port in docker-compose.yml: `ports: - "8000:5000"`

**Database errors?**
```bash
docker-compose down -v
docker-compose up --build
```

## Next Steps

1. **Paper Trade First**: Run in analysis mode for a week
2. **Track Performance**: Check `/api/strategies/<name>/performance`
3. **Review CLAUDE.md**: Detailed trading guide with strategies
4. **Monitor During Peak Hours**: 13:00-17:00 UTC
5. **Focus on Major Pairs**: EUR/USD, GBP/USD, USD/JPY

## Important Notes

- This is a **demo account** - no real money
- Always review signals before executing
- Strategies follow CLAUDE.md trading guide principles
- Keep effective leverage at 4:1-10:1
- Markets are unpredictable - past performance doesn't guarantee future results

## Getting Help

- Check README.md for full documentation
- Review CLAUDE.md for trading strategy details
- Check logs: `docker-compose logs -f web`
- Database issues: Reset with `docker-compose down -v`

Happy trading!
