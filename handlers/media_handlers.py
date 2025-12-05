"""Media upload handlers (photos and documents)."""

from telegram import Update
from telegram.ext import ContextTypes
import logging
from core.constants import (
    INVALID_STATE_MESSAGE,
    ALREADY_PROCESSING_MESSAGE,
    INVALID_FORMAT_MESSAGE,
    MAX_RETRY_MESSAGE,
    UPLOAD_FAILED_MESSAGE
)

logger = logging.getLogger('mark4_bot')

# Injected dependencies
state_manager = None
file_service = None
workflow_service = None
config = None


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo uploads from users.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # Check user state
        is_waiting_image = state_manager.is_state(user_id, 'waiting_for_image')
        is_waiting_video = state_manager.is_state(user_id, 'waiting_for_video')

        # Validate user state
        if not (is_waiting_image or is_waiting_video):
            await update.message.reply_text(INVALID_STATE_MESSAGE)
            return

        # Check if already processing
        if state_manager.is_state(user_id, 'processing'):
            await update.message.reply_text(ALREADY_PROCESSING_MESSAGE)
            return

        # Reset retry count on successful photo upload
        state_manager.update_state(user_id, retry_count=0)

        # Get highest resolution photo
        photo = update.message.photo[-1]

        # Download photo
        local_path = await file_service.download_telegram_photo(
            photo,
            user_id,
            context.bot
        )

        # Start appropriate workflow
        if is_waiting_image:
            # Get image style from state (if exists)
            state = state_manager.get_state(user_id)
            image_style = state.get('image_style')

            if image_style:
                # Has style selection - start image workflow with style
                await workflow_service.start_image_workflow_with_style(
                    update,
                    context,
                    local_path,
                    user_id,
                    image_style
                )
                logger.info(f"Photo processed for user {user_id} (image workflow, style={image_style})")
            else:
                # No style selection - fallback (shouldn't happen in new flow)
                logger.warning(f"User {user_id} uploading image without style selection")
                await update.message.reply_text(
                    "请先从主菜单选择图片处理选项"
                )
                state_manager.reset_state(user_id)
                return

        elif is_waiting_video:
            # Get video style from state
            state = state_manager.get_state(user_id)
            video_style = state.get('video_style')

            if not video_style:
                await update.message.reply_text("风格选择错误，请重新开始")
                state_manager.reset_state(user_id)
                return

            await workflow_service.start_video_workflow(
                update,
                context,
                local_path,
                user_id,
                video_style
            )
            logger.info(f"Photo processed for user {user_id} (video workflow, style: {video_style})")

    except Exception as e:
        logger.error(f"Error handling photo from user {user_id}: {str(e)}")
        await update.message.reply_text(UPLOAD_FAILED_MESSAGE)
        state_manager.reset_state(user_id)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle document uploads (images sent as files).

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # Check user state
        is_waiting_image = state_manager.is_state(user_id, 'waiting_for_image')
        is_waiting_video = state_manager.is_state(user_id, 'waiting_for_video')

        # Validate user state
        if not (is_waiting_image or is_waiting_video):
            return

        # Check if already processing
        if state_manager.is_state(user_id, 'processing'):
            await update.message.reply_text(ALREADY_PROCESSING_MESSAGE)
            return

        document = update.message.document

        # Validate file format
        if not file_service.is_valid_image_format(document.file_name):
            await handle_invalid_format(update, context, user_id)
            return

        # Valid format - reset retry count
        state_manager.update_state(user_id, retry_count=0)

        # Download document
        local_path = await file_service.download_telegram_document(
            document,
            user_id,
            context.bot
        )

        # Start appropriate workflow
        if is_waiting_image:
            # Get image style from state (if exists)
            state = state_manager.get_state(user_id)
            image_style = state.get('image_style')

            if image_style:
                # Has style selection - start image workflow with style
                await workflow_service.start_image_workflow_with_style(
                    update,
                    context,
                    local_path,
                    user_id,
                    image_style
                )
                logger.info(f"Document processed for user {user_id} (image workflow, style={image_style})")
            else:
                # No style selection - fallback (shouldn't happen in new flow)
                logger.warning(f"User {user_id} uploading image without style selection")
                await update.message.reply_text(
                    "请先从主菜单选择图片处理选项"
                )
                state_manager.reset_state(user_id)
                return

        elif is_waiting_video:
            # Get video style from state
            state = state_manager.get_state(user_id)
            video_style = state.get('video_style')

            if not video_style:
                await update.message.reply_text("风格选择错误，请重新开始")
                state_manager.reset_state(user_id)
                return

            await workflow_service.start_video_workflow(
                update,
                context,
                local_path,
                user_id,
                video_style
            )
            logger.info(f"Document processed for user {user_id} (video workflow, style: {video_style})")

    except Exception as e:
        logger.error(f"Error handling document from user {user_id}: {str(e)}")
        await update.message.reply_text(UPLOAD_FAILED_MESSAGE)
        state_manager.reset_state(user_id)


async def handle_invalid_format(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle invalid file format uploads.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        state = state_manager.get_state(user_id)
        retry_count = state.get('retry_count', 0) + 1

        if retry_count >= config.MAX_RETRY_COUNT:
            # Max retries reached - reset and show menu
            await update.message.reply_text(MAX_RETRY_MESSAGE)
            state_manager.reset_state(user_id)

            # Show menu again
            from handlers.command_handlers import show_main_menu
            await show_main_menu(update)

            logger.info(f"User {user_id} exceeded max retry count")

        else:
            # Increment retry count and prompt again
            state_manager.update_state(user_id, retry_count=retry_count)
            await update.message.reply_text(INVALID_FORMAT_MESSAGE)

            logger.debug(
                f"Invalid format from user {user_id}, "
                f"retry {retry_count}/{config.MAX_RETRY_COUNT}"
            )

    except Exception as e:
        logger.error(f"Error handling invalid format: {str(e)}")
