# Stripe Integration Merge Guide

This document outlines all changes needed when merging the Stripe payment integration from the `test` branch to `main`.

---

## New Files Created

| File | Description |
|------|-------------|
| `payments/stripe_provider.py` | Stripe payment provider class (Embedded Checkout) |

---

## Modified Files

| File | Changes |
|------|---------|
| `config.py` | Added `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` |
| `payment_webhook.py` | Added Stripe routes: `/stripe/webhook`, `/stripe/checkout`, `/stripe/session-status`, `/stripe/return` |
| `handlers/credit_handlers.py` | Added Stripe payment method button and flow |
| `services/pricing_service.py` | Added Stripe pricing config ($1/30 credits, $5/250 credits) |
| `core/bot_application.py` | Initialize Stripe provider |
| `locales/*.json` | Added Stripe-related translation strings |

---

## Environment Variables

Add to `.env` on production:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_...          # Get from Stripe Dashboard (LIVE key)
STRIPE_PUBLISHABLE_KEY=pk_live_...     # Get from Stripe Dashboard (LIVE key)
STRIPE_WEBHOOK_SECRET=whsec_...        # Generated when creating webhook endpoint
```

⚠️ **Important**: Use LIVE keys for production, not TEST keys.

---

## Stripe Dashboard Configuration

### 1. Webhook Endpoint

1. Go to https://dashboard.stripe.com/webhooks (switch to Live mode)
2. Click **"Add endpoint"**
3. Configure:
   - **Endpoint URL**: `https://telepay.swee.live/stripe/webhook`
   - **Events to listen**:
     - `checkout.session.completed`
     - `checkout.session.expired`
4. Copy the **Signing secret** → add to `.env` as `STRIPE_WEBHOOK_SECRET`

### 2. Apple Pay Domain Verification

1. Go to https://dashboard.stripe.com/settings/payments/apple_pay
2. Add domain: `telepay.swee.live`
3. Download verification file
4. Host at: `https://telepay.swee.live/.well-known/apple-developer-merchantid-domain-association`

> Note: This is already configured for test mode. Need to verify again for live mode.

---

## Nginx Configuration

Add to the production nginx config (if not already present):

```nginx
# Stripe routes - proxy to payment webhook server
location /stripe/ {
    proxy_pass http://127.0.0.1:8081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Apple Pay domain verification
location /.well-known/apple-developer-merchantid-domain-association {
    alias /var/www/html/.well-known/apple-developer-merchantid-domain-association;
}
```

---

## Dependencies

Ensure `stripe` package is installed:

```bash
pip install stripe>=7.0.0
```

Or add to `requirements.txt`:
```
stripe>=7.0.0
```

---

## Testing Checklist

Before going live:

- [ ] Update `.env` with LIVE Stripe keys
- [ ] Create webhook endpoint in Stripe Dashboard (Live mode)
- [ ] Verify Apple Pay domain in Stripe Dashboard (Live mode)
- [ ] Restart payment webhook server
- [ ] Test with a real $1 payment (can refund after)

---

## Test Cards (for test mode only)

| Card | Description |
|------|-------------|
| `4242 4242 4242 4242` | Successful payment |
| `4000 0025 0000 3155` | Requires 3D Secure authentication |
| `4000 0000 0000 9995` | Declined (insufficient funds) |

Use any future expiry date and any 3-digit CVC.

---

## Rollback

If issues occur after merge:

1. Remove Stripe button from `credit_handlers.py`
2. Comment out Stripe routes in `payment_webhook.py`
3. No database changes needed (same `payments` table)

---

## Architecture Notes

- Stripe payments use **direct crediting** via `credit_service.add_credits()`
- Does NOT use `payment_service.process_payment_completion()` (that's for WeChatAlipay only)
- Webhook handler is synchronous with internal `asyncio.run()` for async operations
- Mini App checkout served from `/stripe/checkout` route
