# Credit System Integration Guide

This guide covers the remaining steps to complete the credit/payment system integration.

## ✅ Already Completed

1. **Database Layer**: `services/database_service.py`
2. **Credit Management**: `services/credit_service.py`
3. **Payment Provider**: `payments/wechat_alipay_provider.py`
4. **Payment Service**: `services/payment_service.py`
5. **Constants & Messages**: `core/constants.py`
6. **Workflow Integration**: `services/workflow_service.py`

---

## 🔄 Remaining Steps

### Step 1: Create Credit Handlers

Create `handlers/credit_handlers.py`:

```python
"""Handlers for credit-related operations."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime

logger = logging.getLogger('mark4_bot')

# Injected dependencies
credit_service = None
payment_service = None


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance check request."""
    try:
        user_id = update.effective_user.id

        # Get user stats
        stats = await credit_service.get_user_stats(user_id)

        from core.constants import BALANCE_MESSAGE
        message = BALANCE_MESSAGE.format(
            balance=stats['balance'],
            total_spent=stats['total_spent']
        )

        await update.message.reply_text(message)
        logger.info(f"User {user_id} checked balance: {stats['balance']}")

    except Exception as e:
        logger.error(f"Error checking balance for user {user_id}: {str(e)}")
        await update.message.reply_text("查询余额失败，请稍后重试")


async def show_topup_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top-up package options."""
    try:
        from core.constants import (
            TOPUP_PACKAGES_MESSAGE,
            TOPUP_10_BUTTON,
            TOPUP_30_BUTTON,
            TOPUP_50_BUTTON
        )

        # Create inline keyboard with package options
        keyboard = [
            [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
            [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
            [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            TOPUP_PACKAGES_MESSAGE,
            reply_markup=reply_markup
        )

        logger.info(f"User {update.effective_user.id} viewing top-up packages")

    except Exception as e:
        logger.error(f"Error showing top-up packages: {str(e)}")
        await update.message.reply_text("显示充值套餐失败，请稍后重试")


async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's transaction history."""
    try:
        user_id = update.effective_user.id

        # Get transactions
        transactions = await credit_service.get_transaction_history(user_id, limit=10)

        from core.constants import (
            TRANSACTION_HISTORY_HEADER,
            TRANSACTION_ITEM_TEMPLATE,
            NO_TRANSACTIONS_MESSAGE
        )

        if not transactions:
            await update.message.reply_text(NO_TRANSACTIONS_MESSAGE)
            return

        # Format transactions
        message = TRANSACTION_HISTORY_HEADER
        for tx in transactions:
            date = tx['created_at'][:10]  # Extract date
            tx_type = {
                'topup': '充值',
                'deduction': '消费',
                'refund': '退款'
            }.get(tx['transaction_type'], tx['transaction_type'])

            message += TRANSACTION_ITEM_TEMPLATE.format(
                date=date,
                type=tx_type,
                amount=tx['amount'],
                balance=tx['balance_after']
            )

        await update.message.reply_text(message)
        logger.info(f"User {user_id} viewed transaction history")

    except Exception as e:
        logger.error(f"Error showing transaction history: {str(e)}")
        await update.message.reply_text("查询记录失败，请稍后重试")


async def handle_topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle top-up package selection."""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Extract amount from callback data (topup_10, topup_30, topup_50)
        amount_str = query.data.replace("topup_", "")
        amount_cny = int(amount_str)

        # Create payment
        success, payment_info, error = await payment_service.create_topup_payment(
            user_id,
            amount_cny
        )

        if not success:
            await query.edit_message_text(f"创建支付失败: {error}")
            return

        from core.constants import PAYMENT_PENDING_MESSAGE
        message = PAYMENT_PENDING_MESSAGE.format(
            payment_id=payment_info['payment_id'],
            amount=payment_info['amount_cny'],
            credits=payment_info['credits_amount']
        )

        # Add payment URL button
        keyboard = [[
            InlineKeyboardButton(
                "前往支付",
                url=payment_info['payment_url']
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(message, reply_markup=reply_markup)

        logger.info(
            f"Created payment {payment_info['payment_id']} for user {user_id}: "
            f"¥{amount_cny} = {payment_info['credits_amount']} credits"
        )

    except Exception as e:
        logger.error(f"Error handling top-up callback: {str(e)}")
        try:
            await query.edit_message_text("创建支付失败，请稍后重试")
        except:
            pass
```

---

### Step 2: Update Menu Handlers

Add to `handlers/menu_handlers.py`:

```python
# At the top, add import
from core.constants import (
    MENU_OPTION_CHECK_BALANCE,
    MENU_OPTION_TOPUP,
    MENU_OPTION_HISTORY
)

# In handle_menu_selection function, add these cases:

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu option selection."""
    try:
        text = update.message.text
        user_id = update.effective_user.id

        # ... existing cases ...

        # Credit system menu options
        elif text == MENU_OPTION_CHECK_BALANCE:
            from handlers.credit_handlers import check_balance
            await check_balance(update, context)

        elif text == MENU_OPTION_TOPUP:
            from handlers.credit_handlers import show_topup_packages
            await show_topup_packages(update, context)

        elif text == MENU_OPTION_HISTORY:
            from handlers.credit_handlers import show_transaction_history
            await show_transaction_history(update, context)
```

---

### Step 3: Update Callback Handlers

Add to `handlers/callback_handlers.py`:

```python
async def topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle top-up package selection callbacks."""
    from handlers.credit_handlers import handle_topup_callback
    await handle_topup_callback(update, context)
```

---

### Step 4: Update Command Handlers

Update `handlers/command_handlers.py` to show credit info in /start and /help:

```python
# In start_command, after showing menu, optionally show balance:
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... existing code ...

    # Optionally show balance
    if credit_service:
        stats = await credit_service.get_user_stats(user_id)
        if stats['has_free_trial']:
            balance_info = "🎁 您有1次免费体验机会"
        else:
            balance_info = f"💰 当前积分：{stats['balance']}"
        # Append to welcome message or send separately
```

---

### Step 5: Update Config

Add to `config.py`:

```python
# Database settings
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/mark4_bot.db')

# Payment settings (TODO: Replace with actual credentials)
PAYMENT_API_KEY = os.getenv('PAYMENT_API_KEY', None)
PAYMENT_API_SECRET = os.getenv('PAYMENT_API_SECRET', None)
PAYMENT_API_URL = os.getenv('PAYMENT_API_URL', None)
PAYMENT_MERCHANT_ID = os.getenv('PAYMENT_MERCHANT_ID', None)
PAYMENT_CALLBACK_URL = os.getenv('PAYMENT_CALLBACK_URL', None)
PAYMENT_RETURN_URL = os.getenv('PAYMENT_RETURN_URL', None)
```

Add to `.env`:

```bash
# Database
DATABASE_PATH=data/mark4_bot.db

# Payment (TODO: Replace with actual credentials when available)
# PAYMENT_API_KEY=your_api_key
# PAYMENT_API_SECRET=your_api_secret
# PAYMENT_API_URL=https://payment-api.example.com
# PAYMENT_MERCHANT_ID=your_merchant_id
# PAYMENT_CALLBACK_URL=https://your-server.com/payment/callback
# PAYMENT_RETURN_URL=https://your-server.com/payment/return
```

---

### Step 6: Wire Services in BotApplication

Update `core/bot_application.py`:

```python
# In __init__, add imports:
from services.database_service import DatabaseService
from services.credit_service import CreditService
from services.payment_service import PaymentService
from payments.wechat_alipay_provider import WeChatAlipayProvider

# In __init__, initialize services:
def __init__(self, config: Config):
    # ... existing code ...

    # Initialize database and credit services
    self.database_service = DatabaseService(config)
    self.credit_service = CreditService(config, self.database_service)

    # Initialize payment provider and service
    self.payment_provider = WeChatAlipayProvider(config)
    self.payment_service = PaymentService(
        config,
        self.database_service,
        self.credit_service,
        self.payment_provider
    )

    # Update workflow service initialization to include credit_service
    self.workflow_service = WorkflowService(
        config,
        self.comfyui_service,
        self.file_service,
        self.notification_service,
        self.queue_service,
        self.state_manager,
        credit_service=self.credit_service  # Add this parameter
    )

# In _inject_dependencies:
def _inject_dependencies(self):
    # ... existing injections ...

    # Inject credit dependencies
    from handlers import credit_handlers
    credit_handlers.credit_service = self.credit_service
    credit_handlers.payment_service = self.payment_service

# In _register_handlers, add:
def _register_handlers(self):
    # ... existing handlers ...

    # Credit system callback handlers
    self.app.add_handler(
        CallbackQueryHandler(
            callback_handlers.topup_callback,
            pattern="^topup_"
        )
    )
```

---

### Step 7: Update Menu Display

Update `handlers/command_handlers.py` show_menu function:

```python
from core.constants import (
    SELECT_FUNCTION_MESSAGE,
    MENU_OPTION_IMAGE,
    MENU_OPTION_VIDEO,
    MENU_OPTION_CHECK_QUEUE,
    MENU_OPTION_CHECK_BALANCE,
    MENU_OPTION_TOPUP,
    MENU_OPTION_HISTORY
)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu."""
    menu_text = f"""{SELECT_FUNCTION_MESSAGE}

{MENU_OPTION_IMAGE}
{MENU_OPTION_VIDEO}
{MENU_OPTION_CHECK_QUEUE}

{MENU_OPTION_CHECK_BALANCE}
{MENU_OPTION_TOPUP}
{MENU_OPTION_HISTORY}
"""

    keyboard = [
        [MENU_OPTION_IMAGE],
        [MENU_OPTION_VIDEO],
        [MENU_OPTION_CHECK_QUEUE],
        [MENU_OPTION_CHECK_BALANCE, MENU_OPTION_TOPUP],
        [MENU_OPTION_HISTORY]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(menu_text, reply_markup=reply_markup)
```

---

## Testing Checklist

### 1. Database Initialization
- [ ] Run bot, check `data/mark4_bot.db` is created
- [ ] Verify tables exist: users, transactions, payments, feature_pricing
- [ ] Check default pricing: image_processing = 10 credits

### 2. Free Trial
- [ ] New user starts bot
- [ ] Select "图片脱衣" and upload image
- [ ] Should see "这是您的免费体验！"
- [ ] Image processes successfully
- [ ] Check database: `free_image_processing_used = 1`

### 3. Credit Check
- [ ] Same user tries again without credits
- [ ] Should see "积分不足" message
- [ ] Cannot process without top-up

### 4. Balance Check
- [ ] Select "💰 查看积分余额"
- [ ] See balance and total spent

### 5. Transaction History
- [ ] Select "📊 消费记录"
- [ ] See free trial marked or "暂无消费记录"

### 6. Top-up Flow
- [ ] Select "💳 充值积分"
- [ ] See 3 package options
- [ ] Click package → see payment info (placeholder URL)
- [ ] Check database: payment record created with status 'pending'

### 7. Payment Integration (When Real API Available)
- [ ] Replace placeholder in `wechat_alipay_provider.py`
- [ ] Test real payment creation
- [ ] Implement webhook/callback endpoint
- [ ] Test payment completion → credits added

---

## Payment Callback Endpoint (Future)

When you have the payment API documentation, implement:

```python
# In a new file: handlers/payment_webhook.py
from telegram.ext import ContextTypes

async def handle_payment_callback(callback_data: dict):
    """
    Handle payment callback from acquirer.
    This should be exposed as a webhook endpoint.
    """
    success, payment_id = await payment_service.process_payment_callback(callback_data)

    if success:
        # Notify user via Telegram
        payment = await payment_service.get_payment_info(payment_id)
        if payment:
            user_id = payment['user_id']
            from core.constants import PAYMENT_SUCCESS_MESSAGE
            message = PAYMENT_SUCCESS_MESSAGE.format(
                credits=payment['credits_amount']
            )
            # Send notification to user
            # await bot.send_message(user_id, message)

    return {'status': 'ok'}
```

---

## Database Backup

Important: Backup database regularly:

```bash
# Manual backup
cp data/mark4_bot.db data/mark4_bot_backup_$(date +%Y%m%d).db

# Or add to cron
0 2 * * * cp /path/to/mark4/data/mark4_bot.db /path/to/backups/mark4_bot_$(date +\%Y\%m\%d).db
```

---

## Migration Notes

If you need to add features later:

1. **Add new feature pricing**:
```python
# Direct SQL or add to database_service.py
cursor.execute("""
    INSERT INTO feature_pricing (feature_name, credit_cost, description)
    VALUES ('video_processing', 20.0, '视频脱衣')
""")
```

2. **Add new top-up packages**:
```python
# Update core/constants.py
TOPUP_PACKAGES = {
    10: 30,
    30: 120,
    50: 250,
    100: 600  # New package
}
```

---

## Troubleshooting

### Credits not deducting
- Check `workflow_service.py` has `credit_service` parameter
- Check `bot_application.py` passes `credit_service` to workflow_service
- Check logs for "Deducted credits for user..."

### Balance not showing
- Check database connection
- Check user exists in users table
- Check `credit_handlers.credit_service` is injected

### Payment not creating
- Check payment provider credentials in `.env`
- Check logs for error messages
- Verify placeholder mode warnings

---

## Next Steps After Integration

1. **Get payment API credentials** from your acquirer
2. **Implement signature algorithm** in `_generate_signature()`
3. **Implement callback verification** in `handle_callback()`
4. **Set up webhook endpoint** for payment callbacks
5. **Test with small amounts** before going live
6. **Monitor transaction logs** regularly

---

## Support

For questions about this integration:
1. Check this guide first
2. Review the code comments in each service file
3. Check logs at `logs/bot.log`
4. Examine database with: `sqlite3 data/mark4_bot.db`
