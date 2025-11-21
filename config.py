"""Configuration management for Mark4 Telegram Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration with environment variable support."""

    # Base directory
    BASE_DIR = Path(__file__).parent

    # Telegram Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'declothing_free1_bot')

    # ComfyUI Server Configuration
    COMFYUI_SERVER = os.getenv('COMFYUI_SERVER', 'http://20.196.153.126:8188')

    # Computed URLs
    @property
    def COMFYUI_UPLOAD_URL(self):
        return f"{self.COMFYUI_SERVER}/api/upload/image"

    @property
    def COMFYUI_PROMPT_URL(self):
        return f"{self.COMFYUI_SERVER}/prompt"

    @property
    def COMFYUI_QUEUE_URL(self):
        return f"{self.COMFYUI_SERVER}/queue"

    @property
    def COMFYUI_HISTORY_URL(self):
        return f"{self.COMFYUI_SERVER}/history"

    @property
    def COMFYUI_VIEW_URL(self):
        return f"{self.COMFYUI_SERVER}/view"

    # Directory Configuration
    USER_UPLOADS_DIR = Path(
        os.getenv('USER_UPLOADS_DIR', '~/mark4/user_uploads')
    ).expanduser()

    COMFYUI_RETRIEVE_DIR = Path(
        os.getenv('COMFYUI_RETRIEVE_DIR', '~/mark4/comfyui_retrieve')
    ).expanduser()

    WORKFLOWS_DIR = Path(
        os.getenv('WORKFLOWS_DIR', '~/mark4/workflows')
    ).expanduser()

    # Processing Configuration
    CLEANUP_TIMEOUT = int(os.getenv('CLEANUP_TIMEOUT', '300'))  # 5 minutes in seconds
    QUEUE_POLL_INTERVAL = int(os.getenv('QUEUE_POLL_INTERVAL', '5'))  # seconds
    MAX_RETRY_COUNT = int(os.getenv('MAX_RETRY_COUNT', '3'))

    # File Configuration
    ALLOWED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'webp']

    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE')  # Optional: path to log file

    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/mark4_bot.db')

    # Payment Configuration (WeChat/Alipay 3rd party acquirer)
    PAYMENT_GATEWAY_URL = os.getenv('PAYMENT_GATEWAY_URL')  # Base URL for payment gateway
    PAYMENT_MERCHANT_ID = os.getenv('PAYMENT_MERCHANT_ID')  # pay_memberid
    PAYMENT_SECRET_KEY = os.getenv('PAYMENT_SECRET_KEY')    # Secret key for MD5 signing
    PAYMENT_NOTIFY_URL = os.getenv('PAYMENT_NOTIFY_URL')    # Server callback URL (pay_notifyurl)
    PAYMENT_CALLBACK_URL = os.getenv('PAYMENT_CALLBACK_URL')  # User return URL (pay_callbackurl)
    PAYMENT_BANKCODE_WECHAT = os.getenv('PAYMENT_BANKCODE_WECHAT', '998')  # Bank code for WeChat
    PAYMENT_BANKCODE_ALIPAY = os.getenv('PAYMENT_BANKCODE_ALIPAY', '999')  # Bank code for Alipay

    def __init__(self):
        """Initialize configuration and validate required settings."""
        self.validate()
        self._ensure_directories()

    def validate(self):
        """Validate required configuration values."""
        if not self.BOT_TOKEN:
            raise ValueError(
                "BOT_TOKEN is required. Please set it in .env file or environment variables."
            )
        return True

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.USER_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.COMFYUI_RETRIEVE_DIR.mkdir(parents=True, exist_ok=True)
        self.WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        """String representation of config (without sensitive data)."""
        return (
            f"Config(bot_username={self.BOT_USERNAME}, "
            f"comfyui_server={self.COMFYUI_SERVER})"
        )
