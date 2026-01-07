"""Onboarding handlers for mandatory channel/bot follow flow."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging

logger = logging.getLogger('mark4_bot')

# Injected dependencies
database_service = None
config = None
translation_service = None


async def check_channel_membership(bot, user_id: int, channel: str) -> bool:
    """
    Check if user is a member of the required channel.

    Args:
        bot: Telegram bot instance
        user_id: User ID to check
        channel: Channel username (e.g., '@zuiqiangtuoyi')

    Returns:
        True if user is a member
    """
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        status = member.status
        is_member = status in ['member', 'administrator', 'creator']
        logger.info(f"Channel check for user {user_id} in {channel}: status={status}, is_member={is_member}")
        return is_member
    except TelegramError as e:
        logger.error(f"Error checking channel membership for user {user_id}: {e}")
        return False


def check_backup_bot_started(user_id: int, bot_id: str) -> bool:
    """
    Check if user has started the backup bot.

    Args:
        user_id: User ID to check
        bot_id: Source bot ID

    Returns:
        True if user has started the backup bot
    """
    return database_service.check_user_started_backup_bot(user_id, bot_id)


async def show_onboarding_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None, source_feature: str = None):
    """
    Display the onboarding flow with 2 steps.

    Args:
        update: Telegram Update
        context: Telegram Context
        user_id: Optional user ID (if not provided, extracted from update)
        source_feature: Optional feature user was trying to access ('image' or 'video')
    """
    if user_id is None:
        user_id = update.effective_user.id

    # Store source feature in user_data so we can redirect after verification
    if source_feature:
        context.user_data['onboarding_source'] = source_feature

    # Get translations
    title = translation_service.get(user_id, 'onboarding.title') if translation_service else "Stay Connected - Quick Setup"
    description = translation_service.get(user_id, 'onboarding.description') if translation_service else (
        "Bots like this get banned frequently by Telegram.\n\n"
        "To make sure you don't lose access and can always find us again, please complete these 2 quick steps:"
    )
    step1_label = translation_service.get(user_id, 'onboarding.step1_label') if translation_service else "Step 1: Follow our announcement channel"
    step1_desc = translation_service.get(user_id, 'onboarding.step1_desc') if translation_service else "We'll post the new bot link here if this one gets banned"
    step1_button = translation_service.get(user_id, 'onboarding.step1_button') if translation_service else "Follow Channel"
    step2_label = translation_service.get(user_id, 'onboarding.step2_label') if translation_service else "Step 2: Start our backup bot"
    step2_desc = translation_service.get(user_id, 'onboarding.step2_desc') if translation_service else "We'll notify you directly when we move to a new bot"
    step2_button = translation_service.get(user_id, 'onboarding.step2_button') if translation_service else "Start Backup Bot"
    verify_button = translation_service.get(user_id, 'onboarding.verify_button') if translation_service else "Done - Verify & Continue"

    # Build message
    message = f"""
{title}

{description}

*{step1_label}*
_{step1_desc}_

*{step2_label}*
_{step2_desc}_
"""

    # Build keyboard
    channel = config.REQUIRED_CHANNEL if config else '@zuiqiangtuoyi'
    backup_bot_username = config.BACKUP_BOT_USERNAME if config else 'HumanityBackupBot'
    bot_id = config.BOT_ID if config else 'default_bot'

    # Deep link format: t.me/BotUsername?start=bot_id_user_id
    backup_bot_link = f"https://t.me/{backup_bot_username}?start={bot_id}_{user_id}"
    channel_link = f"https://t.me/{channel.replace('@', '')}"

    keyboard = [
        [InlineKeyboardButton(f"📢 {step1_button}", url=channel_link)],
        [InlineKeyboardButton(f"🤖 {step2_button}", url=backup_bot_link)],
        [InlineKeyboardButton(f"✅ {verify_button}", callback_data="onboarding_verify")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send or edit message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def handle_onboarding_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verify that user has completed both onboarding steps.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    query = update.callback_query
    user_id = update.effective_user.id

    logger.info(f"[ONBOARDING] handle_onboarding_verify called for user {user_id}")

    bot_id = config.BOT_ID if config else 'default_bot'
    channel = config.REQUIRED_CHANNEL if config else '@zuiqiangtuoyi'

    # Check step 1: Channel membership
    channel_ok = await check_channel_membership(context.bot, user_id, channel)
    logger.info(f"[ONBOARDING] User {user_id} channel_ok={channel_ok}")

    if not channel_ok:
        error_msg = translation_service.get(user_id, 'onboarding.error_channel') if translation_service else (
            f"Please follow {channel} first so you won't lose us!"
        )
        await query.answer(error_msg, show_alert=True)
        return

    # Check step 2: Backup bot started
    backup_ok = check_backup_bot_started(user_id, bot_id)
    logger.info(f"[ONBOARDING] User {user_id} backup_ok={backup_ok}")

    if not backup_ok:
        backup_bot_username = config.BACKUP_BOT_USERNAME if config else 'HumanityBackupBot'
        error_msg = translation_service.get(user_id, 'onboarding.error_backup_bot') if translation_service else (
            f"Please start @{backup_bot_username} first - this ensures we can always reach you!"
        )
        await query.answer(error_msg, show_alert=True)
        return

    # Both steps completed - mark onboarding as complete
    logger.info(f"[ONBOARDING] User {user_id} passed both checks, marking complete")
    database_service.mark_onboarding_complete(user_id)

    success_msg = translation_service.get(user_id, 'onboarding.success') if translation_service else (
        "You're all set! You'll never lose access to us now. Enjoy!"
    )
    success_instruction = translation_service.get(user_id, 'onboarding.success_instruction') if translation_service else (
        "Please select a feature from the main menu."
    )

    logger.info(f"[ONBOARDING] User {user_id} completed onboarding, success_msg={success_msg}")

    # Answer the callback first
    await query.answer("✅")

    try:
        # Show success message
        await query.edit_message_text(
            f"✅ {success_msg}\n\n_{success_instruction}_",
            parse_mode='Markdown'
        )
        logger.info(f"[ONBOARDING] User {user_id} success message sent")
    except Exception as e:
        logger.error(f"[ONBOARDING] Error editing message for user {user_id}: {e}")
        # Try sending a new message instead
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ {success_msg}\n\n_{success_instruction}_",
                parse_mode='Markdown'
            )
            logger.info(f"[ONBOARDING] User {user_id} success message sent as new message")
        except Exception as e2:
            logger.error(f"[ONBOARDING] Error sending new message for user {user_id}: {e2}")


async def handle_image_processing_after_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Show image processing UI after successful onboarding verification.
    This sends a new message instead of editing since we're coming from a callback.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from datetime import datetime
    import pytz

    # Get injected services from menu_handlers
    from handlers import menu_handlers
    credit_service = menu_handlers.credit_service
    state_manager = menu_handlers.state_manager

    # Check trial status for undress style
    has_trial = await credit_service.has_free_trial(user_id)

    # Get translated button text
    if translation_service:
        bra_button = translation_service.get(user_id, 'image.style_bra_button')
        back_button = translation_service.get(user_id, 'buttons.back_to_menu')
        style_selection_text = translation_service.get(user_id, 'image.style_selection')
    else:
        bra_button = "🎁 粉红蕾丝内衣 ✨永久免费✨"
        back_button = "🏠 返回主菜单"
        style_selection_text = "🎨 选择脱衣风格"

    # Build undress button based on trial status
    if has_trial:
        if translation_service:
            undress_button = "🎁 " + translation_service.get(user_id, 'image.style_undress_name') + " ✨FREE✨"
        else:
            undress_button = "🎁 全脱光 ✨免费体验✨"
    else:
        if translation_service:
            undress_button = translation_service.get(user_id, 'image.style_undress_button')
        else:
            undress_button = "全脱光 (10积分)"

    keyboard = [
        [InlineKeyboardButton(bra_button, callback_data="style_image_bra")],
        [InlineKeyboardButton(undress_button, callback_data="style_image_undress")],
        [InlineKeyboardButton(back_button, callback_data="back_to_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send as a new message
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=style_selection_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_video_processing_after_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """
    Show video processing UI after successful onboarding verification.
    This sends a new message instead of editing since we're coming from a callback.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Get translated content
    if translation_service:
        style_selection_text = translation_service.get(user_id, 'video.style_selection')
        style_a_button = translation_service.get(user_id, 'video.style_a_button')
        style_b_button = translation_service.get(user_id, 'video.style_b_button')
        style_c_button = translation_service.get(user_id, 'video.style_c_button')
        back_button = translation_service.get(user_id, 'buttons.back_to_menu')
    else:
        style_selection_text = "🎬 选择视频风格"
        style_a_button = "脱衣+晃胸 (30积分)"
        style_b_button = "脱衣+流水 (30积分)"
        style_c_button = "脱衣+露骨 (30积分)"
        back_button = "🏠 返回主菜单"

    keyboard = [
        [InlineKeyboardButton(style_a_button, callback_data="style_video_a")],
        [InlineKeyboardButton(style_b_button, callback_data="style_video_b")],
        [InlineKeyboardButton(style_c_button, callback_data="style_video_c")],
        [InlineKeyboardButton(back_button, callback_data="back_to_menu")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=style_selection_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


def is_onboarding_required(user_id: int) -> bool:
    """
    Check if user needs to complete onboarding.

    Args:
        user_id: User ID to check

    Returns:
        True if onboarding is required (not completed)
    """
    return not database_service.is_onboarding_complete(user_id)
