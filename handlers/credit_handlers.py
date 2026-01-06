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
pricing_service = None  # NEW: For payment method pricing calculations
database_service = None  # NEW: For user language lookup


async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance check request."""
    try:
        user_id = update.effective_user.id

        # Get user stats
        stats = await credit_service.get_user_stats(user_id)

        if translation_service:
            message = translation_service.get(
                user_id,
                'credits.balance',
                balance=stats['balance'],
                total_spent=stats['total_spent']
            )
        else:
            message = f"""💰 积分余额

当前积分：{stats['balance']} 积分
累计消费：{stats['total_spent']} 积分"""

        await update.message.reply_text(message)
        logger.info(f"User {user_id} checked balance: {stats['balance']}")

    except Exception as e:
        logger.error(f"Error checking balance for user {user_id}: {str(e)}")
        if translation_service:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "查询余额失败，请稍后重试"
        await update.message.reply_text(msg)


async def show_topup_packages(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False):
    """
    Show payment method selection with Lucky Discount button (NEW UX - Step 1).

    User flow:
    1. Click "立即抽取幸运折扣" → THIS FUNCTION
       - Shows Lucky Discount button at top (if not revealed)
       - OR shows discount info (if already revealed)
       - Shows 3 payment method buttons
    2. Click Lucky Discount → Reveals discount and updates this page
    3. Click payment method → show_pricing_for_method() (shows pricing menu)

    Args:
        is_callback: If True, edit existing message; if False, send new message
    """
    try:
        user_id = update.effective_user.id

        # Check if discount already revealed (don't auto-reveal)
        discount_info = await discount_service.get_current_discount(user_id)
        tier = await discount_service.peek_discount_tier(user_id)

        from core.constants import DISCOUNT_TIERS

        # Build message based on discount status
        if discount_info:
            # Discount already revealed - show discount info
            savings_percent = int((1 - discount_info['rate']) * 100)

            if translation_service:
                tier_name = translation_service.get(user_id, f"discount.tier_{discount_info['tier'].lower()}")
                message_text = translation_service.get(
                    user_id,
                    'topup.method_selection_with_discount',
                    tier=tier_name,
                    emoji=discount_info['emoji'],
                    off=discount_info['off'],
                    savings_percent=savings_percent
                )
            else:
                message_text = f"""🎰 *超级幸运日！* 🎰

🔥 您的专属折扣：{discount_info['display']} {discount_info['emoji']} - {discount_info['off']}折！
💰 *全场可省{savings_percent}%* - 所有支付方式通用
⏰ _今日24:00前有效，手慢无！_

━━━━━━━━━━━━━━━━━

💫 选择支付方式，立即享受折扣："""

        else:
            # Discount NOT revealed yet - show teaser message
            if translation_service:
                message_text = translation_service.get(user_id, 'topup.method_selection_no_discount')
            else:
                message_text = """💫 *选择您的支付方式*

支持以下支付方式：
⭐ Telegram Stars - 无手续费
💚 微信支付 - 快速到账
💰 支付宝 - 安全便捷

请选择您偏好的支付方式："""

        # Build keyboard
        keyboard = []

        # Lucky Discount button at top (ALWAYS SHOW)
        if discount_info:
            # Already revealed - show revealed button
            tier_name = translation_service.get(user_id, f'discount.tier_{tier.lower()}') if translation_service else DISCOUNT_TIERS[tier]['display']
            lucky_button_text = translation_service.get(
                user_id,
                'discount.button_revealed',
                emoji=DISCOUNT_TIERS[tier]['emoji'],
                tier=tier_name,
                off=DISCOUNT_TIERS[tier]['off']
            ) if translation_service else f"{DISCOUNT_TIERS[tier]['emoji']} {tier_name} ({DISCOUNT_TIERS[tier]['off']}折)"
        else:
            # Not revealed yet - show reveal button
            if tier in ['SSR', 'SR']:
                lucky_button_text = translation_service.get(user_id, 'discount.button_hot') if translation_service else "🔥💰 点我领取今日超级折扣！ 💰🔥"
            else:
                lucky_button_text = translation_service.get(user_id, 'discount.button_normal') if translation_service else "🎰 每日幸运折扣 - 点击查看"

        keyboard.append([InlineKeyboardButton(
            lucky_button_text,
            callback_data="reveal_discount_unified"
        )])

        # 3 payment method buttons
        stars_text = translation_service.get(user_id, 'topup.method_button_stars') if translation_service else "⭐ Telegram Stars"
        keyboard.append([InlineKeyboardButton(stars_text, callback_data="method_stars")])

        wechat_text = translation_service.get(user_id, 'payment.button_wechat') if translation_service else "💚 微信支付"
        keyboard.append([InlineKeyboardButton(wechat_text, callback_data="method_wechat")])

        alipay_text = translation_service.get(user_id, 'payment.button_alipay') if translation_service else "💰 支付宝支付"
        keyboard.append([InlineKeyboardButton(alipay_text, callback_data="method_alipay")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send or edit message based on context
        if is_callback:
            # Called from callback (e.g., back button) - edit existing message
            query = update.callback_query
            await query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Called from regular message - send new message
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        logger.info(f"User {user_id} viewing payment method selection (discount: {'revealed - ' + discount_info['tier'] if discount_info else 'not revealed'})")

    except Exception as e:
        logger.error(f"Error showing payment methods: {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.display_payment_methods_failed')
        else:
            msg = "显示支付方式失败，请稍后重试"

        if is_callback:
            query = update.callback_query
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)


async def show_pricing_for_method(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_method: str
):
    """
    Show pricing menu for selected payment method (NEW FLOW - Step 2).

    Args:
        payment_method: 'stars', 'alipay', or 'wechat'

    User flow:
    1. User selected payment method → THIS FUNCTION (shows Lucky Discount + 6 packages)
    2. Click package → create_payment_for_method() (creates payment)
    """
    try:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        from core.constants import TOPUP_PACKAGES

        # Get discount info (discount already revealed on method selection page)
        discount_info = await discount_service.get_current_discount(user_id)

        # Build simple intro message
        method_names = {
            'stars': '⭐ Telegram Stars',
            'wechat': '💚 微信支付',
            'alipay': '💰 支付宝'
        }
        method_name = method_names.get(payment_method, payment_method)

        if translation_service:
            message_text = translation_service.get(user_id, f'topup.packages_{payment_method}_intro')
        else:
            message_text = f"{method_name} 充值\n\n选择充值套餐："

        # Build keyboard
        keyboard = []

        # Package buttons with method-specific pricing (discount already revealed on method selection page)
        packages = [
            (10, TOPUP_PACKAGES[10]),
            (30, TOPUP_PACKAGES[30]),
            (50, TOPUP_PACKAGES[50]),
            (100, TOPUP_PACKAGES[100]),
            (160, TOPUP_PACKAGES[160]),
            (260, TOPUP_PACKAGES[260])
        ]

        for base_amount, credits in packages:
            # Calculate price using PricingService
            discount_rate = discount_info['rate'] if discount_info else 1.0
            price_info = pricing_service.calculate_price(
                base_amount,
                payment_method,
                discount_rate
            )

            # Format button text
            if discount_info and price_info['is_discount_eligible']:
                # Show discounted price
                if base_amount in [160, 260]:
                    # VIP packages with discount
                    if translation_service:
                        button_text = translation_service.get(
                            user_id,
                            'topup.button_vip_with_discount' if base_amount == 160 else 'topup.button_black_gold_vip_with_discount',
                            discounted_price=price_info['display'],
                            original_price=pricing_service.format_price_display(price_info['base_price'], payment_method)
                        )
                    else:
                        vip_name = "Lifetime VIP" if base_amount == 160 else "Black Gold VIP"
                        base_display = pricing_service.format_price_display(price_info['base_price'], payment_method)
                        button_text = f"💎 {vip_name} {price_info['display']} 🎁 (Was {base_display})"
                else:
                    # Credit packages with discount
                    if translation_service:
                        button_text = translation_service.get(
                            user_id,
                            'topup.button_credits_with_discount',
                            credits=credits,
                            discounted_price=price_info['display'],
                            original_price=pricing_service.format_price_display(price_info['base_price'], payment_method)
                        )
                    else:
                        base_display = pricing_service.format_price_display(price_info['base_price'], payment_method)
                        button_text = f"💰 {credits} credits {price_info['display']} 🎁 (Was {base_display})"
            else:
                # No discount or ineligible
                if base_amount in [160, 260]:
                    vip_name = "Lifetime VIP" if base_amount == 160 else "Black Gold VIP"
                    button_text = f"{price_info['display']} = {vip_name}"
                else:
                    button_text = f"{price_info['display']} = {credits} credits"

            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"topup_{payment_method}_{base_amount}"
            )])

        # Add back button to return to payment method selection
        if translation_service:
            back_button_text = translation_service.get(user_id, 'topup.button_back')
        else:
            back_button_text = "« 返回支付方式选择"

        keyboard.append([InlineKeyboardButton(back_button_text, callback_data="back_to_payment_methods")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as edit_error:
            # Handle "Message is not modified" error (happens when clicking discount after already revealed)
            if "message is not modified" in str(edit_error).lower():
                logger.debug(f"Message already shows current pricing for {payment_method}, no update needed")
                # Don't need to answer query - it was already answered by the caller
                pass
            else:
                # Re-raise other errors
                raise

        logger.info(f"User {user_id} viewing {payment_method} pricing menu (discount: {discount_info is not None})")

    except Exception as e:
        logger.error(f"Error showing pricing for {payment_method}: {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.display_pricing_failed')
        else:
            msg = "显示价格失败，请稍后重试"
        try:
            await query.edit_message_text(msg)
        except:
            pass


async def create_payment_for_method(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_method: str,
    base_amount_cny: int
):
    """
    Create payment for selected method and amount (NEW FLOW - Step 3).

    Args:
        update: Telegram update object
        context: Bot context
        payment_method: Payment method ('stars', 'alipay', 'wechat')
        base_amount_cny: Base CNY amount (10, 30, 50, 100, 160, 260)
    """
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        chat_id = query.message.chat_id
        message_id = query.message.message_id

        # Get discount info
        discount_info = await discount_service.get_current_discount(user_id)
        discount_rate = discount_info['rate'] if discount_info else 1.0

        # Calculate price using PricingService
        price_info = pricing_service.calculate_price(base_amount_cny, payment_method, discount_rate)

        # Get credits for this package
        from core.constants import TOPUP_PACKAGES
        credits = TOPUP_PACKAGES.get(base_amount_cny, 0)

        # Check if this is a VIP purchase
        is_vip_purchase = base_amount_cny in [160, 260]
        vip_tier = None

        if is_vip_purchase:
            # Determine VIP tier
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

        # Route to appropriate payment service based on method
        if payment_method == 'stars':
            # Telegram Stars payment
            success, payment_info, error = await payment_service.create_topup_payment_stars(
                user_id=user_id,
                amount_stars=price_info['final_price'],
                base_amount_cny=base_amount_cny,
                credits_amount=credits,
                chat_id=chat_id,
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
                logger.info(f"Stored VIP tier metadata for Stars payment {payment_info['payment_id']}: {vip_tier}")

            # For Stars, the invoice is sent as a separate message by Telegram
            # We don't need to edit the pricing menu message - just acknowledge the callback
            if translation_service:
                answer_msg = translation_service.get(user_id, 'payment.stars_invoice_sent')
            else:
                answer_msg = "✨ 已发送支付请求，请在弹出窗口中完成支付"
            await query.answer(answer_msg, show_alert=False)

            logger.info(
                f"Created Stars payment {payment_info['payment_id']} for user {user_id}: "
                f"{price_info['final_price']} Stars (base ¥{base_amount_cny}) = {credits} credits"
            )

        else:
            # WeChat/Alipay payment (existing CNY flow)
            amount_cny = base_amount_cny if discount_rate == 1.0 else int(base_amount_cny * discount_rate)

            success, payment_info, error = await payment_service.create_topup_payment(
                user_id=user_id,
                amount_cny=amount_cny,
                payment_method=payment_method,
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
                logger.info(f"Stored VIP tier metadata for payment {payment_info['payment_id']}: {vip_tier}")

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
                message = f"""💳 等待支付

订单号：{payment_info['payment_id']}
金额：¥{displayed_amount}
积分：{payment_info['credits_amount']}
"""
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

            # Try to edit message, if fails, send new message
            try:
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as edit_error:
                logger.debug(f"Could not edit message, sending new: {str(edit_error)}")
                sent_msg = await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                message_id = sent_msg.message_id

            logger.info(
                f"Created payment {payment_info['payment_id']} for user {user_id}: "
                f"¥{amount_cny} = {payment_info['credits_amount']} credits via {payment_method}"
            )

            # Start payment timeout timer (3 minutes) - CNY only
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

    except Exception as e:
        logger.error(f"Error creating payment for {payment_method}: {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'payment.failed')
        else:
            msg = "创建支付失败，请稍后重试"
        try:
            await query.edit_message_text(msg)
        except:
            pass


async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's transaction history."""
    try:
        user_id = update.effective_user.id

        # Get transactions
        transactions = await credit_service.get_transaction_history(user_id, limit=10)

        if not transactions:
            if translation_service:
                no_tx_msg = translation_service.get(user_id, 'transactions.no_transactions')
            else:
                no_tx_msg = "暂无消费记录"
            await update.message.reply_text(no_tx_msg)
            return

        # Format transactions
        if translation_service:
            message = translation_service.get(user_id, 'transactions.header')
        else:
            message = "📝 交易记录\n\n"

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
                message += f"{date} | {tx_type} | {tx['amount']:+d} 积分 | 余额: {tx['balance_after']} 积分\n"

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
                vip_badge = f"👑 {tier_display}"
                message = f"""{vip_badge}

💰 当前积分：{int(balance)} 积分
📈 累计消费：{int(total_spent)} 积分

图片脱衣：VIP 免费
视频脱衣：VIP 免费"""
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
            history_header = translation_service.get(user_id, 'transactions.recent_header', default="\n\n━━━━━━━━━━━━━━━━━━━\n\n📝 Recent 10 Transactions:\n\n")
        else:
            history_header = "\n\n━━━━━━━━━━━━━━━━━━━\n\n📝 最近10笔记录：\n\n"
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
                    message += f"{date} | {tx_type} | {tx['amount']:+d} 积分 | 余额: {tx['balance_after']} 积分\n"

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

        # Get bot instance from timeout_service
        bot = timeout_service.bot

        # Get timeout message
        if translation_service:
            timeout_msg = translation_service.get(user_id, 'payment.timeout')
        else:
            timeout_msg = """⏰ 支付超时

订单已取消，请重新发起充值。"""

        # Edit the payment pending message to show timeout
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=timeout_msg
            )
        except Exception as e:
            logger.warning(f"Failed to edit timeout message {message_id}: {str(e)}")

        # Store timeout message ID for cleanup
        timeout_service.add_timeout_messages(user_id, message_id)

        logger.info(f"Payment timeout displayed for user {user_id}, payment {payment_id}")

    except Exception as e:
        logger.error(f"Error handling payment timeout for user {user_id}: {str(e)}", exc_info=True)


async def handle_lucky_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle lucky discount button click on payment method selection page.

    Handles two callback patterns:
    1. "reveal_discount_unified" - New unified reveal button on method selection page
    2. "lucky_discount_*" - Old per-method buttons (deprecated, for backward compat)
    """
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        callback_data = query.data

        from core.constants import DISCOUNT_TIERS

        # Handle unified reveal button
        if callback_data == "reveal_discount_unified":
            # Reveal discount
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

            # Show celebration if new reveal
            if is_new:
                # Show celebration message
                if translation_service:
                    tier_name = translation_service.get(user_id, f"discount.tier_{discount_info['tier'].lower()}")
                    celebration_msg = translation_service.get(
                        user_id,
                        'discount.celebration_inline',
                        tier=tier_name,
                        emoji=discount_info['emoji']
                    )
                else:
                    celebration_msg = f"🎉 恭喜！抽到{discount_info['display']}折扣 {discount_info['emoji']}"

                await query.answer(celebration_msg, show_alert=False)
                logger.info(f"User {user_id} revealed new discount: {tier} ({discount_info['rate']})")

            # Update the message with discount info
            savings_percent = int((1 - discount_info['rate']) * 100)

            if translation_service:
                tier_name = translation_service.get(user_id, f"discount.tier_{discount_info['tier'].lower()}")
                message_text = translation_service.get(
                    user_id,
                    'topup.method_selection_with_discount',
                    tier=tier_name,
                    emoji=discount_info['emoji'],
                    off=discount_info['off'],
                    savings_percent=savings_percent
                )
            else:
                message_text = f"""🎰 *超级幸运日！* 🎰

🔥 您的专属折扣：{discount_info['display']} {discount_info['emoji']} - {discount_info['off']}折！
💰 *全场可省{savings_percent}%* - 所有支付方式通用
⏰ _今日24:00前有效，手慢无！_

━━━━━━━━━━━━━━━━━

💫 选择支付方式，立即享受折扣："""

            # Build keyboard (KEEP Lucky Discount button)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = []

            # Add Lucky Discount button (revealed state)
            tier_name = translation_service.get(user_id, f'discount.tier_{tier.lower()}') if translation_service else DISCOUNT_TIERS[tier]['display']
            lucky_button_text = translation_service.get(
                user_id,
                'discount.button_revealed',
                emoji=DISCOUNT_TIERS[tier]['emoji'],
                tier=tier_name,
                off=DISCOUNT_TIERS[tier]['off']
            ) if translation_service else f"{DISCOUNT_TIERS[tier]['emoji']} {tier_name} ({DISCOUNT_TIERS[tier]['off']}折)"

            keyboard.append([InlineKeyboardButton(
                lucky_button_text,
                callback_data="reveal_discount_unified"
            )])

            # Add 3 payment method buttons
            stars_text = translation_service.get(user_id, 'topup.method_button_stars') if translation_service else "⭐ Telegram Stars"
            keyboard.append([InlineKeyboardButton(stars_text, callback_data="method_stars")])

            wechat_text = translation_service.get(user_id, 'payment.button_wechat') if translation_service else "💚 微信支付"
            keyboard.append([InlineKeyboardButton(wechat_text, callback_data="method_wechat")])

            alipay_text = translation_service.get(user_id, 'payment.button_alipay') if translation_service else "💰 支付宝支付"
            keyboard.append([InlineKeyboardButton(alipay_text, callback_data="method_alipay")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Update message
            try:
                await query.edit_message_text(
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as edit_error:
                if "message is not modified" in str(edit_error).lower():
                    pass  # Silently ignore
                else:
                    raise

            return

        # Handle old per-method buttons (deprecated)
        logger.warning(
            f"DEPRECATED: User {user_id} clicked old lucky_discount button (callback: {callback_data}). "
            "This button should not exist in new UX. Redirecting to payment method selection."
        )

        # Show toast notification
        if translation_service:
            toast_msg = translation_service.get(user_id, 'errors.deprecated_button')
        else:
            toast_msg = "请从主菜单重新进入充值页面"
        await query.answer(toast_msg, show_alert=False)

        # Redirect to payment method selection (which will show discount)
        discount_info = await discount_service.get_or_reveal_daily_discount(user_id)

        if discount_info:
            savings_percent = int((1 - discount_info['rate']) * 100)
            if translation_service:
                tier_name = translation_service.get(user_id, f"discount.tier_{discount_info['tier'].lower()}")
                message_text = translation_service.get(
                    user_id,
                    'topup.method_selection_with_discount',
                    tier=tier_name,
                    emoji=discount_info['emoji'],
                    off=discount_info['off'],
                    savings_percent=savings_percent
                )
            else:
                message_text = f"""🎰 *超级幸运日！* 🎰

🔥 您的专属折扣：{discount_info['display']} {discount_info['emoji']} - {discount_info['off']}折！
💰 *全场可省{savings_percent}%* - 所有支付方式通用
⏰ _今日24:00前有效，手慢无！_

━━━━━━━━━━━━━━━━━

💫 选择支付方式，立即享受折扣："""
        else:
            if translation_service:
                message_text = translation_service.get(user_id, 'topup.method_selection_no_discount')
            else:
                message_text = """💫 *选择您的支付方式*

支持以下支付方式：
⭐ Telegram Stars - 无手续费
💚 微信支付 - 快速到账
💰 支付宝 - 安全便捷

请选择您偏好的支付方式："""

        # Build 3 payment method buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = []
        stars_text = translation_service.get(user_id, 'topup.method_button_stars') if translation_service else "⭐ Telegram Stars"
        keyboard.append([InlineKeyboardButton(stars_text, callback_data="method_stars")])

        wechat_text = translation_service.get(user_id, 'payment.button_wechat') if translation_service else "💚 微信支付"
        keyboard.append([InlineKeyboardButton(wechat_text, callback_data="method_wechat")])

        alipay_text = translation_service.get(user_id, 'payment.button_alipay') if translation_service else "💰 支付宝支付"
        keyboard.append([InlineKeyboardButton(alipay_text, callback_data="method_alipay")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit the message
        try:
            await query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as edit_error:
            if "message is not modified" in str(edit_error).lower():
                pass  # Silently ignore
            else:
                raise

        logger.info(f"User {user_id} redirected to payment method selection from deprecated lucky_discount callback")

    except Exception as e:
        logger.error(f"Error handling lucky discount (deprecated): {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "操作失败，请稍后再试"
        try:
            await query.answer(msg, show_alert=True)
        except:
            pass


async def handle_topup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle top-up package selection (NEW FLOW).

    NEW Flow:
    Step 1: User selects payment method (callback_data: "method_stars", "method_wechat", "method_alipay")
            → Show pricing menu
    Step 2: User selects package (callback_data: "topup_stars_30", "topup_wechat_50", etc.)
            → Create payment
    """
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        callback_data = query.data

        # Check routing pattern
        if callback_data == 'back_to_payment_methods':
            # ===== Back button: Return to payment method selection =====
            await query.answer()
            await show_topup_packages(update, context, is_callback=True)
            logger.info(f"User {user_id} returned to payment method selection")
            return

        elif callback_data.startswith('method_'):
            # ===== NEW FLOW - Step 1: Payment method selected, show pricing =====
            payment_method = callback_data.replace('method_', '')
            await show_pricing_for_method(update, context, payment_method)
            logger.info(f"User {user_id} selected payment method: {payment_method}")
            return

        elif callback_data.startswith('topup_') and '_' in callback_data.replace('topup_', ''):
            # ===== NEW FLOW - Step 2: Package selected, create payment =====
            # Parse: "topup_stars_30" → method='stars', base_amount=30
            parts = callback_data.replace('topup_', '').split('_', 1)
            if len(parts) != 2:
                logger.error(f"Invalid topup callback format: {callback_data}")
                return

            payment_method = parts[0]
            base_amount_cny = int(parts[1])

            # Call dedicated payment creation function
            await create_payment_for_method(update, context, payment_method, base_amount_cny)
            return

        # Legacy support for old flow (if needed for backward compatibility)
        elif callback_data.endswith('_alipay') or callback_data.endswith('_wechat'):
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
                message = f"""💳 等待支付

订单号：{payment_info['payment_id']}
金额：¥{displayed_amount}
积分：{payment_info['credits_amount']}
"""
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
                await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as edit_error:
                # Message was deleted (likely by cleanup middleware), send new message
                logger.debug(f"Could not edit message, sending new message: {str(edit_error)}")
                # Update message_id to the new message for timeout tracking
                sent_msg = await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
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

🔥 *折扣已应用* - 为您节省 ¥{savings}！
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

            # Get translated button text (i18n approach)
            if translation_service:
                alipay_text = translation_service.get(user_id, 'payment.button_alipay')
                wechat_text = translation_service.get(user_id, 'payment.button_wechat')
            else:
                alipay_text = "💰 支付宝支付"
                wechat_text = "💚 微信支付"

            # Build payment method keyboard (WeChat Pay restored for all packages including ¥10)
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


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle Telegram Stars successful_payment update.

    This is triggered when a user completes a Stars payment in Telegram.
    """
    try:
        user_id = update.effective_user.id
        successful_payment = update.message.successful_payment

        logger.info(f"Received successful_payment from user {user_id}")

        # Process payment through Stars provider
        result = await payment_service.stars_provider.handle_successful_payment(successful_payment)

        if result['status'] != 'success':
            logger.error(f"Error processing Stars payment: {result.get('message', 'Unknown error')}")
            if translation_service:
                msg = translation_service.get(user_id, 'payment.processing_error')
            else:
                msg = "支付处理失败，请联系客服"
            await update.message.reply_text(msg)
            return

        payment_id = result['payment_id']
        transaction_id = result['transaction_id']
        amount_stars = result['amount']

        logger.info(
            f"Processing Stars payment completion: {payment_id}, "
            f"telegram_id={transaction_id}, amount={amount_stars} Stars"
        )

        # Process payment completion (credit user's account)
        success, new_balance, error = await payment_service.process_payment_completion(payment_id)

        if not success:
            logger.error(f"Failed to credit user {user_id} for Stars payment {payment_id}: {error}")
            if translation_service:
                msg = translation_service.get(user_id, 'payment.credit_failed')
            else:
                msg = "充值处理失败，请联系客服"
            await update.message.reply_text(msg)
            return

        # Get payment details for confirmation message
        payment = payment_service.db.get_payment(payment_id)
        if not payment:
            logger.error(f"Could not retrieve payment {payment_id} after completion")
            return

        credits_amount = int(payment['credits_amount'])

        # Send success message
        if translation_service:
            message = translation_service.get(
                user_id,
                'payment.stars_success',
                credits=credits_amount,
                stars=amount_stars,
                balance=int(new_balance)
            )
        else:
            message = f"""✅ 支付成功！

获得积分：{credits_amount}
支付金额：{amount_stars} ⭐
当前余额：{int(new_balance)} 积分

感谢您的充值！"""

        await update.message.reply_text(message)

        logger.info(
            f"Stars payment completed successfully: user {user_id}, "
            f"payment {payment_id}, {credits_amount} credits, {amount_stars} Stars"
        )

    except Exception as e:
        logger.error(f"Error handling successful Stars payment: {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "系统错误，请稍后重试"
        try:
            await update.message.reply_text(msg)
        except:
            pass
