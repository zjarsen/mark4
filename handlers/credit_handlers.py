"""Handlers for credit-related operations."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# Injected dependencies
credit_service = None
payment_service = None
timeout_service = None
discount_service = None
translation_service = None


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
        if translation_service:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "查询余额失败，请稍后重试"
        await update.message.reply_text(msg)


async def show_topup_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top-up package options (including VIP packages and lucky discount)."""
    try:
        user_id = update.effective_user.id

        from core.constants import (
            TOPUP_PACKAGES_MESSAGE_WITH_DISCOUNT,
            TOPUP_PACKAGES_MESSAGE_NORMAL,
            TOPUP_PACKAGES_MESSAGE_NO_DISCOUNT,
            TOPUP_PACKAGES,
            LUCKY_DISCOUNT_BUTTON_HOT,
            LUCKY_DISCOUNT_BUTTON_NORMAL,
            LUCKY_DISCOUNT_BUTTON_REVEALED,
            DISCOUNT_TIERS
        )

        # Check if user has active discount today
        discount_info = await discount_service.get_current_discount(user_id)

        # Peek at discount tier to determine message variant
        tier = await discount_service.peek_discount_tier(user_id)

        # Select appropriate message variant and button text based on tier
        if discount_info:
            # Get translated tier name
            tier_name = translation_service.get(user_id, f'discount.tier_{tier.lower()}') if translation_service else DISCOUNT_TIERS[tier]['display']

            # Discount already revealed - use appropriate message based on tier
            if tier in ['SSR', 'SR']:
                message_text = translation_service.get(user_id, 'topup.packages_with_discount') if translation_service else TOPUP_PACKAGES_MESSAGE_WITH_DISCOUNT
                lucky_button_text = translation_service.get(user_id, 'discount.button_revealed',
                    emoji=DISCOUNT_TIERS[tier]['emoji'],
                    tier=tier_name,
                    off=DISCOUNT_TIERS[tier]['off']
                ) if translation_service else LUCKY_DISCOUNT_BUTTON_REVEALED.format(
                    emoji=DISCOUNT_TIERS[tier]['emoji'],
                    tier=tier_name,
                    off=DISCOUNT_TIERS[tier]['off']
                )
            else:  # R or C
                message_text = translation_service.get(user_id, 'topup.packages_normal') if translation_service else TOPUP_PACKAGES_MESSAGE_NORMAL
                lucky_button_text = translation_service.get(user_id, 'discount.button_revealed',
                    emoji=DISCOUNT_TIERS[tier]['emoji'],
                    tier=tier_name,
                    off=DISCOUNT_TIERS[tier]['off']
                ) if translation_service else LUCKY_DISCOUNT_BUTTON_REVEALED.format(
                    emoji=DISCOUNT_TIERS[tier]['emoji'],
                    tier=tier_name,
                    off=DISCOUNT_TIERS[tier]['off']
                )
        else:
            # Not revealed yet - select message based on future tier
            if tier in ['SSR', 'SR']:
                message_text = translation_service.get(user_id, 'topup.packages_with_discount') if translation_service else TOPUP_PACKAGES_MESSAGE_WITH_DISCOUNT
                lucky_button_text = translation_service.get(user_id, 'discount.button_hot') if translation_service else LUCKY_DISCOUNT_BUTTON_HOT
            elif tier in ['R', 'C']:
                message_text = translation_service.get(user_id, 'topup.packages_normal') if translation_service else TOPUP_PACKAGES_MESSAGE_NORMAL
                lucky_button_text = translation_service.get(user_id, 'discount.button_normal') if translation_service else LUCKY_DISCOUNT_BUTTON_NORMAL
            else:
                message_text = translation_service.get(user_id, 'topup.packages_no_discount') if translation_service else TOPUP_PACKAGES_MESSAGE_NO_DISCOUNT
                lucky_button_text = translation_service.get(user_id, 'discount.button_normal') if translation_service else LUCKY_DISCOUNT_BUTTON_NORMAL

        # Build keyboard with discount-aware buttons
        keyboard = []

        # Add lucky discount button at the top
        keyboard.append([InlineKeyboardButton(lucky_button_text, callback_data="lucky_discount")])

        # Add package buttons with discount if applicable
        packages = [
            (10, "topup_10"),
            (30, "topup_30"),
            (50, "topup_50"),
            (100, "topup_100"),
            (160, "topup_160"),
            (260, "topup_260")
        ]

        for base_price, callback_data in packages:
            credits = TOPUP_PACKAGES[base_price]

            # Calculate displayed price (with 8% fee)
            displayed_price = int(base_price * 1.08)

            # Apply discount if active (exclude ¥10 package from discounts)
            if discount_info and base_price != 10:
                discount_rate = discount_info['rate']
                original_price = displayed_price
                discounted_price = discount_service.apply_discount_to_price(base_price, discount_rate)

                # Calculate savings
                savings = original_price - discounted_price

                # Format button text with emoji-based design
                if base_price in [160, 260]:
                    # VIP packages (keeping simple - these are shown with discount info inline)
                    button_text = translation_service.get(user_id, 'topup.button_vip' if base_price == 160 else 'topup.button_black_gold_vip') if translation_service else (f"¥{displayed_price} = 永久VIP" if base_price == 160 else f"¥{displayed_price} = 永久黑金VIP")
                else:
                    # Credit packages (keeping numbers/prices visible)
                    button_text = f"¥{discounted_price} = {credits}" + (" credits" if translation_service and translation_service.db.get_user_language(user_id) == 'en_US' else " 积分")
            else:
                # No discount
                if base_price in [160, 260]:
                    button_text = translation_service.get(user_id, 'topup.button_vip' if base_price == 160 else 'topup.button_black_gold_vip') if translation_service else (f"¥{displayed_price} = 永久VIP" if base_price == 160 else f"¥{displayed_price} = 永久黑金VIP")
                else:
                    button_text = f"¥{displayed_price} = {credits}" + (" credits" if translation_service and translation_service.db.get_user_language(user_id) == 'en_US' else " 积分")

            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        logger.info(f"User {user_id} viewing top-up packages (discount active: {discount_info is not None}, tier: {tier})")

    except Exception as e:
        logger.error(f"Error showing top-up packages: {str(e)}")
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "显示充值套餐失败，请稍后重试"
        await update.message.reply_text(msg)


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
        if translation_service:
            message = translation_service.get(user_id, 'transactions.header')
        else:
            message = TRANSACTION_HISTORY_HEADER

        for tx in transactions:
            date = tx['created_at'][:10]  # Extract date
            # Transaction type translation (keeping simple for now - these could be moved to translation file later)
            tx_type = {
                'topup': '充值',
                'deduction': '消费',
                'refund': '退款'
            }.get(tx['transaction_type'], tx['transaction_type'])

            if translation_service:
                message += translation_service.get(
                    user_id,
                    'transactions.item_template',
                    date=date,
                    type=tx_type,
                    amount=tx['amount'],
                    balance=tx['balance_after']
                )
            else:
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
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "查询记录失败，请稍后重试"
        await update.message.reply_text(msg)


async def show_balance_and_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's balance and transaction history combined (VIP-aware)."""
    try:
        user_id = update.effective_user.id

        # Get VIP status
        is_vip, tier = await credit_service.is_vip_user(user_id)

        # Get user stats
        balance = await credit_service.get_balance(user_id)
        total_spent = await credit_service.get_total_spent(user_id)

        # Get transactions
        transactions = await credit_service.get_transaction_history(user_id, limit=10)

        from core.constants import (
            TRANSACTION_ITEM_TEMPLATE,
            VIP_STATUS_BADGE,
            BALANCE_MESSAGE_VIP
        )

        # Build VIP or regular message
        if is_vip:
            # VIP balance message
            tier_display = credit_service._tier_display_name(tier)
            if translation_service:
                vip_badge = translation_service.get(user_id, 'vip.status_badge', tier=tier_display)
                message = translation_service.get(user_id, 'vip.balance_message',
                    vip_badge=vip_badge,
                    balance=int(balance),
                    total_spent=int(total_spent)
                )
            else:
                vip_badge = VIP_STATUS_BADGE.format(tier=tier_display)
                message = BALANCE_MESSAGE_VIP.format(
                    vip_badge=vip_badge,
                    balance=int(balance),
                    total_spent=int(total_spent)
                )
        else:
            # Regular balance message
            if translation_service:
                message = translation_service.get(user_id, 'credits.balance_message',
                    balance=int(balance),
                    total_spent=int(total_spent)
                )
            else:
                message = f"""📊 积分余额 & 充值记录

💰 当前积分：{int(balance)} 积分
📈 累计消费：{int(total_spent)} 积分

图片脱衣：10 积分/次"""

        # Add transaction history section
        if translation_service:
            history_header = translation_service.get(user_id, 'transactions.recent_header', default="\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n📝 Recent 10 Transactions:\n\n")
        else:
            history_header = "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n📝 最近10笔记录：\n\n"
        message += history_header

        if not transactions:
            if translation_service:
                message += translation_service.get(user_id, 'transactions.no_transactions')
            else:
                message += "暂无消费记录"
        else:
            # Format transactions
            for tx in transactions:
                date = tx['created_at'][:10]  # Extract date
                # Get translated transaction type
                if translation_service:
                    tx_type = {
                        'topup': translation_service.get(user_id, 'transactions.type_topup', default='Topup'),
                        'deduction': translation_service.get(user_id, 'transactions.type_deduction', default='Usage'),
                        'refund': translation_service.get(user_id, 'transactions.type_refund', default='Refund')
                    }.get(tx['transaction_type'], tx['transaction_type'])
                else:
                    tx_type = {
                        'topup': '充值',
                        'deduction': '消费',
                        'refund': '退款'
                    }.get(tx['transaction_type'], tx['transaction_type'])

                if translation_service:
                    message += translation_service.get(user_id, 'transactions.item_template',
                        date=date,
                        type=tx_type,
                        amount=tx['amount'],
                        balance=tx['balance_after']
                    )
                else:
                    message += TRANSACTION_ITEM_TEMPLATE.format(
                        date=date,
                        type=tx_type,
                        amount=tx['amount'],
                        balance=tx['balance_after']
                    )

        await update.message.reply_text(message)
        logger.info(f"User {user_id} viewed balance and history (VIP: {is_vip})")

    except Exception as e:
        logger.error(f"Error showing balance and history: {str(e)}")
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "查询失败，请稍后重试"
        await update.message.reply_text(msg)


async def handle_payment_timeout(user_id: int, chat_id: int, message_id: int, payment_id: str, amount_cny: int):
    """
    Handle payment timeout after 3 minutes.

    Called by timeout service when payment timeout expires.
    Edits the pending payment message to show timeout and sends new top-up menu.

    Args:
        user_id: Telegram user ID
        chat_id: Chat ID where payment message is
        message_id: Message ID of the payment pending message
        payment_id: Payment ID that timed out
        amount_cny: Payment amount in CNY
    """
    try:
        # Check if payment has already been completed
        payment = payment_service.db.get_payment(payment_id)
        if payment and payment['status'] != 'pending':
            # Payment already completed or cancelled, don't send timeout menu
            logger.info(f"Payment {payment_id} already {payment['status']}, skipping timeout menu")
            return

        from core.constants import PAYMENT_TIMEOUT_MESSAGE

        # Get bot instance from timeout_service
        bot = timeout_service.bot

        # Edit the payment pending message to show timeout
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=PAYMENT_TIMEOUT_MESSAGE
            )
        except Exception as e:
            logger.warning(f"Failed to edit timeout message {message_id}: {str(e)}")

        # Store timeout message ID for cleanup
        timeout_service.add_timeout_messages(user_id, message_id)

        logger.info(f"Payment timeout displayed for user {user_id}, payment {payment_id}")

    except Exception as e:
        logger.error(f"Error handling payment timeout for user {user_id}: {str(e)}", exc_info=True)


async def handle_lucky_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lucky discount button click."""
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        from core.constants import (
            LUCKY_DISCOUNT_CELEBRATION_SSR,
            LUCKY_DISCOUNT_CELEBRATION_SR,
            LUCKY_DISCOUNT_REVEALED_R,
            LUCKY_DISCOUNT_REVEALED_C,
            LUCKY_DISCOUNT_ALREADY_REVEALED,
            DISCOUNT_TIERS,
            TOPUP_PACKAGES,
            TOPUP_PACKAGES_MESSAGE,
            LUCKY_DISCOUNT_BUTTON_REVEALED
        )

        # Get or reveal daily discount
        discount_info = await discount_service.get_or_reveal_daily_discount(user_id)

        if not discount_info:
            if translation_service:
                msg = translation_service.get(user_id, 'errors.system')
            else:
                msg = "获取折扣信息失败，请稍后再试"
            await query.answer(msg, show_alert=True)
            return

        tier = discount_info['tier']
        is_new = discount_info['is_new']

        # Show celebration message for new SSR/SR, or simple message for R/C
        if is_new:
            if tier == 'SSR':
                msg = translation_service.get(user_id, 'discount.celebration_ssr') if translation_service else LUCKY_DISCOUNT_CELEBRATION_SSR
                logger.info(f"User {user_id} got SSR discount, translation_service={'exists' if translation_service else 'None'}, msg preview: {msg[:50]}")
                await query.answer(msg, show_alert=True)
            elif tier == 'SR':
                msg = translation_service.get(user_id, 'discount.celebration_sr') if translation_service else LUCKY_DISCOUNT_CELEBRATION_SR
                logger.info(f"User {user_id} got SR discount, translation_service={'exists' if translation_service else 'None'}, msg preview: {msg[:50]}")
                await query.answer(msg, show_alert=True)
            elif tier == 'R':
                msg = translation_service.get(user_id, 'discount.revealed_r') if translation_service else LUCKY_DISCOUNT_REVEALED_R
                logger.info(f"User {user_id} got R discount, translation_service={'exists' if translation_service else 'None'}, msg preview: {msg[:50]}")
                await query.answer(msg, show_alert=True)
            else:  # C
                msg = translation_service.get(user_id, 'discount.revealed_c') if translation_service else LUCKY_DISCOUNT_REVEALED_C
                logger.info(f"User {user_id} got C discount, translation_service={'exists' if translation_service else 'None'}, msg preview: {msg[:50]}")
                await query.answer(msg, show_alert=True)
        else:
            # Already revealed today
            tier_data = DISCOUNT_TIERS[tier]
            # Get translated tier name
            tier_name = translation_service.get(user_id, f'discount.tier_{tier.lower()}') if translation_service else tier_data['display']
            if translation_service:
                message = translation_service.get(user_id, 'discount.already_revealed',
                    tier=tier_name,
                    off=tier_data['off']
                )
            else:
                message = LUCKY_DISCOUNT_ALREADY_REVEALED.format(
                    tier=tier_name,
                    off=tier_data['off']
                )
            logger.info(f"User {user_id} discount already revealed (tier={tier}), translation_service={'exists' if translation_service else 'None'}, msg preview: {message[:50]}")
            await query.answer(message, show_alert=True)

        # Update keyboard with discount-aware prices
        keyboard = []

        # Update lucky discount button to show tier
        tier_data = DISCOUNT_TIERS[tier]
        # Get translated tier name
        tier_name = translation_service.get(user_id, f'discount.tier_{tier.lower()}') if translation_service else tier_data['display']
        if translation_service:
            button_text = translation_service.get(user_id, 'discount.button_revealed',
                emoji=tier_data['emoji'],
                tier=tier_name,
                off=tier_data['off']
            )
        else:
            button_text = LUCKY_DISCOUNT_BUTTON_REVEALED.format(
                emoji=tier_data['emoji'],
                tier=tier_name,
                off=tier_data['off']
            )
        keyboard.append([InlineKeyboardButton(button_text, callback_data="lucky_discount")])

        # Add package buttons with discounted prices
        packages = [
            (10, "topup_10"),
            (30, "topup_30"),
            (50, "topup_50"),
            (100, "topup_100"),
            (160, "topup_160"),
            (260, "topup_260")
        ]

        discount_rate = discount_info['rate']

        for base_price, callback_data in packages:
            credits = TOPUP_PACKAGES[base_price]

            # Calculate prices
            original_price = int(base_price * 1.08)

            # Exclude ¥10 package from discounts
            if base_price == 10:
                # Show regular price for ¥10 (no discount) with i18n and consistent emoji format
                if translation_service:
                    button_text = translation_service.get(user_id, 'topup.button_10_no_discount', credits=credits, price=original_price)
                else:
                    button_text = f"💰 {credits}积分 ¥{original_price} (无折扣)"
            else:
                # Apply discount for other packages
                discounted_price = discount_service.apply_discount_to_price(base_price, discount_rate)

                # Calculate savings
                savings = original_price - discounted_price

                # Format button text with emoji-based design
                if base_price in [160, 260]:
                    # VIP packages with i18n
                    if translation_service:
                        button_text = translation_service.get(
                            user_id,
                            'topup.button_vip_with_discount' if base_price == 160 else 'topup.button_black_gold_vip_with_discount',
                            discounted_price=discounted_price,
                            original_price=original_price
                        )
                    else:
                        vip_name = "永久VIP" if base_price == 160 else "永久黑金VIP"
                        emoji = "💎" if base_price == 160 else "👑"
                        button_text = f"{emoji} {vip_name} ¥{discounted_price} 🎁（原价¥{original_price}）"
                else:
                    # Credit packages with i18n
                    if translation_service:
                        button_text = translation_service.get(
                            user_id,
                            'topup.button_credits_with_discount',
                            credits=credits,
                            discounted_price=discounted_price,
                            original_price=original_price
                        )
                    else:
                        button_text = f"💰 {credits}积分 ¥{discounted_price} 🎁（原价¥{original_price}）"

            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Update message with new prices (Markdown formatting for button text)
        await query.edit_message_text(
            query.message.text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        logger.info(f"User {user_id} revealed discount: {tier} ({discount_info['rate']})")

    except Exception as e:
        logger.error(f"Error handling lucky discount: {str(e)}")
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "操作失败，请稍后再试"
        await query.answer(msg, show_alert=True)


async def handle_topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle top-up package selection (two-step process).

    Step 1: User selects amount (callback_data: "topup_10", "topup_30", etc.)
            → Show payment method selection
    Step 2: User selects payment method (callback_data: "topup_10_alipay", "topup_10_wechat")
            → Create payment
    """
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        callback_data = query.data

        # Check if this is Step 2 (payment method selected) or Step 1 (amount selected)
        if callback_data.endswith('_alipay') or callback_data.endswith('_wechat'):
            # ===== STEP 2: Payment method selected, create payment =====
            # Extract amount and payment method (e.g., "topup_10_alipay" -> amount=10, method="alipay")
            parts = callback_data.replace("topup_", "").rsplit("_", 1)
            base_amount_cny = int(parts[0])  # Base price before discount
            payment_method = parts[1]  # 'alipay' or 'wechat'

            # Check if user has active discount and apply it (exclude ¥10 package)
            discount_info = await discount_service.get_current_discount(user_id)
            if discount_info and base_amount_cny != 10:
                # Apply discount to get the actual amount to charge
                discount_rate = discount_info['rate']
                # Calculate: base * discount_rate (this gives the discounted base before 8% fee)
                # The payment provider will add 8% fee on top
                amount_cny = int(base_amount_cny * discount_rate)
                logger.info(f"Applying {discount_info['tier']} discount to payment: ¥{base_amount_cny} → ¥{amount_cny}")
            else:
                amount_cny = base_amount_cny

            # Get chat_id and message_id for later editing
            chat_id = query.message.chat_id
            message_id = query.message.message_id

            # Check if this is a VIP purchase (based on base amount)
            is_vip_purchase = base_amount_cny in [160, 260]
            vip_tier = None

            if is_vip_purchase:
                # Determine VIP tier (based on base amount)
                vip_tier = 'vip' if base_amount_cny == 160 else 'black_gold'

                # Check if redundant purchase
                current_tier = credit_service.db.get_vip_tier(user_id)

                if current_tier == vip_tier:
                    tier_name = credit_service._tier_display_name(vip_tier)
                    if translation_service:
                        msg = translation_service.get(user_id, 'payment.vip_already_owned', tier=tier_name)
                    else:
                        msg = f"您已经是{tier_name}了，无需重复购买！"
                    await query.edit_message_text(msg)
                    return

            # Get user's language for payment record
            user_language = database_service.get_user_language(user_id) if database_service else 'zh_CN'

            # Create payment
            success, payment_info, error = await payment_service.create_topup_payment(
                user_id,
                amount_cny,
                payment_method,
                chat_id=chat_id,
                message_id=message_id,
                language_code=user_language
            )

            if not success:
                if translation_service:
                    msg = translation_service.get(user_id, 'payment.creation_error', error=str(error))
                else:
                    msg = f"创建支付失败: {error}"
                await query.edit_message_text(msg)
                return

            # If VIP purchase, store VIP tier in payment metadata
            if is_vip_purchase and vip_tier:
                conn = payment_service.db._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE payments
                    SET metadata = ?
                    WHERE payment_id = ?
                """, (f"vip_tier:{vip_tier}", payment_info['payment_id']))
                conn.commit()
                logger.info(
                    f"Stored VIP tier metadata for payment {payment_info['payment_id']}: {vip_tier}"
                )

            # Calculate displayed amount (with 8% transaction fee)
            displayed_amount = int(payment_info['amount_cny'] * 1.08)

            # Get translated payment pending message
            if translation_service:
                message = translation_service.get(
                    user_id,
                    'payment.pending',
                    payment_id=payment_info['payment_id'],
                    amount=displayed_amount,
                    credits=int(payment_info['credits_amount'])
                )
                # Get payment method display name
                method_key = 'payment.button_alipay' if payment_method == 'alipay' else 'payment.button_wechat'
                method_name = translation_service.get(user_id, method_key)
                method_line = translation_service.get(user_id, 'payment.method_label', method=method_name)
                message += method_line

                button_text = translation_service.get(user_id, 'payment.button_go_pay')
            else:
                from core.constants import PAYMENT_PENDING_MESSAGE
                message = PAYMENT_PENDING_MESSAGE.format(
                    payment_id=payment_info['payment_id'],
                    amount=displayed_amount,
                    credits=payment_info['credits_amount']
                )
                payment_method_cn = "支付宝" if payment_method == "alipay" else "微信支付"
                message += f"\n支付方式：{payment_method_cn}"
                button_text = "前往支付"

            # Add payment URL button
            keyboard = [[
                InlineKeyboardButton(
                    button_text,
                    url=payment_info['payment_url']
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Try to edit message, if fails (e.g., deleted by cleanup), send new message
            try:
                await query.edit_message_text(message, reply_markup=reply_markup)
            except Exception as edit_error:
                # Message was deleted (likely by cleanup middleware), send new message
                logger.debug(f"Could not edit message, sending new message: {str(edit_error)}")
                # Update message_id to the new message for timeout tracking
                sent_msg = await query.message.reply_text(message, reply_markup=reply_markup)
                message_id = sent_msg.message_id

            logger.info(
                f"Created payment {payment_info['payment_id']} for user {user_id}: "
                f"¥{amount_cny} = {payment_info['credits_amount']} credits via {payment_method}"
            )

            # Start payment timeout timer (3 minutes)
            if timeout_service:
                from core.constants import PAYMENT_TIMEOUT_SECONDS
                timeout_service.start_payment_timeout(
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    payment_id=payment_info['payment_id'],
                    amount_cny=amount_cny,
                    timeout_callback=handle_payment_timeout,
                    delay_seconds=PAYMENT_TIMEOUT_SECONDS
                )
                logger.debug(f"Started {PAYMENT_TIMEOUT_SECONDS}s timeout timer for payment {payment_info['payment_id']}")

        else:
            # ===== STEP 1: Amount selected, show payment method options =====
            # Extract amount (e.g., "topup_10" -> 10)
            amount_str = callback_data.replace("topup_", "")
            amount_cny = int(amount_str)

            # Get credits for this amount
            from core.constants import TOPUP_PACKAGES
            credits = TOPUP_PACKAGES.get(amount_cny, 0)

            # Check if this is a VIP purchase
            is_vip = amount_cny in [160, 260]
            tier_name = ""
            if is_vip:
                tier = 'vip' if amount_cny == 160 else 'black_gold'
                tier_name = f" ({credit_service._tier_display_name(tier)})"

            # Check if user has active discount (exclude ¥10 package)
            discount_info = await discount_service.get_current_discount(user_id)
            if discount_info and amount_cny != 10:
                # Apply discount to displayed amount
                discount_rate = discount_info['rate']
                original_displayed_amount = int(amount_cny * 1.08)
                displayed_amount = discount_service.apply_discount_to_price(amount_cny, discount_rate)
                savings = original_displayed_amount - displayed_amount

                # Show payment method selection with discount reminder
                if translation_service:
                    message = translation_service.get(
                        user_id,
                        'payment.method_selection_with_discount',
                        displayed_amount=displayed_amount,
                        credits=credits,
                        tier_name=tier_name,
                        savings=savings
                    )
                else:
                    message = f"""💳 充值 ¥{displayed_amount} = {credits}积分{tier_name}

🔥 **折扣已应用** - 为您节省 ¥{savings}！
⏰ _今日24:00前有效，请尽快完成支付_

请选择支付方式："""
            else:
                # Calculate displayed amount (with 8% transaction fee)
                displayed_amount = int(amount_cny * 1.08)

                # Show payment method selection without discount
                if translation_service:
                    message = translation_service.get(
                        user_id,
                        'payment.method_selection_normal',
                        displayed_amount=displayed_amount,
                        credits=credits,
                        tier_name=tier_name
                    )
                else:
                    message = f"""💳 充值 ¥{displayed_amount} = {credits}积分{tier_name}

请选择支付方式："""

            # Get translated button text
            if translation_service:
                alipay_text = translation_service.get(user_id, 'payment.button_alipay')
                wechat_text = translation_service.get(user_id, 'payment.button_wechat')
            else:
                alipay_text = "💰 支付宝支付"
                wechat_text = "💚 微信支付"

            keyboard = [
                [InlineKeyboardButton(
                    alipay_text,
                    callback_data=f"topup_{amount_cny}_alipay"
                )],
                [InlineKeyboardButton(
                    wechat_text,
                    callback_data=f"topup_{amount_cny}_wechat"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Try to edit message, if fails (e.g., deleted by cleanup), send new message
            try:
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as edit_error:
                # Message was deleted (likely by cleanup middleware), send new message
                logger.debug(f"Could not edit message, sending new message: {str(edit_error)}")
                await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

            logger.info(f"User {user_id} selected amount ¥{amount_cny}, showing payment methods")

    except Exception as e:
        logger.error(f"Error handling top-up callback: {str(e)}")
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'payment.failed')
        else:
            msg = "创建支付失败，请稍后重试"
        try:
            await query.edit_message_text(msg)
        except:
            pass
