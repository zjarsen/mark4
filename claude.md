# Project Guidelines for Mark4 Telegram Bot

## Project Overview
Telegram bot with python-telegram-bot library providing AI-powered image processing with credit-based payments.

## Critical Rules - ALWAYS FOLLOW THESE

### 1. Security & Credentials - EXTREMELY CRITICAL
**🚨 NEVER HARDCODE SECRETS IN CODE OR CONFIG FILES 🚨**

- **ALL secrets MUST be in `.env` file ONLY** - Bot tokens, API keys, database credentials, payment secrets
- **NEVER hardcode in:** `.py` files, config files, JSON/YAML, Docker files, anything committed to git
- **Always use:** `os.getenv()` or `python-dotenv` to load secrets
- **Verify:** `.env` is in `.gitignore`

```python
# ✅ CORRECT                          # ❌ WRONG
BOT_TOKEN = os.getenv('BOT_TOKEN')    BOT_TOKEN = "1234567890:ABCdef..."
```

**Required `.env` variables:** `BOT_TOKEN`, `BACKUP_BOT_TOKEN`, `DATABASE_URL`, `ALIPAY_APP_ID`, `ALIPAY_PRIVATE_KEY`, `WECHAT_APP_ID`, `WECHAT_SECRET`, `WEBHOOK_SECRET`, `ENCRYPTION_KEY`

**If you see a hardcoded secret:** STOP → Move to `.env` → Update code → Alert user → Advise rotating if committed

### 2. Currency & Pricing
- **NEVER hardcode currency symbols in translation files**
- All price formatting through `services/pricing_service.py`
- Payment methods: Telegram Stars (`{price} ⭐`), Alipay/WeChat (`¥{price}`)
- `pricing_service.calculate_price()` returns `price_info['display']` with currency already formatted
- Translation placeholders: `{discounted_price}`, `{original_price}` - NO currency prefix!

### 3. Multi-language Support
- **6 languages:** zh_CN, zh_TW, en_US, ko_KR, ar_SA, hi_IN
- **ALL user-facing text in translation files** - never hardcode strings

**Translation Workflow:**
- **Development:** ONLY update `zh_CN` first, test feature in Chinese
- **Translation:** After feature complete, user requests other 5 languages
  - Use zh_CN as source, preserve tone/vibe/energy, adapt naturally for target language
- **Editing existing translations:** Ask user if change should propagate to all 6 languages

### 4. VIP System
- Two tiers: `regular` (永久VIP, 160) and `black_gold` (黑金VIP, 260)
- VIP = unlimited usage, Black Gold = priority queue
- VIP status is permanent (lifetime)

### 5. Credit & Payment System
- Credits: "积分" (Chinese) / "credits" (English)
- Costs: 10 credits/image, 30 credits/video
- Free tier: "粉色蕾丝内衣" (Pink Lace) with daily limits
- "脱到精光" (Full Undress): Free once/2 days OR 10 credits

### 6. Discount System
- Daily lucky discount: SSR (50%), SR (30%), R (15%), C (5%)
- Resets at 24:00 (GMT+8)
- Eligible: 30, 50, 100 credits + VIP packages

## Code Architecture

**Key Files:**
- `core/bot_application.py` - Main entry point
- `handlers/credit_handlers.py` - Top-up/payment handlers
- `services/pricing_service.py` - Price calculation/formatting
- `payments/telegram_stars_provider.py` - Stars integration
- `locales/*.json` - Translation files

**Payment Flow:**
1. User selects package → `credit_handlers.py`
2. Calculate price → `pricing_service.calculate_price()`
3. Format with currency → `price_info['display']`
4. Generate button text → translation keys with formatted price
5. Complete payment → credits added

## Common Patterns

```python
# Price calculation
price_info = pricing_service.calculate_price(base_amount, payment_method, discount_info)
# price_info['display'] = "165 ⭐" or "¥32" (already formatted!)

# Button text
button_text = translation_service.get(user_id, 'topup.button_vip_with_discount',
    discounted_price=price_info['display'],
    original_price=pricing_service.format_price_display(price_info['base_price'], payment_method))
```

```json
// Translation format - NO currency symbols!
{ "button_vip_with_discount": "💎 永久VIP {discounted_price} 🎁（原价{original_price}）" }
```

## Common Mistakes to Avoid
- 🚨 Hardcoding secrets in code/config instead of `.env`
- ❌ Adding ¥ in translation strings
- ❌ Hardcoding user-facing text in Python
- ❌ Forgetting to update all 6 language files
- ❌ Mixing up VIP amounts (160 vs 260)

## Package Structure
```
Credits: 2→5, 10→30, 30→120, 50→250, 100→600
VIP: 160 = Lifetime VIP (¥173), 260 = Black Gold VIP (¥281)
```

## Text Formatting (Telegram MarkdownV1)

**Syntax:** Bold `*text*`, Italic `_text_`, Code `` `text` ``
- Use single asterisks/underscores only (NOT `**` or `__`)

**What to Bold:** Numbers, prices, percentages, discounts, VIP tiers, "FREE", time limits, CTAs, queue positions
**What to Italicize:** Tips, hints, soft CTAs, supplementary info
**What NOT to Bold:** Entire paragraphs, regular text, emojis

**Principle:** Preserve tone from zh_CN when translating. Bold creates visual hierarchy - don't overdo it.

## Important Notes
- Telegram Stars: 35% commission vs Alipay/WeChat: 8%
- All credits are permanent (never expire)
- Daily limits only for free tier "Pink Lace" style
- Queue system prioritizes VIP users
