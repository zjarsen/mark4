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

# Demo video links (technical URLs)
DEMO_LINK_BRA = "https://t.me/zuiqiangtuoyi/25"
DEMO_LINK_UNDRESS = "https://t.me/zuiqiangtuoyi/29"

# Payment timeout duration (in seconds)
PAYMENT_TIMEOUT_SECONDS = 180  # 3 minutes

# Workflow file names
WORKFLOW_IMAGE_PROCESSING = "i2i_undress_final_v5.json"

# Image workflow file names
WORKFLOW_IMAGE_STYLE_BRA = "i2i_bra_v5.json"
WORKFLOW_IMAGE_STYLE_UNDRESS = "i2i_undress_final_v5.json"

WORKFLOW_VIDEO_PROCESSING = "video_processing.json"  # Future
WORKFLOW_I2I_OLD = "i2i_1.json"  # Old workflow (deprecated)

# Video workflow file names
WORKFLOW_VIDEO_STYLE_A = "i2v_undress_douxiong.json"
WORKFLOW_VIDEO_STYLE_B = "i2v_undress_liujing.json"
WORKFLOW_VIDEO_STYLE_C = "i2v_undress_shejing.json"

# Node IDs in workflows
NODE_LOAD_IMAGE = "7"  # Image workflow
NODE_SAVE_IMAGE = "27"  # Image workflow
NODE_LOAD_IMAGE_VIDEO = "267"  # Video workflows
NODE_SAVE_VIDEO = "245"  # Video workflows

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
