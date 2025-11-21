# Payment Integration Setup Guide

This guide walks you through setting up the WeChat/Alipay payment integration for your Telegram bot.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Webhook Setup](#webhook-setup)
4. [Testing](#testing)
5. [Deployment](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Payment Provider Account
- Register with your payment provider and get verified
- Access the merchant dashboard
- Navigate to: **API Management** → **API Development Documentation**
- Note down your credentials:
  - Merchant ID (pay_memberid)
  - Secret Key
  - Gateway URL

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

New dependencies for payment system:
- `aiohttp` - Async HTTP client for API calls
- `flask` - Web framework for webhook server
- `hypercorn` - ASGI server for async Flask support
- `asgiref` - ASGI/WSGI adapter

---

## Configuration

### 1. Update `.env` File

Edit `/Users/andychoo/mark4/.env` and fill in your payment credentials:

```env
# Payment Configuration (WeChat/Alipay 3rd party acquirer)
PAYMENT_GATEWAY_URL=https://your-gateway-domain.com
PAYMENT_MERCHANT_ID=your_memberid_here
PAYMENT_SECRET_KEY=your_secret_key_here
PAYMENT_NOTIFY_URL=https://your-server.com/payment/callback
PAYMENT_CALLBACK_URL=https://your-server.com/payment/return

# Bank codes (verify with your provider)
PAYMENT_BANKCODE_WECHAT=998
PAYMENT_BANKCODE_ALIPAY=999
```

### 2. Verify Bank Codes

Contact your payment provider to confirm the correct bank codes:
- **WeChat Pay**: Usually `998` or `weixin`
- **Alipay**: Usually `999` or `alipay`

Different providers may use different codes!

---

## Webhook Setup

### Understanding Webhooks

The payment provider sends callbacks to your server when payments complete. You need:
1. **Notify URL** (pay_notifyurl): Server-to-server callback for processing
2. **Callback URL** (pay_callbackurl): User redirect URL after payment

### Option A: Expose Local Development Server (Testing)

For local testing, use **ngrok** to create a public URL:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start your webhook server
python payment_webhook.py 8080

# In another terminal, create tunnel
ngrok http 8080
```

You'll get a URL like: `https://abc123.ngrok.io`

Update your `.env`:
```env
PAYMENT_NOTIFY_URL=https://abc123.ngrok.io/payment/callback
PAYMENT_CALLBACK_URL=https://abc123.ngrok.io/payment/return
```

**Note**: ngrok URLs change on restart. For persistent URLs, use a paid ngrok plan or deploy to production.

### Option B: Production Deployment

Deploy `payment_webhook.py` to a production server:

```bash
# Using gunicorn (recommended for production)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080 payment_webhook:app

# Or using hypercorn directly
hypercorn payment_webhook:app --bind 0.0.0.0:8080
```

Configure nginx/Apache reverse proxy with SSL:
```nginx
server {
    listen 443 ssl;
    server_name your-server.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /payment/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Register Webhook with Provider

1. Log in to your payment provider dashboard
2. Navigate to **API Settings** or **Webhook Configuration**
3. Set the callback URL: `https://your-server.com/payment/callback`
4. Set the return URL: `https://your-server.com/payment/return`
5. Save and verify the URLs

---

## Testing

### 1. Test Payment Creation

Start both the bot and webhook server:

```bash
# Terminal 1: Start webhook server
python payment_webhook.py 8080

# Terminal 2: Start Telegram bot
python telegram_bot.py
```

### 2. Test Flow in Telegram

1. Start the bot: `/start`
2. Select: **5. 💳 充值积分**
3. Choose a package: **¥10 = 30积分**
4. Click **前往支付** button
5. Complete payment on the payment page

### 3. Verify Callback Processing

Watch the webhook server logs:
```
2025-11-21 10:30:45 - payment_webhook - INFO - Received payment callback: 1732174245170480
2025-11-21 10:30:45 - payment_webhook - INFO - Successfully processed payment callback: pay_1732174245170480
```

### 4. Check User Balance

In Telegram:
1. Select: **4. 💰 查看积分余额**
2. Verify credits were added

### 5. Test Image Processing with Credits

1. Select: **1. 图片脱衣**
2. Upload an image
3. Verify 10 credits are deducted
4. Check: **6. 📊 消费记录**

---

## API Implementation Details

### Payment Provider Integration

The implementation in `payments/wechat_alipay_provider.py` includes:

#### 1. Signature Algorithm (MD5)
```python
# 1. Filter empty values and 'pay_md5sign'
# 2. Sort parameters alphabetically
# 3. Format: key1=value1&key2=value2
# 4. Append: &key=SECRET_KEY
# 5. MD5 hash and uppercase
```

#### 2. Create Payment (`/Pay_Index.html`)
- Generates unique order ID (max 20 chars)
- Signs parameters with MD5
- Returns H5 payment URL for user

#### 3. Query Payment (`/Pay_Trade_query.html`)
- Checks payment status
- returncode='00' = success
- Used for manual verification

#### 4. Webhook Callback
- Verifies signature
- Processes payment completion
- Credits user account
- **MUST respond with "OK"** (uppercase)

---

## Deployment Checklist

### Before Going Live

- [ ] Configure production payment credentials
- [ ] Set up SSL certificate for webhook server
- [ ] Deploy webhook server to production
- [ ] Register webhook URLs with payment provider
- [ ] Test with small amounts first (¥0.01 if supported)
- [ ] Set up monitoring/alerting for webhook failures
- [ ] Configure database backups
- [ ] Test callback signature verification
- [ ] Verify "OK" response format
- [ ] Load test webhook endpoint

### Production Environment Variables

```env
# Use HTTPS URLs in production
PAYMENT_GATEWAY_URL=https://payment-gateway-production.com
PAYMENT_NOTIFY_URL=https://your-production-domain.com/payment/callback
PAYMENT_CALLBACK_URL=https://your-production-domain.com/payment/return
```

### Security Considerations

1. **Always verify callback signatures** - Prevents fake payment notifications
2. **Use HTTPS** - Required for PCI compliance
3. **Validate amounts** - Compare callback amount with database record
4. **Prevent double-processing** - Check payment status before crediting
5. **Log everything** - Keep audit trail of all transactions
6. **Rate limiting** - Prevent webhook spam/abuse
7. **IP whitelisting** - Only accept callbacks from provider IPs (if supported)

---

## Troubleshooting

### Payment Creation Fails

**Error**: `Payment provider not configured`
- **Solution**: Check `.env` file has all required variables set
- Verify `PAYMENT_GATEWAY_URL`, `PAYMENT_MERCHANT_ID`, `PAYMENT_SECRET_KEY`

**Error**: `Payment creation failed: HTTP 403`
- **Solution**: Invalid signature or merchant ID
- Double-check your `PAYMENT_MERCHANT_ID` and `PAYMENT_SECRET_KEY`
- Verify signature algorithm matches provider's documentation

**Error**: `Payment creation failed: HTTP 500`
- **Solution**: Provider server error
- Check provider's status page
- Retry after a few minutes

### Webhook Not Receiving Callbacks

**Issue**: Payment completes but credits not added
- Check webhook server is running: `curl http://localhost:8080/health`
- Verify webhook URL is publicly accessible
- Check provider dashboard for failed callback logs
- Ensure firewall allows incoming connections

**Issue**: Signature verification fails
- Check `PAYMENT_SECRET_KEY` is correct
- Verify callback parameters are not modified
- Check signature algorithm implementation
- Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`

### Testing Signature Verification

```python
# Test signature generation
from payments.wechat_alipay_provider import WeChatAlipayProvider
from config import Config

config = Config()
provider = WeChatAlipayProvider(config)

params = {
    'pay_memberid': 'your_memberid',
    'pay_orderid': '12345',
    'pay_amount': '10.00',
    'pay_bankcode': '999',
    'pay_notifyurl': 'https://example.com/callback',
    'pay_callbackurl': 'https://example.com/return'
}

signature = provider._generate_signature(params)
print(f"Signature: {signature}")
```

### Database Issues

**Issue**: `no such table: users`
- **Solution**: Database not initialized
- Run the bot once to create tables automatically
- Check `DATABASE_PATH` in `.env` points to correct location

**Issue**: Transaction not recorded
- Check logs for database errors
- Verify database file has write permissions
- Check disk space

---

## Monitoring & Logging

### Important Logs to Watch

1. **Payment Creation**:
   ```
   Created payment {payment_id} for user {user_id}: ¥{amount} via {method}
   ```

2. **Callback Received**:
   ```
   Payment callback received: {payment_id} = ¥{amount}
   ```

3. **Credits Added**:
   ```
   Completed payment {payment_id}: credited {credits} credits, new balance: {balance}
   ```

4. **Signature Verification**:
   ```
   Invalid callback signature! Received: xxx..., Calculated: yyy...
   ```

### Set Up Alerts

Monitor for:
- Failed signature verifications (potential fraud)
- Payment webhook server downtime
- Database connection errors
- Failed credit additions

---

## Support

If you encounter issues not covered in this guide:

1. Check the logs in `logs/bot.log`
2. Enable debug logging: `LOG_LEVEL=DEBUG` in `.env`
3. Review payment provider documentation
4. Check provider's support portal for API changes

---

## Summary

✅ **What's Implemented**:
- Complete payment API integration with signature verification
- Webhook server for automated payment processing
- Credit system with transaction logging
- Free trial for new users
- Top-up packages: ¥10, ¥30, ¥50
- Payment history tracking

🔄 **What's Required**:
- Fill in `.env` with your payment credentials
- Deploy webhook server with public HTTPS URL
- Register webhook URLs with payment provider
- Test with real transactions

📚 **Key Files**:
- `payments/wechat_alipay_provider.py` - Payment API implementation
- `payment_webhook.py` - Webhook server
- `services/payment_service.py` - Payment orchestration
- `services/credit_service.py` - Credit management
- `.env` - Configuration

Good luck with your payment integration! 🚀
