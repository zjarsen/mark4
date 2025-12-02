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


async def video_style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle video style selection button clicks.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        query = update.callback_query
        await query.answer()  # Acknowledge button click

        user_id = update.effective_user.id

        # Handle back to menu
        if query.data == "back_to_menu":
            await query.edit_message_text("已取消")
            return

        # Extract style from callback data (video_style_a, video_style_b, video_style_c)
        if not query.data.startswith("video_"):
            await query.edit_message_text("无效的选择")
            return

        style = query.data  # Keep full format: "video_style_a"
        style_name = style.replace("video_", "").replace("_", " ").title()  # "Style A"

        # Check if already processing
        if state_manager.is_state(user_id, 'processing'):
            from core.constants import ALREADY_PROCESSING_MESSAGE
            await query.edit_message_text(ALREADY_PROCESSING_MESSAGE)
            return

        # Validate style
        valid_styles = ['video_style_a', 'video_style_b', 'video_style_c']
        if style not in valid_styles:
            await query.edit_message_text("无效的风格选择")
            return

        # Convert to internal format: "style_a", "style_b", "style_c"
        internal_style = style.replace("video_", "")

        # Update state to waiting for video with selected style
        state_manager.update_state(
            user_id,
            state='waiting_for_video',
            video_style=internal_style,
            retry_count=0
        )

        from core.constants import VIDEO_SEND_IMAGE_PROMPT
        await query.edit_message_text(
            f"已选择 {style_name}\n\n{VIDEO_SEND_IMAGE_PROMPT}"
        )

        logger.info(f"User {user_id} selected video style: {internal_style}")

    except Exception as e:
        logger.error(f"Error handling video style callback: {str(e)}")


async def credit_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle credit confirmation button clicks (confirm or cancel).

    Callback data format:
    - confirm_credits_image
    - confirm_credits_video_style_a
    - confirm_credits_video_style_b
    - confirm_credits_video_style_c
    - cancel_credits
    """
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    try:
        # Handle cancellation
        if query.data == "cancel_credits":
            # Delete confirmation message
            await query.delete_message()

            # Remove from state storage
            if state_manager.has_confirmation_message(user_id):
                state_manager.remove_confirmation_message(user_id)

            # Get uploaded file path and delete it
            state = state_manager.get_state(user_id)
            uploaded_file = state.get('uploaded_file_path')
            if uploaded_file:
                try:
                    import os
                    if os.path.exists(uploaded_file):
                        os.remove(uploaded_file)
                        logger.debug(f"Deleted uploaded file: {uploaded_file}")
                except Exception as e:
                    logger.error(f"Error deleting uploaded file: {e}")

            # Reset state
            state_manager.reset_state(user_id)

            # Send cancelled message and show main menu
            from core.constants import CREDIT_CONFIRMATION_CANCELLED_MESSAGE
            await context.bot.send_message(
                chat_id=user_id,
                text=CREDIT_CONFIRMATION_CANCELLED_MESSAGE
            )

            # Show main menu
            from handlers.command_handlers import show_main_menu
            class FakeMessage:
                def __init__(self, user_id):
                    self.chat = type('obj', (object,), {'id': user_id})
                    self.from_user = type('obj', (object,), {'id': user_id})

            fake_update = type('obj', (object,), {
                'effective_user': type('obj', (object,), {'id': user_id}),
                'message': FakeMessage(user_id)
            })()

            await show_main_menu(fake_update)

            logger.info(f"User {user_id} cancelled credit confirmation")
            return

        # Handle confirmation
        if query.data.startswith("confirm_credits_"):
            workflow_type = query.data.replace("confirm_credits_", "")

            # Delete confirmation message
            await query.delete_message()

            # Remove from state storage
            if state_manager.has_confirmation_message(user_id):
                state_manager.remove_confirmation_message(user_id)

            # Get workflow service from bot_data
            workflow_service = context.bot_data.get('workflow_service')
            if not workflow_service:
                logger.error("workflow_service not found in bot_data")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="系统错误，请稍后重试"
                )
                state_manager.reset_state(user_id)
                return

            # Proceed with appropriate workflow
            if workflow_type == "image":
                success = await workflow_service.proceed_with_image_workflow(
                    context.bot,
                    user_id
                )
                logger.info(
                    f"User {user_id} confirmed image workflow, "
                    f"success: {success}"
                )

            elif workflow_type.startswith("video_"):
                success = await workflow_service.proceed_with_video_workflow(
                    context.bot,
                    user_id
                )
                logger.info(
                    f"User {user_id} confirmed video workflow, "
                    f"success: {success}"
                )

            else:
                logger.error(f"Unknown workflow type: {workflow_type}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="系统错误，请稍后重试"
                )
                state_manager.reset_state(user_id)

    except Exception as e:
        logger.error(f"Error handling credit confirmation callback: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text="处理确认时发生错误，请稍后重试"
        )
        state_manager.reset_state(user_id)
