# Project Guidelines for Mark4 Telegram Bot

## Project Overview
This is a Telegram bot built with python-telegram-bot library that provides AI-powered image processing services with a credit-based payment system.

## Critical Rules - ALWAYS FOLLOW THESE

### 1. Currency & Pricing System
- **NEVER hardcode currency symbols in translation files**
- All price formatting MUST go through `services/pricing_service.py`
- The pricing service handles three payment methods:
  - **Telegram Stars (XTR)**: Format as `{price} ⭐` (e.g., "165 ⭐")
  - **Alipay (CNY)**: Format as `¥{price}` (e.g., "¥32")
  - WeChat Pay (CNY)**: Format as `¥{price}` (e.g., "¥32")
- `pricing_service.calculate_price()` returns `price_info['display']` which already includes the formatted price with currency symbol
- Translation strings should NEVER add extra ¥ or other currency symbols - use placeholders like `{discounted_price}` and `{original_price}` without any prefix

### 2. Multi-language Support
- **ALL user-facing text MUST be in translation files**
- Support 6 languages: zh_CN (Simplified Chinese), zh_TW (Traditional Chinese), en_US (English), ko_KR (Korean), ar_SA (Arabic), hi_IN (Hindi)
- Never hardcode user-facing strings in Python code
- Translation keys use dot notation: `section.key` (e.g., `topup.button_vip_with_discount`)

**Translation Workflow - CRITICAL:**
- **Development Phase**: When adding new features, ONLY update `zh_CN` first
  - Always use the translation service in Python code (never hardcode strings)
  - Add new translation keys to `locales/zh_CN.json` only
  - The user will build and test the feature in Chinese first
- **Translation Phase**: After the feature is complete and tested:
  - The user will manually request translation to other 5 languages
  - **ALWAYS use zh_CN (Simplified Chinese) as the source for translation**
  - When translating to other languages:
    - Accurately copy the **tone and vibe** from the Chinese original
    - Adapt the style to look natural and native for target language speakers
    - Preserve the emotional intent and casual/formal level
    - Match the energy and personality (e.g., if Chinese is playful, keep it playful in the target language)
  - Example: If Chinese uses casual gaming terms like "神级运气" (god-tier luck), translate to equivalent natural expressions in the target language, not literal word-for-word
- **DO NOT** translate to all 6 languages during feature development unless explicitly requested
- **IMPORTANT - Editing Existing Translations**: When modifying existing user-facing text in ANY translation JSON:
  - ALWAYS THINK: Does this change need to be applied to other language files?
  - If you change wording, fix a bug, or update text in one language, you likely need to update all 6 languages
  - Ask the user if unsure: "I see you changed X in zh_CN. Should I update the other 5 languages too?"
  - Exception: Bug fixes specific to one language (e.g., grammar error) don't need propagation

### 3. VIP System
- Two VIP tiers: `regular` (永久VIP) and `black_gold` (黑金VIP)
- VIP users get unlimited usage without credit deduction
- Black Gold VIP gets priority queue processing
- Base amounts: 160 = VIP, 260 = Black Gold VIP
- VIP status is permanent (lifetime)

### 4. Credit & Payment System
- Credits are called "积分" (points) in Chinese, "credits" in English
- Image processing costs: 10 credits per use
- Video processing costs: 30 credits per use
- Free tier: "粉色蕾丝内衣" (Pink Lace) style is free with daily limits
- "脱到精光" (Full Undress) style: Free once every 2 days OR 10 credits

### 5. Discount System
- Daily lucky discount system with 4 tiers:
  - SSR (神级运气): 50% off
  - SR (超级运气): 30% off
  - R (运气不错): 15% off
  - C (普通运气): 5% off
- Discounts reset daily at 24:00 (GMT+8)
- Discount applies to ALL payment methods equally
- Eligible packages: 30, 50, 100 credits + VIP tiers (160, 260)

## Code Architecture

### Key Files
- `core/bot_application.py` - Main bot application entry point
- `handlers/credit_handlers.py` - Top-up and payment flow handlers (lines 222-249: button generation)
- `services/pricing_service.py` - Price calculation and formatting (lines 19-44: PRICING_CONFIGS)
- `payments/telegram_stars_provider.py` - Telegram Stars payment integration
- `locales/*.json` - All translation files

### Payment Flow
1. User selects package → `credit_handlers.py`
2. System calculates price → `pricing_service.calculate_price()`
3. Price formatted with currency → `price_info['display']`
4. Button text generated → Uses translation keys with formatted price
5. User completes payment → Credits added to account

### Discount Application
- Discount info passed to pricing service
- `pricing_service.py` applies discount percentage
- Returns both `display` (discounted) and `base_price` (original)
- Button shows: `{discounted_price} 🎁(原价{original_price})`

## Common Patterns

### Translation String Format
```json
{
  "button_vip_with_discount": "💎 永久VIP {discounted_price} 🎁（原价{original_price}）"
}
```
Note: NO ¥ symbol hardcoded - pricing_service handles it!

### Price Calculation Pattern
```python
price_info = pricing_service.calculate_price(
    base_amount=base_amount,
    payment_method='stars',  # or 'alipay', 'wechat'
    discount_info=discount_info
)
# price_info['display'] = "165 ⭐" or "¥32" (already formatted!)
# price_info['base_price'] = original price before discount
```

### Button Text Generation Pattern
```python
button_text = translation_service.get(
    user_id,
    'topup.button_vip_with_discount',
    discounted_price=price_info['display'],  # Already has currency!
    original_price=pricing_service.format_price_display(price_info['base_price'], payment_method)
)
```

## Development Workflow

### Adding New Features
1. Update Python handlers/services as needed
2. Add translation keys to `locales/zh_CN.json` ONLY (Chinese first, test feature)
3. After feature is tested and complete, user will request translation to other 5 languages
4. Test with different payment methods to ensure currency symbols are correct
5. Verify VIP users get proper unlimited access

### Testing Payment Changes
- Test all 3 payment methods: Telegram Stars, Alipay, WeChat
- Verify currency symbols: ⭐ for Stars, ¥ for Alipay/WeChat
- Check discount application across all tiers
- Confirm VIP purchases work correctly

### Common Mistakes to Avoid
- ❌ Adding ¥ in translation strings (e.g., `"¥{discounted_price}"`)
- ❌ Hardcoding user-facing text in Python code
- ❌ Forgetting to update all 6 language files
- ❌ Mixing up VIP base amounts (160 vs 260)
- ❌ Not preserving discount eligibility for certain packages

## Package Structure
```
Base Packages (credits):
- 2 = 5 credits (test package)
- 10 = 30 credits
- 30 = 120 credits
- 50 = 250 credits
- 100 = 600 credits

VIP Packages:
- 160 = Lifetime VIP (¥173 base price)
- 260 = Black Gold VIP (¥281 base price)
```

## Text Formatting Guidelines

### MarkdownV1 Syntax (Telegram)
All user-facing messages use Telegram's MarkdownV1 parser. This is the ONLY formatting syntax supported:

**Available Formatting:**
- Bold: `*text*` - Wrap text with single asterisks
- Italic: `_text_` - Wrap text with single underscores
- Backticks: `` `text` `` - Wrap text with single backticks (for code/IDs)

**Critical Rules:**
- MarkdownV1 is more forgiving than MarkdownV2 - special characters don't need escaping
- Never use `**text**` (double asterisks) - use `*text*` (single asterisks)
- Never use `__text__` (double underscores) - use `_text_` (single underscores)
- Keep formatting simple and consistent across all languages

### Strategic Formatting Patterns

Apply bold/italic formatting consistently to emphasize key information and create visual hierarchy:

#### BOLD (`*text*`) - Use for Critical Info:
1. **Numbers & Quantities:**
   - Credit amounts: `*10 credits*`, `*30 credits*`
   - Percentages & discounts: `*50% OFF*`, `*5折*`, `*30%*`
   - Prices: `*¥87*`, `*¥173*`
   - Usage counts: `*{current_usage}/{limit}*`, `*50*`, `*100 rounds*`
   - Time values: `*2 days*`, `*3 minutes*`, `*5 minutes*`, `*24:00*`, `*midnight*`

2. **VIP & Tiers:**
   - VIP levels: `*Lifetime VIP*`, `*Black Gold VIP*`, `*VIP*`
   - Discount tiers: `*SSR Divine Discount*`, `*{tier}*`
   - Queue labels: `*Image Processing*`, `*Video Processing*`

3. **Status & Actions:**
   - Status terms: `*FREE*`, `*free trial*`, `*unlimited*`, `*auto-cancel*`
   - CTAs (Call-to-Actions): `*grab it fast*`, `*don't miss it*`, `*use it now*`, `*ASAP*`
   - Warnings: `*Important: ...*`, `*NO daily limit*`, `*instant access*`, `*anytime*`
   - Actions: `*right after*`, `*automatically*`, `*priority processing*`

4. **Positions & Headers:**
   - Queue positions: `*#{position}*`, `*{total}*`
   - Section headers: `*Current Queue Status*`, `*Tip*`
   - Error titles: `*Unsupported Format*`, `*Upload Failed*`

#### ITALIC (`_text_`) - Use for Supplementary Info:
1. **Tips & Hints:**
   - Pro tips: `_Tip: Keep using to level up your discount_`
   - Helpful reminders: `_Valid till 24:00 today, don't miss out!_`
   - Instructions: `_If Alipay shows "Restricted Payment", just restart..._`

2. **Time-Sensitive CTAs:**
   - Final encouragement: `_Pick your package now and enjoy god-tier discount!_`
   - Urgency reminders: `_Limited time offer, top up now!_`
   - Soft CTAs: `_Click below to spin your lucky discount NOW!_`

#### BACKTICKS (`` `text` ``) - Use for Technical Info:
- Order IDs: `` `{payment_id}` ``
- Technical identifiers and codes

### Language-Specific Considerations

**Chinese (zh_CN, zh_TW):**
- Bold discount terms: `*5折*` (not "50% OFF")
- Bold key numbers: `*10积分*`, `*30积分*`
- Maintain casual/playful tone with bold emphasis on benefits

**English (en_US):**
- Bold all "XX% OFF" patterns
- Use bold for urgency: `*grab it fast*`, `*don't miss it*`
- Keep casual gaming/gambling vibe

**Korean (ko_KR):**
- Bold "XX% OFF" in English when used (e.g., `*50% OFF*`)
- Bold action words and credits consistently
- Preserve energetic K-pop style tone

**Hindi (hi_IN):**
- Uses Hinglish (Hindi + English mix)
- Bold English terms: `*free trial*`, `*instant access*`, `*50% OFF EVERYTHING*`
- Bold Hindi numbers: `*50%*`
- Keep super casual vibe

**Arabic (ar_SA):**
- RTL language - formatting still works the same
- Bold English phrases when used: `*50% OFF EVERYTHING*`, `*Lifetime VIP*`
- Bold Arabic percentages: `*50%*`, `*30%*`

**Key Principles:**
1. **Consistency First:** Same type of information should always be formatted the same way across all languages
2. **Preserve Tone:** Match the energy and personality from zh_CN source when translating
3. **Visual Hierarchy:** Bold creates scanning patterns - use it to guide user's eye to critical info
4. **Don't Overdo It:** If everything is bold, nothing stands out
5. **Test Both Ways:** Content should be readable with AND without the formatting

### Quick Reference: What to Bold

✅ **ALWAYS BOLD:**
- All numbers (credits, prices, percentages, times, counts)
- All "XX% OFF" or discount percentages
- VIP tiers and status
- CTAs and action words
- "FREE", "unlimited", "instant"
- Time limits and deadlines
- Queue positions and counts

❌ **NEVER BOLD:**
- Entire paragraphs or long sentences
- Regular descriptive text
- Connecting words (and, or, the, etc.)
- Emojis (they're already visually distinctive)

### Formatting Workflow

**When adding/editing translations:**
1. Write the base translation in the target language first
2. Apply strategic bold/italic based on patterns above
3. Cross-check with zh_CN formatting for consistency
4. Verify readability - content should make sense even if formatting is stripped
5. Test in Telegram to ensure MarkdownV1 renders correctly

## Important Notes
- Telegram Stars has higher commission (35%) vs Alipay/WeChat (8%)
- All credits are permanent (never expire)
- Daily limits only apply to free tier "Pink Lace" style
- Payment gateway may be in maintenance - show appropriate warnings
- Queue system gives priority to VIP users
