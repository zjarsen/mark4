"""Command handlers for /start, /help, etc."""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# These will be injected by bot_application.py
state_manager = None
config = None
credit_service = None
translation_service = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - always show language selection.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # Always show language selection for /start
        from handlers.language_handlers import show_language_selection

        # Check if user is new or existing
        db = context.bot_data.get('database_service')
        user_data = db.get_user(user_id) if db else None
        is_first_time = user_data and not user_data.get('telegram_username')

        await show_language_selection(update, context, is_first_time=is_first_time)

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
                msg = "取消操作失败"
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


def _get_main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard with translated text.

    Args:
        user_id: User ID for translation

    Returns:
        ReplyKeyboardMarkup with menu options
    """
    # Get translated menu options
    if translation_service:
        option_image = translation_service.get(user_id, 'menu.option_image')
        option_video = translation_service.get(user_id, 'menu.option_video')
        option_topup = translation_service.get(user_id, 'menu.option_topup')
        option_balance = translation_service.get(user_id, 'menu.option_balance')
        option_queue = translation_service.get(user_id, 'menu.option_queue')
    else:
        # Fallback to Chinese
        option_image = "1. 📸 图生图类脱衣！✨"
        option_video = "2. 🎬 图生成视频类脱衣！✨"
        option_topup = "3. 💳 充值积分 🎁 每日抽最高5折！"
        option_balance = "4. 📊 积分余额 & 充值记录"
        option_queue = "5. 查看当前队列"

    # Language option always in English for universal recognition
    option_language = "6. 🌍 Language"

    keyboard = [
        [KeyboardButton(option_image), KeyboardButton(option_video)],
        [KeyboardButton(option_topup)],
        [KeyboardButton(option_balance)],
        [KeyboardButton(option_queue), KeyboardButton(option_language)]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def show_main_menu(update: Update):
    """
    Show main menu keyboard to user with translated text.

    Args:
        update: Telegram Update
    """
    user_id = update.effective_user.id

    # Get translated menu message (use pointing up emoji if empty)
    if translation_service:
        message_text = translation_service.get(user_id, 'menu.select_function')
        if not message_text or message_text.strip() == '':
            message_text = '👆'
    else:
        message_text = ""  # Empty string fallback (Chinese constant was empty)

    reply_markup = _get_main_menu_keyboard(user_id)

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
                description_text = translation_service.get(user_id, 'admin.topup_description') if translation_service else "管理员测试充值"
                success, new_balance = await credit_service.add_credits(
                    user_id,
                    config.ADMIN_TOPUP_AMOUNT,
                    description=description_text,
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
