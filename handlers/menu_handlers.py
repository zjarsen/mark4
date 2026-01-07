"""Menu selection handlers."""

from telegram import Update
from telegram.ext import ContextTypes
import logging
from core.constants import (
    DEMO_LINK_BRA,
    DEMO_LINK_UNDRESS
)

logger = logging.getLogger('mark4_bot')

# Injected dependencies
state_manager = None
notification_service = None
queue_service = None
config = None
credit_service = None
translation_service = None


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Route menu selections to appropriate handlers using numeric prefix (language-independent).

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id
        text = update.message.text

        logger.info(f"[MENU_SELECTION] User {user_id} sent text: '{text}'")

        # Use numeric prefix matching (language-independent routing)
        if text.startswith("1."):
            logger.info(f"[MENU_SELECTION] Matched option 1 (image processing) for user {user_id}")
            await handle_image_processing(update, context, user_id)

        elif text.startswith("2."):
            logger.info(f"[MENU_SELECTION] Matched option 2 (video processing) for user {user_id}")
            await handle_video_processing(update, context, user_id)

        elif text.startswith("3."):
            logger.info(f"[MENU_SELECTION] Matched option 3 (topup) for user {user_id}")
            from handlers.credit_handlers import show_topup_packages
            await show_topup_packages(update, context)

        elif text.startswith("4."):
            logger.info(f"[MENU_SELECTION] Matched option 4 (balance history) for user {user_id}")
            from handlers.credit_handlers import show_balance_and_history
            await show_balance_and_history(update, context)

        elif text.startswith("5."):
            logger.info(f"[MENU_SELECTION] Matched option 5 (check queue) for user {user_id}")
            await handle_check_queue(update, context, user_id)

        elif text.startswith("6."):
            logger.info(f"[MENU_SELECTION] Matched option 6 (language) for user {user_id}")
            from handlers.language_handlers import show_language_selection
            await show_language_selection(update, context, is_first_time=False)

        else:
            # Unknown menu option
            logger.warning(f"[MENU_SELECTION] No match found for text from user {user_id}: '{text}'")
            if translation_service:
                msg = translation_service.get(user_id, 'errors.unexpected_input')
            else:
                msg = "💡 请选择功能\n\n请点击下方菜单按钮\n或发送对应数字（如：1、2、3）"
            await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error handling menu selection: {str(e)}")
        raise


async def handle_image_processing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Image Processing' menu selection - show style selection with dynamic trial status.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        logger.info(f"[IMAGE_PROCESSING] Function called for user {user_id}")
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from datetime import datetime
        import pytz

        # Check onboarding requirement first
        from handlers.onboarding_handlers import is_onboarding_required, show_onboarding_flow
        if is_onboarding_required(user_id):
            logger.info(f"[IMAGE_PROCESSING] User {user_id} needs to complete onboarding")
            await show_onboarding_flow(update, context, user_id, source_feature='image')
            return

        # Check if user is already processing
        if state_manager.is_state(user_id, 'processing'):
            logger.info(f"[IMAGE_PROCESSING] User {user_id} already processing, showing error")
            if translation_service:
                msg = translation_service.get(user_id, 'processing.already_processing')
            else:
                msg = "⏳ 您的图片正在处理中\n\n请耐心等待当前任务完成\n多次提交不会加快处理速度哦～"
            await update.message.reply_text(msg)
            return

        # Check trial status for undress style
        has_trial = await credit_service.has_free_trial(user_id)

        # Get translated button text
        if translation_service:
            bra_button = translation_service.get(user_id, 'image.style_bra_button')
            back_button = translation_service.get(user_id, 'buttons.back_to_menu')
        else:
            bra_button = "🎁 粉色蕾丝内衣 ✨永久免费✨"
            back_button = "🏠 返回主菜单"

        # Generate dynamic button text for undress style (for now keep it simple)
        if translation_service:
            undress_button_text = translation_service.get(user_id, 'image.style_undress_button')
        else:
            undress_button_text = "脱到精光（10积分）"

        # For now, use simplified version of style selection message
        # The complex trial status display can be enhanced later
        if translation_service:
            message = translation_service.get(user_id, 'image.style_selection')
        else:
            message = f"""🎨 选择脱衣风格

━━━━━━━━━━━━━━━━━━
1️⃣ 粉色蕾丝内衣示例✨✨
[🔞点击观看🔞]({DEMO_LINK_BRA})

🎁💝 *100%永久免费！* 💝🎁
🆓 *无需积分！随时使用！* 🆓
━━━━━━━━━━━━━━━━━━

2️⃣ 脱到精光示例✨✨
[🔞点击观看🔞]({DEMO_LINK_UNDRESS})

请选择您想要的风格："""

        # Build keyboard with dynamic button text
        keyboard = [
            [InlineKeyboardButton(bra_button, callback_data="image_style_bra")],
            [InlineKeyboardButton(undress_button_text, callback_data="image_style_undress")],
            [InlineKeyboardButton(back_button, callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        logger.info(
            f"User {user_id} requested image processing - showing style selection "
            f"(trial available: {has_trial})"
        )

    except Exception as e:
        logger.error(f"Error in handle_image_processing: {str(e)}")
        if translation_service:
            msg = translation_service.get(user_id, 'errors.system')
        else:
            msg = "❌ 系统繁忙\n\n请稍后重试\n如问题持续出现，请联系客服"
        await update.message.reply_text(msg)


async def handle_video_processing(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Video Processing' menu selection - show style selection.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # Check onboarding requirement first
        from handlers.onboarding_handlers import is_onboarding_required, show_onboarding_flow
        if is_onboarding_required(user_id):
            logger.info(f"[VIDEO_PROCESSING] User {user_id} needs to complete onboarding")
            await show_onboarding_flow(update, context, user_id, source_feature='video')
            return

        # Check if user is already processing
        if state_manager.is_state(user_id, 'processing'):
            if translation_service:
                msg = translation_service.get(user_id, 'processing.already_processing')
            else:
                msg = "⏳ 您的图片正在处理中\n\n请耐心等待当前任务完成\n多次提交不会加快处理速度哦～"
            await update.message.reply_text(msg)
            return

        # Get translated text
        if translation_service:
            message = translation_service.get(user_id, 'video.style_selection')
            style_a = translation_service.get(user_id, 'video.style_a_button')
            style_b = translation_service.get(user_id, 'video.style_b_button')
            style_c = translation_service.get(user_id, 'video.style_c_button')
            back_button = translation_service.get(user_id, 'buttons.back_to_menu')
        else:
            message = "🎬 选择视频风格\n\n模型效果展示：\n\n1. 视频模型1示例：✨✨脱衣+抖胸✨✨：\n[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/13)\n\n2. 视频模型2示例：✨✨脱衣+下体流精✨✨：\n[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/15)\n\n3. 视频模型3示例：✨✨脱衣+吃吊喝精✨✨：\n[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/19)\n\n请选择您想要的动态效果："
            style_a = "脱衣+抖胸（30积分）"
            style_b = "脱衣+下体流精（30积分）"
            style_c = "脱衣+ 吃吊喝精（30积分）"
            back_button = "🏠 返回主菜单"

        # Show style selection keyboard
        keyboard = [
            [InlineKeyboardButton(style_a, callback_data="video_style_a")],
            [InlineKeyboardButton(style_b, callback_data="video_style_b")],
            [InlineKeyboardButton(style_c, callback_data="video_style_c")],
            [InlineKeyboardButton(back_button, callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        logger.info(f"User {user_id} requested video processing - showing style selection")

    except Exception as e:
        logger.error(f"Error in handle_video_processing: {str(e)}")


async def handle_check_queue(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
):
    """
    Handle 'Check Queue' menu selection.
    Shows application-layer queue status from queue managers.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        logger.info(f"handle_check_queue called for user {user_id}")
        logger.info(f"Update type: message={bool(update.message)}, callback_query={bool(update.callback_query)}")

        # Get workflow service from bot data
        workflow_service = context.bot_data.get('workflow_service')

        if not workflow_service:
            logger.error("workflow_service not found in bot_data")
            if translation_service:
                msg = translation_service.get(user_id, 'queue.unavailable')
            else:
                msg = "⚠️ 队列系统繁忙中\n请稍后再试或联系客服"
            # Handle both message and callback query
            if update.callback_query:
                await update.callback_query.answer(msg, show_alert=True)
            elif update.message:
                await update.message.reply_text(msg)
            return

        logger.info("Getting application queue status...")
        # Get application queue status
        status = queue_service.get_application_queue_status(workflow_service)
        logger.info(f"Queue status retrieved: {status['total_jobs']} total jobs")

        # Format queue status message with improved UI
        message = "━━━━━━━━━━━━━━━━━\n"
        if translation_service:
            message += translation_service.get(user_id, 'queue.status_header', default="📊 *Current Queue Status*")
        else:
            message += "📊 *当前队列状态*"
        message += "\n━━━━━━━━━━━━━━━━━\n\n"

        # Per-manager detailed status (no overview section)
        for workflow_type, servers in status['managers'].items():
            # Workflow type icon and label
            if workflow_type == 'image':
                workflow_icon = "🖼️"
                if translation_service:
                    workflow_label = translation_service.get(user_id, 'queue.label_image', default="Image Processing")
                else:
                    workflow_label = "图片处理"
            else:
                workflow_icon = "🎬"
                if translation_service:
                    workflow_label = translation_service.get(user_id, 'queue.label_video', default="Video Processing")
                else:
                    workflow_label = "视频处理"

            message += f"{workflow_icon} *{workflow_label}*\n"

            # Convert server keys to numbered servers (1号, 2号, etc.)
            server_number = 1
            for server_key, manager_status in servers.items():
                vip_count = manager_status['vip_queue_size']
                regular_count = manager_status['regular_queue_size']
                is_processing = manager_status['processing']

                # Include processing task in total count
                total_count = vip_count + regular_count + (1 if is_processing else 0)

                # Show server details with numbered naming
                if translation_service:
                    server_line = translation_service.get(user_id, 'queue.server_status', server_number=server_number, total_count=total_count, default=f"  └─ Server *{server_number}*: *{total_count}* tasks")
                else:
                    server_line = f"  └─ 服务器 *{server_number}号*：*{total_count}* 个任务"
                message += server_line + "\n"

                if vip_count > 0:
                    if translation_service:
                        vip_line = translation_service.get(user_id, 'queue.vip_count', vip_count=vip_count, default=f"     • 👑 VIP: *{vip_count}*")
                    else:
                        vip_line = f"     • 👑 VIP：*{vip_count}* 个"
                    message += vip_line + "\n"

                if regular_count > 0:
                    if translation_service:
                        regular_line = translation_service.get(user_id, 'queue.regular_count', regular_count=regular_count, default=f"     • 👤 Regular: *{regular_count}*")
                    else:
                        regular_line = f"     • 👤 普通：*{regular_count}* 个"
                    message += regular_line + "\n"

                server_number += 1

            message += "\n"

        # Footer with helpful info
        message += "━━━━━━━━━━━━━━━━━\n"
        if translation_service:
            message += translation_service.get(user_id, 'queue.vip_priority_tip', default="💡 *Tip*: VIP users have priority processing")
        else:
            message += "💡 *提示*：VIP用户享有优先处理权"

        logger.info(f"Sending queue status message to user {user_id}")

        # Handle both message and callback query
        if update.callback_query:
            # Answer the callback query first to stop loading
            await update.callback_query.answer()
            # Send the queue status as a new message
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Queue status sent via callback query for user {user_id}")
        elif update.message:
            await update.message.reply_text(message, parse_mode='Markdown')
            logger.info(f"Queue status sent via message reply for user {user_id}")

        logger.info(f"User {user_id} checked queue: {status['total_jobs']} total jobs")

    except Exception as e:
        logger.error(f"Error checking queue: {str(e)}", exc_info=True)
        user_id = update.effective_user.id if update.effective_user else None
        if translation_service and user_id:
            msg = translation_service.get(user_id, 'queue.unavailable')
        else:
            msg = "⚠️ 队列系统繁忙中\n请稍后再试或联系客服"
        # Handle both message and callback query
        if update.callback_query:
            await update.callback_query.answer(msg, show_alert=True)
        elif update.message:
            await update.message.reply_text(msg)


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

        logger.warning(f"[UNEXPECTED_TEXT] Called for user {user_id} with text: '{text}'")
        logger.warning(f"[UNEXPECTED_TEXT] This handler should NOT be called directly - menu_selection should handle everything")

        # Check if user is in 'waiting_for_image' state
        if state_manager.is_state(user_id, 'waiting_for_image'):
            # User sent text instead of image - treat as invalid format
            from handlers.media_handlers import handle_invalid_format
            await handle_invalid_format(update, context, user_id)
        else:
            # Generic unexpected input
            if translation_service:
                msg = translation_service.get(user_id, 'errors.unexpected_input')
            else:
                msg = "💡 请选择功能\n\n请点击下方菜单按钮\n或发送对应数字（如：1、2、3）"
            await update.message.reply_text(msg)

            # Show menu
            from handlers.command_handlers import show_main_menu
            await show_main_menu(update)

    except Exception as e:
        logger.error(f"Error handling unexpected text: {str(e)}")
