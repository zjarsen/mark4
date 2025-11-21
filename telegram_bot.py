#!/usr/bin/env python3
"""
Mark4 Telegram Bot - Entry Point

A modular Telegram bot for image processing with ComfyUI integration.
"""

from core.bot_application import BotApplication
from config import Config
from utils.logger import setup_logger


def main():
    """Main entry point for the bot."""
    # Load and validate configuration
    try:
        config = Config()
        print("✅ Configuration loaded successfully")

    except ValueError as e:
        print(f"❌ Configuration error: {str(e)}")
        print("💡 Make sure BOT_TOKEN is set in .env file")
        return

    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")
        return

    # Setup logging
    try:
        logger = setup_logger(config.LOG_LEVEL, config.LOG_FILE)
        logger.info("=" * 60)
        logger.info("Mark4 Telegram Bot Starting")
        logger.info("=" * 60)

    except Exception as e:
        print(f"⚠️  Logging setup failed: {str(e)}")
        print("Continuing without logging...")

    # Create and run bot
    try:
        bot = BotApplication(config)
        bot.run()

    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user (Ctrl+C)")

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        if logger:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
