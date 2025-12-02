"""Constants and enumerations for the bot."""

from enum import Enum


class UserState(Enum):
    """User state enumeration."""
    IDLE = "idle"
    WAITING_FOR_IMAGE = "waiting_for_image"
    PROCESSING = "processing"
    WAITING_FOR_PAYMENT = "waiting_for_payment"
    WAITING_FOR_VIDEO = "waiting_for_video"


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


# Menu text constants
MENU_OPTION_IMAGE = "1. 图片脱衣"
MENU_OPTION_VIDEO = "2. 图片转视频脱衣（花费30积分）"
MENU_OPTION_CHECK_QUEUE = "3. 查看队列"
MENU_OPTION_BALANCE_HISTORY = "4. 📊 积分余额 & 充值记录"
MENU_OPTION_TOPUP = "5. 💳 充值积分"

# Message templates
WELCOME_MESSAGE = """欢迎使用AI脱衣bot！

🎁 新用户福利：每2天可免费体验1次图片脱衣功能

使用说明：
选择"图片脱衣"，上传一张正脸照片（可半身或全身），AI会自动处理。

后续使用需要积分，可随时充值。"""

SELECT_FUNCTION_MESSAGE = "请选择功能："
SEND_IMAGE_PROMPT = "请现在向我发送图片"
FEATURE_NOT_IMPLEMENTED = "此功能仍在开发中"
INVALID_FORMAT_MESSAGE = '您发送的文件格式有误，请发送以下图片格式之一："png", "jpg", "jpeg", "webp"'
MAX_RETRY_MESSAGE = "您已尝试3次，请重新开始。"
ALREADY_PROCESSING_MESSAGE = "您上传的图片仍在队列中，请耐心等待"
UPLOAD_FAILED_MESSAGE = "上传失败，请稍后重试"
PROCESSING_COMPLETE_MESSAGE = "处理完成！请在5分钟内尽快储存"
QUEUE_STATUS_TEMPLATE = "已经进入队列，您现在的排队为第{position}位。队列总人数为：{total}\n\n点击 '刷新队列' 看最新排位"
QUEUE_TOTAL_TEMPLATE = "当前队列总人数为：{total}"
PROCESSING_IN_PROGRESS = "处理中..."
PROCESSING_RUNNING = "正在处理您的图片，请稍候..."
PROCESSING_RETRIEVING = "处理完成，正在获取图片..."
QUEUE_UNAVAILABLE = "无法获取队列信息，请稍后再试"
INVALID_STATE_MESSAGE = "请先选择 '1. 图片脱衣' 功能"
UNEXPECTED_INPUT_MESSAGE = "请从菜单中选择一个选项。"
ERROR_MESSAGE = "发生错误，请稍后重试"

# Credit system messages
INSUFFICIENT_CREDITS_MESSAGE = """积分不足！
当前余额：{balance} 积分
所需积分：{required} 积分

请充值后再使用此功能。"""

FREE_TRIAL_MESSAGE = """🎁 免费体验可用！
这是您的免费次数，处理完成后将在2天后重置。

请上传图片开始处理～"""

FREE_TRIAL_AVAILABLE_MESSAGE = """🎁 免费体验可用！
这是您的免费次数，处理完成后将在2天后重置。

请上传图片开始处理～"""

FREE_TRIAL_COOLDOWN_MESSAGE = """免费体验冷却中...
下次可用时间：{next_available}

当前余额：{balance} 积分
本次需要：10 积分

您可以充值积分立即使用，或等待免费次数重置。"""

BALANCE_MESSAGE = """💰 您的积分余额

当前积分：{balance} 积分
累计消费：{total_spent} 积分

图片脱衣：10 积分/次"""

TOPUP_PACKAGES_MESSAGE = """💳 充值套餐

请选择充值套餐：
0️⃣ ¥1 = 2积分
1️⃣ ¥10 = 30积分
2️⃣ ¥30 = 120积分
3️⃣ ¥50 = 250积分
4️⃣ ¥100 = 600积分

充值后积分永久有效，无过期时间限制。"""

TRANSACTION_HISTORY_HEADER = "📊 最近10笔消费记录\n\n"
TRANSACTION_ITEM_TEMPLATE = "{date} | {type} | {amount:+.0f}积分 | 余额:{balance:.0f}\n"
NO_TRANSACTIONS_MESSAGE = "暂无消费记录"

CREDITS_DEDUCTED_MESSAGE = "已扣除 {amount} 积分，当前余额：{balance} 积分"
CREDITS_ADDED_MESSAGE = "充值成功！获得 {amount} 积分，当前余额：{balance} 积分"

PAYMENT_PENDING_MESSAGE = """等待支付中...
⏰ 请在3分钟内完成支付

订单号：{payment_id}
金额：¥{amount}
积分：{credits} 积分

请在新窗口完成支付。"""

PAYMENT_TIMEOUT_MESSAGE = "⏰ 支付超时，请重新选择充值套餐"

PAYMENT_SUCCESS_MESSAGE = "支付成功！已到账 {credits} 积分"
PAYMENT_FAILED_MESSAGE = "支付失败，请重试"

# Payment timeout duration (in seconds)
PAYMENT_TIMEOUT_SECONDS = 180  # 3 minutes

# Button labels
REFRESH_QUEUE_BUTTON = "刷新队列"
TOPUP_1_BUTTON = "¥1 = 2积分"
TOPUP_10_BUTTON = "¥10 = 30积分"
TOPUP_30_BUTTON = "¥30 = 120积分"
TOPUP_50_BUTTON = "¥50 = 250积分"
TOPUP_100_BUTTON = "¥100 = 600积分"

# Workflow file names
WORKFLOW_IMAGE_PROCESSING = "i2i_undress_final.json"
WORKFLOW_VIDEO_PROCESSING = "video_processing.json"  # Future
WORKFLOW_I2I_OLD = "i2i_1.json"  # Old workflow (deprecated)

# Video workflow file names
WORKFLOW_VIDEO_STYLE_A = "video_style_a.json"
WORKFLOW_VIDEO_STYLE_B = "video_style_b.json"
WORKFLOW_VIDEO_STYLE_C = "video_style_c.json"

# Node IDs in workflows
NODE_LOAD_IMAGE = "7"
NODE_SAVE_IMAGE = "27"
NODE_SAVE_VIDEO = "27"  # Update based on actual workflow

# Video processing messages
VIDEO_SEND_IMAGE_PROMPT = "请上传图片，我们将生成视频"
VIDEO_STYLE_SELECTION_MESSAGE = "请选择视频风格："

# Video processing button labels
VIDEO_STYLE_A_BUTTON = "风格 A"
VIDEO_STYLE_B_BUTTON = "风格 B"
VIDEO_STYLE_C_BUTTON = "风格 C"
BACK_TO_MENU_BUTTON = "🏠 返回主菜单"

# Top-up packages (amount in CNY: credits)
TOPUP_PACKAGES = {
    1: 2,       # ¥1 = 2积分
    10: 30,     # ¥10 = 30积分
    30: 120,    # ¥30 = 120积分
    50: 250,    # ¥50 = 250积分
    100: 600    # ¥100 = 600积分
}
