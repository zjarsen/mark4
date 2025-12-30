"""Handlers for language selection."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger('mark4_bot')

# Will be injected by bot_application
translation_service = None


async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, is_first_time: bool = False):
    """
    Show language selection menu.

    Args:
        update: Telegram Update
        context: Telegram Context
        is_first_time: Whether this is the first time the user is selecting a language
    """
    try:
        keyboard = [
            [InlineKeyboardButton("🇨🇳 简体中文", callback_data="lang_zh_CN"),
             InlineKeyboardButton("🇺🇸 English", callback_data="lang_en_US")],
            [InlineKeyboardButton("🇹🇼 繁體中文", callback_data="lang_zh_TW"),
             InlineKeyboardButton("🇯🇵 日本語", callback_data="lang_ja_JP")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar_SA"),
             InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_hi_IN")],
            [InlineKeyboardButton("🇮🇩 Bahasa Indonesia", callback_data="lang_id_ID"),
             InlineKeyboardButton("🇰🇷 한국어", callback_data="lang_ko_KR")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        title = "🌍 选择您的语言 / Choose Your Language"
        subtitle = "\n请选择您偏好的语言，设置后可随时更改" if is_first_time else ""

        if update.message:
            await update.message.reply_text(f"{title}{subtitle}", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(f"{title}{subtitle}", reply_markup=reply_markup)

        logger.info(f"Language selection shown to user {update.effective_user.id if update.effective_user else 'unknown'}")

    except Exception as e:
        logger.error(f"Error showing language selection: {str(e)}")
        raise


async def handle_language_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle language selection callback.

    Args:
        update: Telegram Update
        context: Telegram Context
    """
    try:
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        lang_code = query.data.replace("lang_", "")

        # Store language preference in database
        db = context.bot_data.get('database_service')
        if db:
            success = db.set_user_language(user_id, lang_code)
            if not success:
                logger.error(f"Failed to set language for user {user_id}")
                await query.edit_message_text("❌ Error setting language. Please try again.")
                return
        else:
            logger.error("Database service not available")
            await query.edit_message_text("❌ Database service not available.")
            return

        # Get language name in selected language
        if translation_service:
            lang_name = translation_service.get_lang(lang_code, 'language.name')
            success_msg = translation_service.get_lang(lang_code, 'language_selection.success', language_name=lang_name)
        else:
            success_msg = f"✅ Language set to {lang_code}"

        await query.edit_message_text(success_msg)
        logger.info(f"User {user_id} selected language: {lang_code}")

        # Show welcome message in selected language
        # Import here to avoid circular dependency
        from handlers.command_handlers import start

        # Create a temporary update with a message (since callback_query doesn't have message)
        # We'll simulate a /start command
        import asyncio
        await asyncio.sleep(1)  # Brief pause before showing welcome

        # Show main menu in new language
        from handlers.command_handlers import show_main_menu

        # Create temporary message object for show_main_menu
        class TempMessage:
            async def reply_text(self, text, **kwargs):
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text, **kwargs)

        class TempUpdate:
            def __init__(self, user_id, chat_id, msg):
                self.effective_user = type('obj', (object,), {'id': user_id})
                self.effective_chat = type('obj', (object,), {'id': chat_id})
                self.message = msg

        temp_update = TempUpdate(user_id, update.effective_chat.id, TempMessage())

        # Show welcome message
        if translation_service:
            welcome_msg = translation_service.get(user_id, 'welcome.message')
            lucky_button_text = translation_service.get(user_id, 'welcome.lucky_discount_button')
        else:
            welcome_msg = "Welcome!"
            lucky_button_text = "Lucky Discount"

        keyboard = [[InlineKeyboardButton(lucky_button_text, callback_data="open_topup_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_msg,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        # Show main menu
        await show_main_menu(temp_update)

    except Exception as e:
        logger.error(f"Error handling language selection: {str(e)}")
        try:
            await update.callback_query.edit_message_text("❌ Error processing language selection. Please try /start again.")
        except:
            pass
