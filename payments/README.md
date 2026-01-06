# Payment Module

This module provides a framework for integrating multiple payment providers for the Telegram bot's credit system.

## Structure

- **`base_payment.py`** - Abstract base class (`PaymentProvider`) and payment manager
- **`telegram_stars_provider.py`** - ✅ Telegram Stars payment integration (IMPLEMENTED)
- **`wechat_alipay_provider.py`** - ✅ WeChat Pay + Alipay integration (IMPLEMENTED)

## Implemented Providers

### 1. Telegram Stars Provider (`telegram_stars_provider.py`)

Uses Telegram's native Stars cryptocurrency for payments.

**Features**:
- Native Telegram payment UI
- Instant payment confirmation
- No external gateway required
- Automatic currency conversion (Stars ⭐)

**Methods**:
- `create_payment()` - Create invoice for user
- `check_payment_status()` - Check payment status
- `handle_successful_payment()` - Process successful payment
- `refund_payment()` - Refund Stars to user
- `get_payment_details()` - Get payment details

### 2. WeChat + Alipay Provider (`wechat_alipay_provider.py`)

Combined provider for Chinese payment methods via third-party gateway.

**Features**:
- WeChat Pay support
- Alipay support
- QR code generation
- Payment callback handling
- 3-minute payment timeout

**Methods**:
- `create_payment()` - Generate payment QR code
- `check_payment_status()` - Check payment via callback
- `handle_callback()` - Process payment gateway callback
- `refund_payment()` - Refund via gateway
- `get_payment_details()` - Get payment details

## Usage

### 1. Register Providers in Bot

```python
from payments.base_payment import PaymentManager
from payments.telegram_stars_provider import TelegramStarsProvider
from payments.wechat_alipay_provider import WeChatAlipayProvider

# Initialize payment manager
payment_manager = PaymentManager(config)

# Register providers
payment_manager.register_provider('stars', TelegramStarsProvider(config, translation_service))
payment_manager.register_provider('wechat_alipay', WeChatAlipayProvider(config, translation_service))
```

### 2. Create Payment in Handler

```python
# Get selected provider
provider = payment_manager.get_provider('stars')  # or 'wechat_alipay'

# Create payment
payment_info = await provider.create_payment(
    user_id=user_id,
    amount=32.00,  # CNY
    currency='CNY',
    credits=120,
    description="Top-up 120 credits"
)

# payment_info contains:
# - payment_id: Unique payment ID
# - amount: Payment amount
# - credits: Credits to add
# - Additional provider-specific data
```

### 3. Check Payment Status

```python
# Check if payment completed
status = await provider.check_payment_status(payment_id)

if status == PaymentStatus.COMPLETED:
    # Add credits to user
    await credit_service.add_credits(user_id, credits, "top-up")
```

## Configuration

### Required Environment Variables

```env
# Telegram Stars - No configuration needed (uses bot token)

# WeChat/Alipay Gateway
WECHAT_ALIPAY_API_URL=https://your-gateway.com/api
WECHAT_ALIPAY_API_KEY=your_api_key
WECHAT_ALIPAY_MERCHANT_ID=your_merchant_id
```

### Payment Manager Setup

The `PaymentManager` handles:
- Provider registration
- Provider selection
- Common payment operations

```python
payment_manager = PaymentManager(config)
payment_manager.register_provider('provider_name', ProviderInstance(config))

# Use provider
provider = payment_manager.get_provider('provider_name')
result = await provider.create_payment(...)
```

## Payment Flow

### Telegram Stars Flow:
1. User selects package → `create_payment()`
2. Bot sends Telegram invoice
3. User pays with Stars
4. Telegram sends `successful_payment` update
5. `handle_successful_payment()` processes it
6. Credits added to user account

### WeChat/Alipay Flow:
1. User selects package → `create_payment()`
2. Gateway generates QR code
3. Bot displays QR code to user
4. User scans and pays
5. Gateway sends callback to server
6. `handle_callback()` processes it
7. Credits added to user account

## Payment Status

Defined in `core/constants.py`:

```python
class PaymentStatus(Enum):
    PENDING = "pending"      # Payment created, awaiting payment
    COMPLETED = "completed"  # Payment successful
    FAILED = "failed"        # Payment failed
    REFUNDED = "refunded"    # Payment refunded
```

## Database Integration

All payments are stored in the `payments` table:

```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    payment_id TEXT UNIQUE NOT NULL,
    amount REAL NOT NULL,
    credits INTEGER NOT NULL,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

## Extending with New Providers

To add a new payment provider (e.g., Stripe, PayPal):

### 1. Create Provider Class

```python
from payments.base_payment import PaymentProvider
from core.constants import PaymentStatus

class StripeProvider(PaymentProvider):
    def __init__(self, config, translation_service=None):
        super().__init__(config)
        self.stripe_api_key = config.get('STRIPE_API_KEY')
        self.translation_service = translation_service

    async def create_payment(self, user_id: int, amount: float,
                           currency: str, credits: int, **kwargs) -> Dict:
        # Implement Stripe checkout session creation
        pass

    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        # Check Stripe payment status
        pass

    async def refund_payment(self, payment_id: str,
                           amount: Optional[float] = None,
                           reason: str = "") -> bool:
        # Implement Stripe refund
        pass

    async def get_payment_details(self, payment_id: str) -> Dict:
        # Get Stripe payment details
        pass
```

### 2. Register in Bot

```python
from payments.stripe_provider import StripeProvider

payment_manager.register_provider('stripe', StripeProvider(config, translation_service))
```

### 3. Add Configuration

```env
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Future Enhancements

- [ ] Add Stripe provider for international payments
- [ ] Add PayPal provider
- [ ] Add cryptocurrency payments (Bitcoin, USDT)
- [ ] Implement automatic retry for failed payments
- [ ] Add payment analytics and reporting
- [ ] Add subscription/recurring payment support
- [ ] Implement partial refunds
- [ ] Add payment webhooks for all providers
- [ ] Add fraud detection and prevention

## Notes

- All providers support internationalization via `translation_service`
- Payment amounts are in CNY for WeChat/Alipay, XTR (Stars) for Telegram
- Payment timeout is 180 seconds (3 minutes) by default
- All providers inherit from `PaymentProvider` abstract base class
- Provider selection is handled by user choice in payment flow
