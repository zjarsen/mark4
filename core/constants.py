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
MENU_OPTION_VIDEO = "2. 图片转视频脱衣（暂未开放）"
MENU_OPTION_CHECK_QUEUE = "3. 查看队列"

# Message templates
WELCOME_MESSAGE = """欢迎光临免费版脱衣bot!
简单的使用说明：仅需选择"图片脱衣"，上传一张尽量正脸的照片，可以半身可以全身，AI就会直接帮你把衣服脱掉～"""

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
QUEUE_UNAVAILABLE = "无法获取队列信息，请稍后再试"
INVALID_STATE_MESSAGE = "请先选择 '1. 图片脱衣' 功能"
UNEXPECTED_INPUT_MESSAGE = "请从菜单中选择一个选项。"
ERROR_MESSAGE = "发生错误，请稍后重试"

# Button labels
REFRESH_QUEUE_BUTTON = "刷新队列"

# Workflow file names
WORKFLOW_IMAGE_PROCESSING = "qwen_image_edit_final.json"
WORKFLOW_VIDEO_PROCESSING = "video_processing.json"  # Future
WORKFLOW_I2I = "i2i_1.json"  # Alternative workflow

# Node IDs in workflows
NODE_LOAD_IMAGE = "7"
NODE_SAVE_IMAGE = "27"
