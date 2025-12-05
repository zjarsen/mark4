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
credit_service = None


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

        logger.info(f"[MENU_SELECTION] User {user_id} sent text: '{text}'")
        logger.info(f"[MENU_SELECTION] Text length: {len(text)}, starts with '1.': {text.startswith('1.')}")

        # Use partial matching since menu text is dynamic
        if text.startswith("1.") or "图生图" in text or "图片脱衣" in text:
            logger.info(f"[MENU_SELECTION] Matched option 1 (image processing) for user {user_id}")
            await handle_image_processing(update, context, user_id)

        elif text.startswith("2.") or "图生成视频" in text or "视频类脱衣" in text or "图片转视频" in text:
            logger.info(f"[MENU_SELECTION] Matched option 2 (video processing) for user {user_id}")
            await handle_video_processing(update, context, user_id)

        elif text.startswith("3.") or "查看队列" in text:
            logger.info(f"[MENU_SELECTION] Matched option 3 (check queue) for user {user_id}")
            await handle_check_queue(update, context, user_id)

        elif text.startswith("4.") or "积分余额" in text or "充值记录" in text:
            logger.info(f"[MENU_SELECTION] Matched option 4 (balance history) for user {user_id}")
            from handlers.credit_handlers import show_balance_and_history
            await show_balance_and_history(update, context)

        elif text.startswith("5.") or "充值积分" in text:
            logger.info(f"[MENU_SELECTION] Matched option 5 (topup) for user {user_id}")
            from handlers.credit_handlers import show_topup_packages
            await show_topup_packages(update, context)

        else:
            # Unknown menu option
            logger.warning(f"[MENU_SELECTION] No match found for text from user {user_id}: '{text}'")
            logger.warning(f"[MENU_SELECTION] Sending UNEXPECTED_INPUT_MESSAGE")
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
    Handle 'Image Processing' menu selection - show style selection with dynamic trial status.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: User ID
    """
    try:
        logger.info(f"[IMAGE_PROCESSING] Function called for user {user_id}")
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from core.constants import (
            IMAGE_STYLE_BRA_BUTTON,
            BACK_TO_MENU_BUTTON,
            ALREADY_PROCESSING_MESSAGE
        )
        from datetime import datetime
        import pytz

        # Check if user is already processing
        if state_manager.is_state(user_id, 'processing'):
            logger.info(f"[IMAGE_PROCESSING] User {user_id} already processing, showing error")
            await update.message.reply_text(ALREADY_PROCESSING_MESSAGE)
            return

        # Check trial status for undress style
        has_trial = await credit_service.has_free_trial(user_id)

        # Generate dynamic button text for undress style
        if has_trial:
            undress_button_text = "🆓 脱到精光 ✨免费体验✨"
            trial_status = "🎁🎉 **免费体验可用！** 🎉🎁\n💫 使用后2天内自动重置"
        else:
            # Get next free trial time and calculate countdown
            next_trial_time = await credit_service.get_next_free_trial_time(user_id)

            if next_trial_time:
                # Calculate time difference
                beijing_tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(beijing_tz)
                time_diff = next_trial_time - now

                # Convert to days and hours
                days = time_diff.days
                hours = time_diff.seconds // 3600

                if days > 0:
                    countdown = f"{days}天{hours}小时"
                else:
                    countdown = f"{hours}小时"

                undress_button_text = f"脱到精光（10积分）"
                trial_status = f"⏰ **距离下次免费：{countdown}**\n💳 当前需要：10积分"
            else:
                # No trial history, treat as available
                undress_button_text = "🆓 脱到精光 ✨免费体验✨"
                trial_status = "🎁🎉 **免费体验可用！** 🎉🎁\n💫 使用后2天内自动重置"

        # Generate dynamic message
        message = f"""🎨 选择脱衣风格

━━━━━━━━━━━━━━━━━━
1️⃣ 粉色蕾丝内衣示例✨✨
[🔞点击观看🔞](https://t.me/placeholder1)

🎁💝 **100%永久免费！** 💝🎁
🆓 **无需积分！随时使用！** 🆓
━━━━━━━━━━━━━━━━━━

2️⃣ 脱到精光示例✨✨
[🔞点击观看🔞](https://t.me/placeholder2)

{trial_status}
━━━━━━━━━━━━━━━━━━

请选择您想要的风格："""

        # Build keyboard with dynamic button text
        keyboard = [
            [InlineKeyboardButton(IMAGE_STYLE_BRA_BUTTON, callback_data="image_style_bra")],
            [InlineKeyboardButton(undress_button_text, callback_data="image_style_undress")],
            [InlineKeyboardButton(BACK_TO_MENU_BUTTON, callback_data="back_to_menu")]
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
        from core.constants import ERROR_MESSAGE
        await update.message.reply_text(ERROR_MESSAGE)


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
        from core.constants import (
            VIDEO_STYLE_SELECTION_MESSAGE,
            VIDEO_STYLE_A_BUTTON,
            VIDEO_STYLE_B_BUTTON,
            VIDEO_STYLE_C_BUTTON,
            BACK_TO_MENU_BUTTON,
            ALREADY_PROCESSING_MESSAGE
        )

        # Check if user is already processing
        if state_manager.is_state(user_id, 'processing'):
            await update.message.reply_text(ALREADY_PROCESSING_MESSAGE)
            return

        # Show style selection keyboard
        keyboard = [
            [InlineKeyboardButton(VIDEO_STYLE_A_BUTTON, callback_data="video_style_a")],
            [InlineKeyboardButton(VIDEO_STYLE_B_BUTTON, callback_data="video_style_b")],
            [InlineKeyboardButton(VIDEO_STYLE_C_BUTTON, callback_data="video_style_c")],
            [InlineKeyboardButton(BACK_TO_MENU_BUTTON, callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            VIDEO_STYLE_SELECTION_MESSAGE,
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

        logger.warning(f"[UNEXPECTED_TEXT] Called for user {user_id} with text: '{text}'")
        logger.warning(f"[UNEXPECTED_TEXT] This handler should NOT be called directly - menu_selection should handle everything")

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
