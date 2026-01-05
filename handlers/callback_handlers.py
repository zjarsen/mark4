"""Callback query handlers for inline buttons."""

from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# Injected dependencies
state_manager = None
queue_service = None
translation_service = None


async def refresh_queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    DEPRECATED: This handler is no longer used.

    The refresh queue functionality has been moved to an inline handler
    in core/bot_application.py to properly handle message editing with
    stored message IDs from state manager.

    This function is kept for backward compatibility but should not be called.
    """
    logger.warning(
        f"DEPRECATED refresh_queue_callback called - "
        f"this should not happen. Check handler registration."
    )

    query = update.callback_query
    user_id = update.effective_user.id
    if translation_service:
        msg = translation_service.get(user_id, 'callbacks.deprecated_function')
    else:
        msg = "此功能已更新，请重新提交任务"
    await query.answer(msg, show_alert=True)


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

        user_id = update.effective_user.id

        # TODO: Implement payment callback handling
        logger.info(f"Payment callback received: {query.data}")

        if translation_service:
            msg = translation_service.get(user_id, 'callbacks.payment_in_development')
        else:
            msg = "支付功能开发中"
        await query.edit_message_text(msg)

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
                if translation_service:
                    msg = translation_service.get(user_id, 'callbacks.operation_cancelled')
                else:
                    msg = "操作已取消"
                await query.edit_message_text(msg)
                logger.info(f"Cancelled workflow via callback for user {user_id}")
            else:
                if translation_service:
                    msg = translation_service.get(user_id, 'callbacks.no_operation_in_progress')
                else:
                    msg = "没有进行中的操作"
                await query.edit_message_text(msg)
        else:
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.cannot_cancel')
            else:
                msg = "无法取消操作"
            await query.edit_message_text(msg)

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
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.cancelled')
            else:
                msg = "已取消"
            await query.edit_message_text(msg)
            return

        # Extract style from callback data (video_style_a, video_style_b, video_style_c)
        if not query.data.startswith("video_"):
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.invalid_selection')
            else:
                msg = "无效的选择"
            await query.edit_message_text(msg)
            return

        style = query.data  # Keep full format: "video_style_a"

        # Map callback data to translated style names
        if translation_service:
            style_map = {
                'video_style_a': translation_service.get(user_id, 'video.style_a_name'),
                'video_style_b': translation_service.get(user_id, 'video.style_b_name'),
                'video_style_c': translation_service.get(user_id, 'video.style_c_name')
            }
            style_name = style_map.get(style, style)
        else:
            from core.constants import WORKFLOW_NAME_VIDEO_A, WORKFLOW_NAME_VIDEO_B, WORKFLOW_NAME_VIDEO_C
            style_map = {
                'video_style_a': WORKFLOW_NAME_VIDEO_A,
                'video_style_b': WORKFLOW_NAME_VIDEO_B,
                'video_style_c': WORKFLOW_NAME_VIDEO_C
            }
            style_name = style_map.get(style, style)

        # Check if already processing
        if state_manager.is_state(user_id, 'processing'):
            if translation_service:
                msg = translation_service.get(user_id, 'processing.already_processing')
            else:
                from core.constants import ALREADY_PROCESSING_MESSAGE
                msg = ALREADY_PROCESSING_MESSAGE
            await query.edit_message_text(msg)
            return

        # Validate style
        valid_styles = ['video_style_a', 'video_style_b', 'video_style_c']
        if style not in valid_styles:
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.invalid_style')
            else:
                msg = "无效的风格选择"
            await query.edit_message_text(msg)
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

        if translation_service:
            prompt = translation_service.get(user_id, 'video.send_image_prompt')
            msg = translation_service.get(user_id, 'callbacks.style_selected_video', style_name=style_name, prompt=prompt)
        else:
            from core.constants import VIDEO_SEND_IMAGE_PROMPT
            msg = f"已选择 {style_name}\n\n{VIDEO_SEND_IMAGE_PROMPT}"
        await query.edit_message_text(msg)

        logger.info(f"User {user_id} selected video style: {internal_style}")

    except Exception as e:
        logger.error(f"Error handling video style callback: {str(e)}")


async def image_style_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle image style selection button clicks.

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
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.cancelled')
            else:
                msg = "已取消"
            await query.edit_message_text(msg)
            return

        # Extract style from callback data (image_style_bra, image_style_undress)
        if not query.data.startswith("image_style_"):
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.invalid_selection')
            else:
                msg = "无效的选择"
            await query.edit_message_text(msg)
            return

        style = query.data  # Keep full format: "image_style_bra" or "image_style_undress"

        # Validate style
        valid_styles = ['image_style_bra', 'image_style_undress']
        if style not in valid_styles:
            if translation_service:
                msg = translation_service.get(user_id, 'callbacks.invalid_style')
            else:
                msg = "无效的风格选择"
            await query.edit_message_text(msg)
            return

        # Convert to internal format: "bra" or "undress"
        internal_style = style.replace("image_style_", "")

        # Check if already processing
        if state_manager.is_state(user_id, 'processing'):
            if translation_service:
                msg = translation_service.get(user_id, 'processing.already_processing')
            else:
                from core.constants import ALREADY_PROCESSING_MESSAGE
                msg = ALREADY_PROCESSING_MESSAGE
            await query.edit_message_text(msg)
            return

        # Map callback data to translated style names
        if translation_service:
            style_map = {
                'image_style_bra': translation_service.get(user_id, 'image.style_bra_name'),
                'image_style_undress': translation_service.get(user_id, 'image.style_undress_name')
            }
            style_name = style_map.get(style, style)
        else:
            from core.constants import WORKFLOW_NAME_IMAGE_BRA, WORKFLOW_NAME_IMAGE_UNDRESS
            style_map = {
                'image_style_bra': WORKFLOW_NAME_IMAGE_BRA,
                'image_style_undress': WORKFLOW_NAME_IMAGE_UNDRESS
            }
            style_name = style_map.get(style, style)

        # Update state to waiting for image with selected style
        state_manager.update_state(
            user_id,
            state='waiting_for_image',
            image_style=internal_style,
            retry_count=0
        )

        if translation_service:
            prompt = translation_service.get(user_id, 'image.send_image_prompt')
            msg = translation_service.get(user_id, 'callbacks.style_selected_image', style_name=style_name, prompt=prompt)
        else:
            from core.constants import SEND_IMAGE_PROMPT
            msg = f"已选择 {style_name}\n\n{SEND_IMAGE_PROMPT}"
        await query.edit_message_text(msg, parse_mode='Markdown')

        logger.info(f"User {user_id} selected image style: {internal_style}")

    except Exception as e:
        logger.error(f"Error handling image style callback: {str(e)}")
        user_id = update.effective_user.id
        if translation_service:
            msg = translation_service.get(user_id, 'callbacks.style_selection_error')
        else:
            msg = "选择风格时发生错误，请重试"
        await update.effective_chat.send_message(msg)


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
            if translation_service:
                msg = translation_service.get(user_id, 'credits.confirmation_cancelled')
            else:
                from core.constants import CREDIT_CONFIRMATION_CANCELLED_MESSAGE
                msg = CREDIT_CONFIRMATION_CANCELLED_MESSAGE
            await context.bot.send_message(
                chat_id=user_id,
                text=msg
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
                if translation_service:
                    msg = translation_service.get(user_id, 'errors.system')
                else:
                    msg = "系统错误，请稍后重试"
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg
                )
                state_manager.reset_state(user_id)
                return

            # Proceed with appropriate workflow
            if workflow_type.startswith("image_"):
                # Styled image workflows (image_bra, image_undress)
                success = await workflow_service.proceed_with_image_workflow_with_style(
                    context.bot,
                    user_id
                )
                logger.info(
                    f"User {user_id} confirmed styled image workflow, "
                    f"type: {workflow_type}, success: {success}"
                )

            elif workflow_type == "image":
                # Legacy image workflow (backward compatibility)
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
                if translation_service:
                    msg = translation_service.get(user_id, 'errors.system')
                else:
                    msg = "系统错误，请稍后重试"
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg
                )
                state_manager.reset_state(user_id)

    except Exception as e:
        logger.error(f"Error handling credit confirmation callback: {str(e)}")
        if translation_service:
            msg = translation_service.get(user_id, 'callbacks.confirmation_error')
        else:
            msg = "处理确认时发生错误，请稍后重试"
        await context.bot.send_message(
            chat_id=user_id,
            text=msg
        )
        state_manager.reset_state(user_id)


async def open_topup_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle callback for opening top-up menu from inline button.
    This is triggered by the button in the welcome message.
    Also sets up the reply keyboard (main menu) at the bottom.
    """
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id

        # Import and call show_topup_packages
        from handlers.credit_handlers import show_topup_packages

        # Call with is_callback=True to edit the existing message
        await show_topup_packages(update, context, is_callback=True)

        # Note: Reply keyboard is already active from language selection
        # No need to send another 👇 message here

        logger.info(f"User {update.effective_user.id} opened top-up menu from welcome button")

    except Exception as e:
        logger.error(f"Error opening top-up menu: {str(e)}")
        user_id = update.effective_user.id
        if translation_service:
            msg = translation_service.get(user_id, 'callbacks.topup_menu_error')
        else:
            msg = "打开充值菜单失败，请稍后重试"
        await query.answer(msg, show_alert=True)
