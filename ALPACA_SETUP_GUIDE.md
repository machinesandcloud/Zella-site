# Alpaca Integration Setup Guide

## Overview

This guide will help you set up and verify the Alpaca trading integration for Zella AI Trading.

## Quick Start

### 1. Get Your Alpaca API Keys

1. Go to https://app.alpaca.markets/paper/dashboard/overview
2. Navigate to the **API** section in the left sidebar
3. Create new API keys (or use existing ones)
4. Copy both:
   - **API Key ID** (starts with `PK...`)
   - **Secret Key** (longer alphanumeric string)

### 2. Configure Environment Variables on Render

In your Render dashboard for the backend service:

1. Go to **Environment** tab
2. Add these environment variables:

```
ALPACA_API_KEY=PK4OSPAJK3ZOXQIGDJECJQ5NDZ
ALPACA_SECRET_KEY=Dx6wUAkAQNwheZccVfUuKmrDqU4xPcNH2xPgpYeReC
ALPACA_PAPER=true
```

**IMPORTANT**:
- Do NOT wrap values in quotes
- Use your actual API keys (the ones above are just examples)
- Set `ALPACA_PAPER=true` for paper trading ($100k virtual money)
- Set `ALPACA_PAPER=false` only when ready for real money trading

3. Save and **manually restart** the service (or wait for auto-deploy)

### 3. Verify Connection

After deployment completes:

1. Open your frontend at https://zella-site.netlify.app
2. Auto-login should work (auto-authentication enabled)
3. Look for the Alpaca status in the dashboard
4. You should see:
   - **Status**: Connected
   - **Mode**: PAPER
   - **Account Balance**: ~$100,000

## Troubleshooting

### Status Shows "Not Connected"

Check the Render logs for one of these messages:

#### ✓ Good: Successfully Connected
```
Alpaca initialization: use_alpaca=False, effective=True
Alpaca keys configured: api_key=True, secret=True, paper=True
Creating Alpaca client (paper=True)...
✓ Alpaca connected successfully (paper=True)
```

#### ✗ Bad: API Keys Not Set
```
Alpaca initialization: use_alpaca=False, effective=False
✗ Alpaca enabled but API keys missing: api_key=MISSING, secret=MISSING
```

**Fix**: Double-check environment variables on Render. Make sure they're spelled exactly:
- `ALPACA_API_KEY` (not `ALPACA_KEY` or `API_KEY`)
- `ALPACA_SECRET_KEY` (not `ALPACA_SECRET` or `SECRET_KEY`)
- `ALPACA_PAPER`

#### ✗ Bad: Invalid API Keys
```
Creating Alpaca client (paper=True)...
✗ Alpaca client created but initial connection failed - will retry on API calls
```

**Fix**:
1. Go to Alpaca dashboard and regenerate API keys
2. Make sure you're using **Paper Trading** API keys (not live keys for paper mode)
3. Check that keys aren't revoked or expired

#### ✗ Bad: Timeout/Network Issue
```
Alpaca connection timeout: Request timed out after 10 seconds
```

**Fix**:
- Check Render service network connectivity
- Verify Alpaca API status at https://status.alpaca.markets/
- Try manual restart

### Frontend Shows "Enabled: false"

The new status endpoint returns detailed diagnostics:

```json
{
  "enabled": false,
  "connected": false,
  "reason": "Alpaca not enabled in configuration",
  "help": "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables"
}
```

Follow the `help` message to fix the issue.

### CORS Errors

If you see CORS errors in browser console:

1. Make sure `cors_allowed_origins` includes your frontend domain
2. The CORS regex should be: `r"https://.*\.netlify\.app"` (single backslash)
3. Check Render environment variables:
   - `CORS_ALLOWED_ORIGINS=https://zella-site.netlify.app,http://localhost:3000`
   - `CORS_ALLOW_ORIGIN_REGEX=https://.*\.netlify\.app`

## Manual Testing

### Test Status Endpoint

```bash
# Get auth token
TOKEN=$(curl -s -X POST https://zella-site.onrender.com/api/auth/auto-login | jq -r '.access_token')

# Check Alpaca status
curl -s -H "Authorization: Bearer $TOKEN" \
  https://zella-site.onrender.com/api/alpaca/status | jq .

# Expected output (success):
{
  "enabled": true,
  "connected": true,
  "mode": "PAPER",
  "paper_trading": true
}
```

### Test Account Endpoint

```bash
# Get account summary
curl -s -H "Authorization: Bearer $TOKEN" \
  https://zella-site.onrender.com/api/alpaca/account | jq .

# Expected output:
{
  "AccountValue": "100000.00",
  "BuyingPower": "400000.00",
  "Cash": "100000.00",
  "PortfolioValue": "100000.00",
  ...
}
```

### Test Connect with New Credentials

```bash
# Connect with new API keys
curl -s -X POST https://zella-site.onrender.com/api/alpaca/connect \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_NEW_API_KEY",
    "secret_key": "YOUR_NEW_SECRET_KEY",
    "paper": true
  }' | jq .

# Expected output:
{
  "status": "connected",
  "mode": "PAPER",
  "new_credentials": true
}
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_ALPACA` | No | `false` | Explicitly enable Alpaca (auto-enabled if keys present) |
| `ALPACA_API_KEY` | Yes* | `""` | Your Alpaca API key ID (from dashboard) |
| `ALPACA_SECRET_KEY` | Yes* | `""` | Your Alpaca secret key (from dashboard) |
| `ALPACA_PAPER` | No | `true` | Use paper trading (true) or live trading (false) |

*Required if you want to use Alpaca

### Auto-Enable Logic

Alpaca is automatically enabled if:
- `USE_ALPACA=true`, OR
- Both `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are non-empty

This means you don't need to set `USE_ALPACA` if you provide the API keys.

## API Endpoints

### GET /api/alpaca/status
Get connection status with diagnostics.

**Response**:
```json
{
  "enabled": true,
  "connected": true,
  "mode": "PAPER",
  "paper_trading": true
}
```

Or with error:
```json
{
  "enabled": true,
  "connected": false,
  "reason": "Not connected to Alpaca",
  "help": "Click 'Connect' to establish connection, or check API keys if connection fails"
}
```

### POST /api/alpaca/connect
Connect or reconnect to Alpaca.

**Request Body** (optional):
```json
{
  "api_key": "PK...",
  "secret_key": "...",
  "paper": true
}
```

If body is empty, reconnects existing client. If credentials provided, creates new client.

### GET /api/alpaca/account
Get account summary (balance, buying power, etc.)

### GET /api/alpaca/positions
Get all open positions

### GET /api/alpaca/orders?status=open
Get orders (filter by status: open, closed, all)

### POST /api/alpaca/order
Place an order

**Request Body**:
```json
{
  "symbol": "AAPL",
  "quantity": 10,
  "side": "BUY",
  "order_type": "MARKET"
}
```

### GET /api/alpaca/quote/{symbol}
Get latest quote for a symbol

### GET /api/alpaca/bars/{symbol}?timeframe=1Min&limit=100
Get historical price bars

## Security Notes

1. **Never commit API keys to git** - always use environment variables
2. **Use paper trading for testing** - set `ALPACA_PAPER=true`
3. **Rotate API keys regularly** - especially if exposed
4. **Monitor usage** - check Alpaca dashboard for unexpected activity
5. **Enable 2FA** - on your Alpaca account for extra security

## Common Issues

### "Alpaca not enabled" but I set the env vars

- Restart the Render service after adding environment variables
- Check spelling of variable names (case-sensitive)
- Verify variables are set in the correct service (backend, not frontend)

### Connection works locally but not on Render

- Render environment variables are separate from local .env file
- Double-check Render dashboard environment tab
- Check Render logs for initialization messages

### Orders fail with "Account not found"

- Make sure you're using the correct API keys (paper vs. live)
- Verify your Alpaca account is activated and approved
- Check that you're not using sandbox/test keys with live API

## Support

- **Alpaca Documentation**: https://docs.alpaca.markets/
- **Alpaca API Status**: https://status.alpaca.markets/
- **Alpaca Support**: support@alpaca.markets

## Next Steps

Once Alpaca is connected:

1. Test placing a paper trade with a small quantity
2. Verify the order appears in Alpaca dashboard
3. Check positions and account balance update correctly
4. Set up risk limits in `/api/settings/risk`
5. Configure trading strategies in the dashboard
6. Monitor performance and logs

**Remember**: Always test with paper trading before using real money!
