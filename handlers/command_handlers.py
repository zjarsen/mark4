"""Command handlers for /start, /help, etc."""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        user_id = update.effective_user.id

        # First-time welcome message
        if not state_manager.has_state(user_id):
            await update.message.reply_text(WELCOME_MESSAGE)
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
        help_text = """
📖 使用帮助

1️⃣ 图片脱衣
   - 点击按钮后发送照片
   - 支持格式：PNG, JPG, JPEG, WEBP
   - 等待处理完成

2️⃣ 图片转视频脱衣
   - 功能开发中

3️⃣ 查看队列
   - 查看当前排队人数

⏱️ 处理完成后，请在5分钟内保存图片。

❓ 如有问题，请联系管理员。
"""

        await update.message.reply_text(help_text)

        logger.info(f"Help command processed for user {update.effective_user.id}")

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
                await update.message.reply_text("操作已取消")
                logger.info(f"Cancelled workflow for user {user_id}")
            else:
                await update.message.reply_text("没有进行中的操作")
        else:
            await update.message.reply_text("无法取消操作")

        # Show menu
        await show_main_menu(update)

    except Exception as e:
        logger.error(f"Error in cancel command: {str(e)}")
        await update.message.reply_text("取消操作失败")


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
            await update.message.reply_text("当前没有进行中的操作")
            return

        current_state = state.get('state', 'idle')
        prompt_id = state.get('prompt_id', 'N/A')

        status_text = f"""
📊 当前状态

状态: {current_state}
任务ID: {prompt_id}
"""

        await update.message.reply_text(status_text)

        logger.info(f"Status command processed for user {user_id}")

    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")


async def show_main_menu(update: Update):
    """
    Show main menu keyboard to user with dynamic text based on trial availability.

    Args:
        update: Telegram Update
    """
    user_id = update.effective_user.id

    # Dynamically generate image processing menu text based on trial availability
    image_option = MENU_OPTION_IMAGE
    if credit_service:
        try:
            has_trial = await credit_service.has_free_trial(user_id)
            if has_trial:
                image_option = "1. 图片脱衣（免费可用）"
            else:
                image_option = "1. 图片脱衣（花费10积分）"
        except Exception as e:
            logger.error(f"Error checking trial availability: {e}")
            # Fallback to default text on error

    keyboard = [
        [KeyboardButton(image_option)],
        [KeyboardButton(MENU_OPTION_VIDEO)],
        [KeyboardButton(MENU_OPTION_CHECK_QUEUE)],
        [KeyboardButton(MENU_OPTION_BALANCE_HISTORY)],
        [KeyboardButton(MENU_OPTION_TOPUP)]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    await update.message.reply_text(
        SELECT_FUNCTION_MESSAGE,
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
                    await update.message.reply_text("管理员已充值")
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
