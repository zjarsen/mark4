"""Command handlers for /start, /help, etc."""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from core.constants import (
    WELCOME_MESSAGE,
    SELECT_FUNCTION_MESSAGE,
    MENU_OPTION_IMAGE,
    MENU_OPTION_VIDEO,
    MENU_OPTION_CHECK_QUEUE,
    MENU_OPTION_BALANCE_HISTORY,
    MENU_OPTION_TOPUP
)

logger = logging.getLogger('mark4_bot')

# These will be injected by bot_application.py
state_manager = None
config = None
credit_service = None
translation_service = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command with language selection for new users.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # Check if user has language preference set
        db = context.bot_data.get('database_service')
        user_lang = db.get_user_language(user_id) if db else 'zh_CN'

        # First-time user with no language set: Show language selection
        if user_lang is None or user_lang == '' or (user_lang == 'zh_CN' and db and not db.get_user(user_id).get('telegram_username')):
            # Check if this is truly a new user (no telegram_username means get_user just created them)
            user_data = db.get_user(user_id) if db else None
            if user_data and not user_data.get('telegram_username'):
                from handlers.language_handlers import show_language_selection
                await show_language_selection(update, context, is_first_time=True)
                return

        # Existing user: Show welcome message in their language
        if not state_manager.has_state(user_id):
            # Get translated welcome message and button text
            if translation_service:
                welcome_msg = translation_service.get(user_id, 'welcome.message')
                lucky_button = translation_service.get(user_id, 'welcome.lucky_discount_button')
            else:
                # Fallback to Chinese if translation service not available
                welcome_msg = WELCOME_MESSAGE
                lucky_button = "🎁 立即抽取幸运折扣"

            # Create inline keyboard with button to open topup menu
            keyboard = [[InlineKeyboardButton(lucky_button, callback_data="open_topup_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                welcome_msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            state_manager.set_state(user_id, {'first_contact': True})

        # Show main menu
        await show_main_menu(update)

        logger.info(f"Start command processed for user {user_id}")

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        raise


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        if translation_service:
            help_text = translation_service.get(user_id, 'help.text')
        else:
            help_text = """📖 使用帮助\n\n1️⃣ 图片脱衣\n   - 点击按钮后发送照片\n   - 支持格式：PNG, JPG, JPEG, WEBP\n   - 等待处理完成\n\n2️⃣ 图片转视频脱衣\n   - 功能开发中\n\n3️⃣ 查看队列\n   - 查看当前排队人数\n\n⏱️ 处理完成后，请在5分钟内保存图片。\n\n❓ 如有问题，请联系管理员。"""

        await update.message.reply_text(help_text)

        logger.info(f"Help command processed for user {user_id}")

    except Exception as e:
        logger.error(f"Error in help command: {str(e)}")
        raise


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /cancel command - cancel current operation.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # Get workflow_service from context
        workflow_service = context.bot_data.get('workflow_service')

        if workflow_service:
            cancelled = await workflow_service.cancel_user_workflow(user_id)

            if cancelled:
                if translation_service:
                    msg = translation_service.get(user_id, 'commands.cancel_success')
                else:
                    msg = "操作已取消"
                await update.message.reply_text(msg)
                logger.info(f"Cancelled workflow for user {user_id}")
            else:
                if translation_service:
                    msg = translation_service.get(user_id, 'commands.cancel_no_operation')
                else:
                    msg = "没有进行中的操作"
                await update.message.reply_text(msg)
        else:
            if translation_service:
                msg = translation_service.get(user_id, 'commands.cancel_failed')
            else:
                msg = "无法取消操作"
            await update.message.reply_text(msg)

        # Show menu
        await show_main_menu(update)

    except Exception as e:
        logger.error(f"Error in cancel command: {str(e)}")
        if translation_service:
            msg = translation_service.get(user_id, 'commands.cancel_failed')
        else:
            msg = "取消操作失败"
        await update.message.reply_text(msg)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /status command - show user status.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id
        state = state_manager.get_state(user_id)

        if not state:
            if translation_service:
                msg = translation_service.get(user_id, 'commands.status_idle')
            else:
                msg = "当前没有进行中的操作"
            await update.message.reply_text(msg)
            return

        current_state = state.get('state', 'idle')
        prompt_id = state.get('prompt_id', 'N/A')

        if translation_service:
            status_text = translation_service.get(
                user_id,
                'commands.status_text',
                current_state=current_state,
                prompt_id=prompt_id
            )
        else:
            status_text = f"""📊 当前状态\n\n状态: {current_state}\n任务ID: {prompt_id}"""

        await update.message.reply_text(status_text)

        logger.info(f"Status command processed for user {user_id}")

    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /language command to change language.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        from handlers.language_handlers import show_language_selection
        await show_language_selection(update, context, is_first_time=False)
        logger.info(f"Language command processed for user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error in language command: {str(e)}")


async def show_main_menu(update: Update):
    """
    Show main menu keyboard to user with translated text.

    Args:
        update: Telegram Update
    """
    user_id = update.effective_user.id

    # Get translated menu options
    if translation_service:
        option_image = translation_service.get(user_id, 'menu.option_image')
        option_video = translation_service.get(user_id, 'menu.option_video')
        option_topup = translation_service.get(user_id, 'menu.option_topup')
        option_balance = translation_service.get(user_id, 'menu.option_balance')
        option_queue = translation_service.get(user_id, 'menu.option_queue')
        option_language = translation_service.get(user_id, 'menu.option_language')
        message_text = translation_service.get(user_id, 'menu.select_function') or "·"
    else:
        # Fallback to Chinese constants
        option_image = MENU_OPTION_IMAGE
        option_video = MENU_OPTION_VIDEO
        option_topup = MENU_OPTION_TOPUP
        option_balance = MENU_OPTION_BALANCE_HISTORY
        option_queue = MENU_OPTION_CHECK_QUEUE
        option_language = "6. 🌍 更换语言"
        message_text = SELECT_FUNCTION_MESSAGE if SELECT_FUNCTION_MESSAGE else "·"

    keyboard = [
        [KeyboardButton(option_image), KeyboardButton(option_video)],
        [KeyboardButton(option_topup)],
        [KeyboardButton(option_balance)],
        [KeyboardButton(option_queue), KeyboardButton(option_language)]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )


async def admin_topup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle admin top-up backdoor for testing accounts.
    Checks if message matches admin password and tops up credits.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        # Check if message text matches admin password
        if not update.message or not update.message.text:
            return

        message_text = update.message.text.strip()

        # Check if admin password is configured and matches
        if not config or not config.ADMIN_TOPUP_PASSWORD:
            return

        if message_text == config.ADMIN_TOPUP_PASSWORD:
            user_id = update.effective_user.id

            # Add credits using credit service
            if credit_service:
                success, new_balance = await credit_service.add_credits(
                    user_id,
                    config.ADMIN_TOPUP_AMOUNT,
                    description="管理员测试充值",
                    reference_id=f"admin_topup_{user_id}"
                )

                if success:
                    if translation_service:
                        msg = translation_service.get(user_id, 'commands.admin_topup_success')
                    else:
                        msg = "管理员已充值"
                    await update.message.reply_text(msg)
                    logger.info(
                        f"Admin top-up: Added {config.ADMIN_TOPUP_AMOUNT} credits to user {user_id}, "
                        f"new balance: {new_balance}"
                    )
                else:
                    logger.error(f"Failed to process admin top-up for user {user_id}")
            else:
                logger.error("Credit service not available for admin top-up")

    except Exception as e:
        logger.error(f"Error in admin top-up handler: {str(e)}")
