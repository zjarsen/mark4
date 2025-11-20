"""Callback query handlers for inline buttons."""

from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# Injected dependencies
state_manager = None
queue_service = None


async def refresh_queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle 'Refresh Queue' button clicks.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        query = update.callback_query
        await query.answer()  # Acknowledge button click

        user_id = update.effective_user.id

        # Extract prompt_id from callback data
        # Format: "refresh_{prompt_id}"
        prompt_id = query.data.replace("refresh_", "")

        logger.debug(f"Queue refresh requested by user {user_id} for prompt {prompt_id}")

        # Get queue message
        queue_message = state_manager.get_queue_message(user_id)

        if not queue_message:
            logger.warning(f"No queue message found for user {user_id}")
            await query.edit_message_text("无法刷新队列信息")
            return

        # Refresh queue position
        await queue_service.refresh_queue_position(prompt_id, queue_message)

        logger.info(f"Refreshed queue position for user {user_id}")

    except Exception as e:
        logger.error(f"Error handling queue refresh: {str(e)}")

        try:
            await query.edit_message_text("刷新失败，请稍后再试")
        except:
            pass


async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle payment-related callbacks (future implementation).

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        query = update.callback_query
        await query.answer()

        # TODO: Implement payment callback handling
        logger.info(f"Payment callback received: {query.data}")

        await query.edit_message_text("支付功能开发中")

    except Exception as e:
        logger.error(f"Error handling payment callback: {str(e)}")


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle 'Cancel' button clicks.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Get workflow service
        workflow_service = context.bot_data.get('workflow_service')

        if workflow_service:
            cancelled = await workflow_service.cancel_user_workflow(user_id)

            if cancelled:
                await query.edit_message_text("操作已取消")
                logger.info(f"Cancelled workflow via callback for user {user_id}")
            else:
                await query.edit_message_text("没有进行中的操作")
        else:
            await query.edit_message_text("无法取消操作")

    except Exception as e:
        logger.error(f"Error handling cancel callback: {str(e)}")
