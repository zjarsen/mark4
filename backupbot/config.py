"""Configuration for Backup Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration for the backup bot."""

    # Bot Configuration
    BOT_TOKEN = os.getenv('BACKUP_BOT_TOKEN', '8511703907:AAFrblkrogz82MDFqlnhy3VQKhuZ38Avlf4')

    # Database Configuration - uses shared database with main bot
    # Path is relative to backupbot/ folder, so we need to go up one level
    DATABASE_PATH = os.getenv('DATABASE_PATH', '../data/mark4_bot.db')

    @classmethod
    def get_database_path(cls):
        """Get absolute path to database."""
        from pathlib import Path
        # If it's an absolute path, use it directly
        if os.path.isabs(cls.DATABASE_PATH):
            return cls.DATABASE_PATH
        # Otherwise resolve relative to this config file's parent's parent (main bot dir)
        config_dir = Path(__file__).parent  # backupbot/
        return str((config_dir.parent / 'data' / 'mark4_bot.db').resolve())

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
