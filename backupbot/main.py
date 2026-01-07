"""
Backup Bot - Tracks users for notification purposes.

This bot is used to track users who want to stay connected.
When a user starts this bot via a deep link from the main bot,
we record their user_id and source_bot_id in the shared database.
"""

import logging
import sqlite3
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import Config

# Add parent directory to path to import from main bot
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger('backup_bot')


class DatabaseService:
    """Simple database service for backup bot."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _ensure_table(self):
        """Ensure the backup_bot_users table exists."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_bot_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    source_bot_id TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, source_bot_id)
                )
            """)
            conn.commit()
            conn.close()
            logger.info("Database table ensured")
        except Exception as e:
            logger.error(f"Error ensuring table: {e}")

    def record_user_start(self, user_id: int, source_bot_id: str) -> bool:
        """Record that a user started this bot from a specific source."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO backup_bot_users (user_id, source_bot_id)
                VALUES (?, ?)
            """, (user_id, source_bot_id))
            conn.commit()
            conn.close()
            logger.info(f"Recorded user {user_id} from {source_bot_id}")
            return True
        except Exception as e:
            logger.error(f"Error recording user start: {e}")
            return False

    def get_user_language(self, user_id: int) -> str:
        """Get user's language preference from the main bot's users table."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT language FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            if result and result[0]:
                return result[0]
            return 'zh_CN'  # Default language
        except Exception as e:
            logger.error(f"Error getting user language: {e}")
            return 'zh_CN'


# Initialize database using config helper
db_path = Config.get_database_path()
logger.info(f"Using database path: {db_path}")
db = DatabaseService(db_path)

# Initialize TranslationService
# Use the locales from the main bot
locales_dir = Path(__file__).parent.parent / 'locales'
logger.info(f"Using locales directory: {locales_dir}")

from services.translation_service import TranslationService
translation_service = TranslationService(db, str(locales_dir), default_lang='zh_CN')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional deep link payload."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"

    # Check for deep link payload: format is "botid_userid"
    if context.args and len(context.args) > 0:
        payload = context.args[0]
        logger.info(f"Received start with payload: {payload}")

        # Parse payload: expected format is "source_bot_id_user_id"
        # e.g., "cn_bot_123456789"
        parts = payload.rsplit('_', 1)  # Split from right to get bot_id and user_id
        if len(parts) == 2:
            source_bot_id = parts[0]
            try:
                payload_user_id = int(parts[1])
                # Verify the user_id matches (security check)
                if payload_user_id == user_id:
                    db.record_user_start(user_id, source_bot_id)
                    logger.info(f"Verified and recorded user {user_id} from {source_bot_id}")
                else:
                    logger.warning(f"User ID mismatch: payload={payload_user_id}, actual={user_id}")
                    # Still record it but with actual user_id
                    db.record_user_start(user_id, source_bot_id)
            except ValueError:
                logger.warning(f"Invalid user_id in payload: {parts[1]}")
                # Just record with the source_bot_id
                db.record_user_start(user_id, payload)
        else:
            # Payload doesn't match expected format, just use it as source_bot_id
            db.record_user_start(user_id, payload)

    # Send welcome message in user's language
    welcome_message = translation_service.get(user_id, 'backup_bot.welcome', name=user_name)
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    help_text = translation_service.get(user_id, 'backup_bot.help')
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def main():
    """Start the bot."""
    logger.info("Starting Backup Bot...")

    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Initialize and start
    await application.initialize()
    await application.start()
    logger.info("Bot is running...")

    # Start polling
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Run until stopped
    import signal
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await stop_event.wait()

    # Cleanup
    await application.updater.stop()
    await application.stop()
    await application.shutdown()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
