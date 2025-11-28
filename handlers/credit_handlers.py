"""Handlers for credit-related operations."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# Injected dependencies
credit_service = None
payment_service = None
timeout_service = None


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
            TOPUP_1_BUTTON,
            TOPUP_10_BUTTON,
            TOPUP_30_BUTTON,
            TOPUP_50_BUTTON,
            TOPUP_100_BUTTON
        )

        # Create inline keyboard with package options
        keyboard = [
            [InlineKeyboardButton(TOPUP_1_BUTTON, callback_data="topup_1")],
            [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
            [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
            [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
            [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
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


async def show_balance_and_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's balance and transaction history combined."""
    try:
        user_id = update.effective_user.id

        # Get user stats
        stats = await credit_service.get_user_stats(user_id)

        # Get transactions
        transactions = await credit_service.get_transaction_history(user_id, limit=10)

        from core.constants import (
            TRANSACTION_ITEM_TEMPLATE
        )

        # Build combined message
        message = f"""📊 积分余额 & 充值记录

💰 当前积分：{stats['balance']} 积分
📈 累计消费：{stats['total_spent']} 积分

图片脱衣：10 积分/次

━━━━━━━━━━━━━━━━━━━━━━

📝 最近10笔记录：

"""

        if not transactions:
            message += "暂无消费记录"
        else:
            # Format transactions
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
        logger.info(f"User {user_id} viewed balance and history")

    except Exception as e:
        logger.error(f"Error showing balance and history: {str(e)}")
        await update.message.reply_text("查询失败，请稍后重试")


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
        from core.constants import (
            PAYMENT_TIMEOUT_MESSAGE,
            TOPUP_PACKAGES,
            TOPUP_1_BUTTON,
            TOPUP_10_BUTTON,
            TOPUP_30_BUTTON,
            TOPUP_50_BUTTON,
            TOPUP_100_BUTTON
        )

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

        # Send new message with top-up packages below
        keyboard = [
            [InlineKeyboardButton(TOPUP_1_BUTTON, callback_data="topup_1")],
            [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
            [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
            [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
            [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        from core.constants import TOPUP_PACKAGES_MESSAGE
        menu_message = await bot.send_message(
            chat_id=chat_id,
            text=TOPUP_PACKAGES_MESSAGE,
            reply_markup=reply_markup
        )

        # Store both message IDs for cleanup
        timeout_service.add_timeout_messages(user_id, message_id, menu_message.message_id)

        logger.info(f"Payment timeout displayed for user {user_id}, payment {payment_id}")

    except Exception as e:
        logger.error(f"Error handling payment timeout for user {user_id}: {str(e)}", exc_info=True)


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
            amount_cny = int(parts[0])
            payment_method = parts[1]  # 'alipay' or 'wechat'

            # Get chat_id and message_id for later editing
            chat_id = query.message.chat_id
            message_id = query.message.message_id

            # Create payment
            success, payment_info, error = await payment_service.create_topup_payment(
                user_id,
                amount_cny,
                payment_method,
                chat_id=chat_id,
                message_id=message_id
            )

            if not success:
                await query.edit_message_text(f"创建支付失败: {error}")
                return

            from core.constants import PAYMENT_PENDING_MESSAGE
            payment_method_cn = "支付宝" if payment_method == "alipay" else "微信支付"
            message = PAYMENT_PENDING_MESSAGE.format(
                payment_id=payment_info['payment_id'],
                amount=payment_info['amount_cny'],
                credits=payment_info['credits_amount']
            )
            message += f"\n支付方式：{payment_method_cn}"

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

            # Show payment method selection
            message = f"""💳 充值 ¥{amount_cny} = {credits}积分

请选择支付方式："""

            keyboard = [
                [InlineKeyboardButton(
                    "💰 支付宝支付",
                    callback_data=f"topup_{amount_cny}_alipay"
                )],
                [InlineKeyboardButton(
                    "💚 微信支付",
                    callback_data=f"topup_{amount_cny}_wechat"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(message, reply_markup=reply_markup)

            logger.info(f"User {user_id} selected amount ¥{amount_cny}, showing payment methods")

    except Exception as e:
        logger.error(f"Error handling top-up callback: {str(e)}")
        try:
            await query.edit_message_text("创建支付失败，请稍后重试")
        except:
            pass
