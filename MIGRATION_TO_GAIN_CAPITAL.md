# Migration to GAIN Capital API

The platform has been updated to use the correct **GAIN Capital API** (instead of OANDA v20).

## What Changed

### Authentication
**Before (OANDA):**
- API Key (token)
- Account ID

**After (GAIN Capital):**
- Username
- Password
- AppKey

### API Endpoint
**Before:** `https://api-fxpractice.oanda.com`
**After:** `https://ciapi.cityindex.com/TradingAPI`

## Required Actions

### 1. Update Your `.env` File

Replace the old credentials with new ones:

```bash
# OLD - Remove these
# FOREX_API_KEY=...
# FOREX_ACCOUNT_ID=...
# FOREX_ENVIRONMENT=practice

# NEW - Add these
FOREX_USERNAME=your_forex_username
FOREX_PASSWORD=your_forex_password
FOREX_APPKEY=your_appkey_from_forex
```

### 2. Restart the Platform

```bash
# Stop current containers
docker-compose down

# Rebuild and start with new API
docker-compose up --build
```

### 3. Test the Connection

Visit http://localhost:5000 - you should now see your correct account balance!

## What Was Updated

### Files Changed:
1. **`app/services/forex_client.py`** - Complete rewrite for GAIN Capital API
2. **`app/config.py`** - Updated credentials
3. **`app/routes/*.py`** - Updated client initialization (4 files)
4. **`.env.example`** - New credential template
5. **`docker-compose.yml`** - New environment variables

### API Differences:

| Feature | OANDA v20 | GAIN Capital |
|---------|-----------|--------------|
| Auth | Bearer token | Session-based |
| Instruments | String codes | Market IDs |
| Candles | Direct access | Requires market lookup |
| Orders | Simple structure | IfDone conditions |

### Known Limitations (Will Be Fixed):

1. **`get_candles()`** - Returns empty for now (needs market ID mapping)
2. **`get_prices()`** - Returns empty for now (use streaming API for real-time)
3. **`get_instruments()`** - Returns empty (needs market search endpoint)

These limitations don't affect:
- ✅ Account balance display
- ✅ Position monitoring
- ✅ Opening/closing trades
- ✅ Strategy execution (basic functionality)

## Getting Your Credentials

Your Forex.com demo account provides:
- **Username**: Your login username
- **Password**: Your login password
- **AppKey**: Contact Forex.com support or check your API settings

## Troubleshooting

### "Authentication failed"
- Double-check username, password, and AppKey in `.env`
- Make sure there are no extra spaces
- AppKey is case-sensitive

### "No trading accounts found"
- Your account must be approved for API access
- Contact Forex.com support to enable API trading

### Still seeing old errors?
```bash
# Full reset
docker-compose down -v
docker-compose up --build
```

## Next Steps

Once the platform shows your correct balance:
1. Test account info: `curl http://localhost:5000/api/account`
2. Check positions: `curl http://localhost:5000/api/account/positions`
3. Try the dashboard: http://localhost:5000

## Sources & Documentation

- [GAIN Capital API Docs](https://docs.labs.gaincapital.com/)
- [LogOn Endpoint](https://docs.labs.gaincapital.com/Content/HTTP%20Services/LogOn.htm)
- [gcapi-python Reference](https://github.com/rickykim93/gcapi-python)
