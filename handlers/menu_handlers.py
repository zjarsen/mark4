"""Menu selection handlers."""

from telegram import Update
from telegram.ext import ContextTypes
import logging
from core.constants import (
    MENU_OPTION_IMAGE,
    MENU_OPTION_VIDEO,
    MENU_OPTION_CHECK_QUEUE,
    MENU_OPTION_BALANCE_HISTORY,
    MENU_OPTION_TOPUP,
    SEND_IMAGE_PROMPT,
    FEATURE_NOT_IMPLEMENTED,
    QUEUE_UNAVAILABLE,
    UNEXPECTED_INPUT_MESSAGE
)

logger = logging.getLogger('mark4_bot')

# Injected dependencies
state_manager = None
notification_service = None
queue_service = None
config = None


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Route menu selections to appropriate handlers.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id
        text = update.message.text

        logger.debug(f"User {user_id} selected: {text}")

        if text == MENU_OPTION_IMAGE:
            await handle_image_processing(update, context, user_id)

        elif text == MENU_OPTION_VIDEO or "图片转视频" in text:
            await handle_video_processing(update, context, user_id)

        elif text == MENU_OPTION_CHECK_QUEUE or "查看队列" in text:
            await handle_check_queue(update, context, user_id)

        elif text == MENU_OPTION_BALANCE_HISTORY:
            from handlers.credit_handlers import show_balance_and_history
            await show_balance_and_history(update, context)

        elif text == MENU_OPTION_TOPUP:
            from handlers.credit_handlers import show_topup_packages
            await show_topup_packages(update, context)

        else:
            # Unknown menu option
            logger.warning(f"Unknown menu option from user {user_id}: {text}")
            await update.message.reply_text(UNEXPECTED_INPUT_MESSAGE)

    except Exception as e:
        logger.error(f"Error handling menu selection: {str(e)}")
        raise


async def handle_image_processing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Image Processing' menu selection.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        # Set user state to waiting for image
        state_manager.update_state(
            user_id,
            state='waiting_for_image',
            retry_count=0
        )

        # Prompt user to send image
        await update.message.reply_text(SEND_IMAGE_PROMPT)

        logger.info(f"User {user_id} started image processing workflow")

    except Exception as e:
        logger.error(f"Error in handle_image_processing: {str(e)}")
        raise


async def handle_video_processing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Video Processing' menu selection (not implemented).

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        await update.message.reply_text(FEATURE_NOT_IMPLEMENTED)

        logger.info(f"User {user_id} requested video processing (not implemented)")

    except Exception as e:
        logger.error(f"Error in handle_video_processing: {str(e)}")


async def handle_check_queue(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Check Queue' menu selection.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        # Get queue total
        total = await queue_service.get_queue_total()

        # Send queue total to user
        await notification_service.send_queue_total(
            context.bot,
            user_id,
            total
        )

        logger.info(f"User {user_id} checked queue: {total} total")

    except Exception as e:
        logger.error(f"Error checking queue: {str(e)}")
        await update.message.reply_text(QUEUE_UNAVAILABLE)


async def handle_unexpected_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle unexpected text input.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id
        text = update.message.text

        logger.debug(f"Unexpected text from user {user_id}: {text}")

        # Check if user is in 'waiting_for_image' state
        if state_manager.is_state(user_id, 'waiting_for_image'):
            # User sent text instead of image - treat as invalid format
            from handlers.media_handlers import handle_invalid_format
            await handle_invalid_format(update, context, user_id)
        else:
            # Generic unexpected input
            await update.message.reply_text(UNEXPECTED_INPUT_MESSAGE)

            # Show menu
            from handlers.command_handlers import show_main_menu
            await show_main_menu(update)

    except Exception as e:
        logger.error(f"Error handling unexpected text: {str(e)}")
