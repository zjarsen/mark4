"""Handlers for credit-related operations."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

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
