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

    # ComfyUI Server Configuration - Workflow-specific servers
    COMFYUI_IMAGE_UNDRESS_SERVER = os.getenv('COMFYUI_IMAGE_UNDRESS_SERVER')
    COMFYUI_IMAGE_BRA_SERVER = os.getenv('COMFYUI_IMAGE_BRA_SERVER')
    COMFYUI_VIDEO_DOUXIONG_SERVER = os.getenv('COMFYUI_VIDEO_DOUXIONG_SERVER')
    COMFYUI_VIDEO_LIUJING_SERVER = os.getenv('COMFYUI_VIDEO_LIUJING_SERVER')
    COMFYUI_VIDEO_SHEJING_SERVER = os.getenv('COMFYUI_VIDEO_SHEJING_SERVER')

    # Helper method to get workflow server URLs
    def get_workflow_urls(self, workflow_type: str):
        """
        Get all ComfyUI URLs for a specific workflow type.

        Args:
            workflow_type: One of 'image_undress', 'image_bra', 'video_douxiong', 'video_liujing', 'video_shejing'

        Returns:
            Dict with upload_url, prompt_url, queue_url, history_url, view_url
        """
        server_map = {
            'image_undress': self.COMFYUI_IMAGE_UNDRESS_SERVER,
            'image_bra': self.COMFYUI_IMAGE_BRA_SERVER,
            'video_douxiong': self.COMFYUI_VIDEO_DOUXIONG_SERVER,
            'video_liujing': self.COMFYUI_VIDEO_LIUJING_SERVER,
            'video_shejing': self.COMFYUI_VIDEO_SHEJING_SERVER
        }

        server = server_map.get(workflow_type)
        if not server:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        return {
            'upload_url': f"{server}/api/upload/image",
            'prompt_url': f"{server}/prompt",
            'queue_url': f"{server}/queue",
            'history_url': f"{server}/history",
            'view_url': f"{server}/view"
        }

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

    # Admin Testing Configuration
    ADMIN_TOPUP_PASSWORD = os.getenv('ADMIN_TOPUP_PASSWORD')  # Admin password for testing top-ups
    ADMIN_TOPUP_AMOUNT = int(os.getenv('ADMIN_TOPUP_AMOUNT', '100000'))  # Credits to add for admin top-up

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
            f"workflows=4)"
        )
