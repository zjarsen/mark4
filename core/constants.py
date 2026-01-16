"""Constants and enumerations for the bot."""

from enum import Enum


class UserState(Enum):
    """User state enumeration."""
    IDLE = "idle"
    WAITING_FOR_IMAGE = "waiting_for_image"
    PROCESSING = "processing"
    WAITING_FOR_PAYMENT = "waiting_for_payment"
    WAITING_FOR_VIDEO = "waiting_for_video"
    WAITING_FOR_CREDIT_CONFIRMATION = "waiting_for_credit_confirmation"


class WorkflowType(Enum):
    """Workflow type enumeration."""
    IMAGE_PROCESSING = "image_processing"
    VIDEO_PROCESSING = "video_processing"
    BATCH_PROCESSING = "batch_processing"


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


# ============================================================================
# NOTE: User-facing text has been moved to translation files (locales/*.json)
# Only technical constants remain below.
# ============================================================================

# Payment timeout duration (in seconds)
PAYMENT_TIMEOUT_SECONDS = 180  # 3 minutes

# Node IDs in workflows
NODE_LOAD_IMAGE = "7"       # i2i workflows - input node
NODE_SAVE_IMAGE = "27"      # i2i workflows - output node
NODE_LOAD_IMAGE_VIDEO = "267"  # i2v workflows - input node
NODE_SAVE_VIDEO = "245"     # i2v workflows - output node

# Note: Workflow files and style config are now in core/styles.py

# Top-up packages (amount in CNY: credits)
TOPUP_PACKAGES = {
    10: 30,         # ¥10 = 30积分
    30: 120,        # ¥30 = 120积分
    50: 250,        # ¥50 = 250积分
    100: 600,       # ¥100 = 600积分
    160: 99999999,  # ¥160 = 永久VIP (unlimited credits)
    260: 99999999   # ¥260 = 永久黑金VIP (unlimited credits)
}

# Daily Lucky Discount System
# Note: 'display' names moved to translation files (discount.tier_ssr, etc.)
DISCOUNT_TIERS = {
    'SSR': {'rate': 0.5, 'emoji': '🎊', 'off': '50'},
    'SR': {'rate': 0.7, 'emoji': '🎉', 'off': '30'},
    'R': {'rate': 0.85, 'emoji': '✨', 'off': '15'},
    'C': {'rate': 0.95, 'emoji': '🍀', 'off': '5'}
}
