# Payment Module

This module provides a framework for integrating multiple payment providers.

## Structure

- `base_payment.py` - Abstract base class and payment manager
- Payment provider implementations (to be added):
  - `stripe_provider.py` - Stripe integration
  - `alipay_provider.py` - Alipay integration
  - `wechat_provider.py` - WeChat Pay integration
  - `paypal_provider.py` - PayPal integration

## Usage

### 1. Implement a Payment Provider

```python
from payments.base_payment import PaymentProvider
from core.constants import PaymentStatus

class StripeProvider(PaymentProvider):
    async def create_payment(self, user_id, amount, currency):
        # Your Stripe implementation
        pass

    async def check_payment_status(self, payment_id):
        # Check payment status
        pass

    async def refund_payment(self, payment_id, amount=None):
        # Refund logic
        pass

    async def get_payment_details(self, payment_id):
        # Get details
        pass
```

### 2. Register Provider

```python
from payments.base_payment import PaymentManager
from payments.stripe_provider import StripeProvider

payment_manager = PaymentManager(config)
payment_manager.register_provider('stripe', StripeProvider(config))
```

### 3. Use in Handlers

```python
# Create payment
payment_info = await payment_manager.create_payment(
    user_id=user_id,
    amount=9.99,
    currency='USD',
    provider_name='stripe'
)

# Check status
status = await payment_manager.get_provider('stripe').check_payment_status(
    payment_info['payment_id']
)
```

## Configuration

Add payment credentials to `.env`:

```env
# Stripe
STRIPE_API_KEY=sk_test_...

# Alipay
ALIPAY_APP_ID=...
ALIPAY_PRIVATE_KEY=...

# WeChat Pay
WECHAT_MERCHANT_ID=...
WECHAT_API_KEY=...

# PayPal
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
```

## Future Features

- [ ] Implement Stripe provider
- [ ] Implement Alipay provider
- [ ] Implement WeChat Pay provider
- [ ] Implement PayPal provider
- [ ] Add credit/balance system
- [ ] Add payment webhooks
- [ ] Add transaction logging
- [ ] Add refund handling
