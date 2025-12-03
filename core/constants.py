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


# Menu text constants
MENU_OPTION_IMAGE = "1. 图片脱衣"
MENU_OPTION_VIDEO = "2. 图片转视频脱衣"
MENU_OPTION_CHECK_QUEUE = "3. 查看队列"
MENU_OPTION_BALANCE_HISTORY = "4. 📊 积分余额 & 充值记录"
MENU_OPTION_TOPUP = "5. 💳 充值积分"

# Message templates
WELCOME_MESSAGE = """✨ 欢迎体验AI智能脱衣！

🎁 限时免费：每2天免费体验1次
无需充值，立即开始！

💡 使用技巧：
• 上传清晰正脸照片效果最佳
• 支持半身或全身照
• AI自动识别并处理

准备好了吗？选择功能开始体验～"""

SELECT_FUNCTION_MESSAGE = "请选择功能："
SEND_IMAGE_PROMPT = "📸 请上传您的照片，让AI开始创作～"
FEATURE_NOT_IMPLEMENTED = "此功能仍在开发中"
INVALID_FORMAT_MESSAGE = """❌ 图片格式不支持

请发送以下格式的图片：
✅ JPG / JPEG
✅ PNG
✅ WEBP

💡 提示：直接从相册选择照片即可"""
MAX_RETRY_MESSAGE = """⚠️ 已达到尝试上限（3次）

请返回主菜单重新开始
如有疑问，欢迎联系客服"""
ALREADY_PROCESSING_MESSAGE = """⏳ 您的图片正在处理中

请耐心等待当前任务完成
多次提交不会加快处理速度哦～"""
UPLOAD_FAILED_MESSAGE = """❌ 上传失败

可能原因：
• 网络连接不稳定
• 图片文件过大

💡 建议：
1. 检查网络连接
2. 尝试压缩图片后重试
3. 如仍失败请联系客服"""
PROCESSING_COMPLETE_MESSAGE = """🎉 创作完成！

⏰ 作品将在5分钟后自动清理
请及时保存到相册～

💡 提示：长按图片即可保存"""
QUEUE_STATUS_TEMPLATE = """⏳ 已进入处理队列

您的位置：第 {position} 位
队列总数：{total} 人

💡 提示：点击下方按钮可随时查看最新排位"""
QUEUE_TOTAL_TEMPLATE = "当前队列总人数为：{total}"
PROCESSING_IN_PROGRESS = "处理中..."
PROCESSING_RUNNING = "🎨 AI正在精心处理您的照片...\n请稍候，好作品值得等待～"
PROCESSING_RETRIEVING = "✨ 处理完成！正在为您准备作品..."
QUEUE_UNAVAILABLE = "⚠️ 队列系统繁忙中\n请稍后再试或联系客服"
INVALID_STATE_MESSAGE = """💡 操作提示

请先从主菜单选择功能：
→ 1. 图片脱衣

然后按提示上传照片"""
UNEXPECTED_INPUT_MESSAGE = """💡 请选择功能

请点击下方菜单按钮
或发送对应数字（如：1、2、3）"""
ERROR_MESSAGE = """❌ 系统繁忙

请稍后重试
如问题持续出现，请联系客服"""

# Credit system messages
INSUFFICIENT_CREDITS_MESSAGE = """💳 积分不足

当前余额：{balance} 积分
本次需要：{required} 积分

充值后立即可用，无需等待～"""

FREE_TRIAL_MESSAGE = """🎁 免费体验可用！

这是您的免费体验次数
• 使用后2天内自动重置
• 无需消耗积分

请上传照片，开始体验AI魔法～"""

FREE_TRIAL_AVAILABLE_MESSAGE = """🎁 免费体验可用！

这是您的免费体验次数
• 使用后2天内自动重置
• 无需消耗积分

请上传照片，开始体验AI魔法～"""

FREE_TRIAL_COOLDOWN_MESSAGE = """⏰ 免费次数冷却中

下次可用：{next_available}

💳 当前方案：
• 您的余额：{balance} 积分
• 本次需要：10 积分

💡 充值可立即使用，或等待免费次数重置"""

BALANCE_MESSAGE = """💰 我的积分

当前余额：{balance} 积分
累计消费：{total_spent} 积分

📋 服务价格：
• 图片脱衣：10 积分/次
• 视频生成：30 积分/次"""

TOPUP_PACKAGES_MESSAGE = """💳 充值套餐

🔥 超值套餐推荐：
0️⃣ ¥1 = 2积分（体验装）
1️⃣ ¥10 = 30积分 ⭐
2️⃣ ¥30 = 120积分 🔥 性价比最高
3️⃣ ¥50 = 250积分 💎
4️⃣ ¥100 = 600积分 👑 豪华装

✨ 充值优势：
• 积分永久有效
• 充值后立即到账
• 支持微信/支付宝"""

TRANSACTION_HISTORY_HEADER = "📊 最近消费记录\n\n"
TRANSACTION_ITEM_TEMPLATE = "{date} | {type} | {amount:+.0f}分 | 余额 {balance:.0f}\n"
NO_TRANSACTIONS_MESSAGE = "暂无消费记录\n充值后即可开始使用～"

CREDITS_DEDUCTED_MESSAGE = "已扣除 {amount} 积分，当前余额：{balance} 积分"
CREDITS_ADDED_MESSAGE = "充值成功！获得 {amount} 积分，当前余额：{balance} 积分"

# Credit confirmation messages
CREDIT_CONFIRMATION_MESSAGE = """📋 确认使用积分

{workflow_name}

💰 消费明细：
• 当前余额：{balance} 积分
• 本次消费：{cost} 积分
• 确认后余额：{remaining} 积分

✨ 确认后立即开始处理"""

CREDIT_CONFIRMATION_FREE_TRIAL_MESSAGE = """🎁 免费体验

{workflow_name}

本次使用：免费
当前余额：{balance} 积分

{cooldown_info}

✨ 确认后立即开始处理"""

CREDIT_CONFIRMATION_CANCELLED_MESSAGE = "已取消操作"

CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE = """❌ 积分不足

当前余额：{balance} 积分
所需积分：{cost} 积分

请选择充值套餐："""

PAYMENT_PENDING_MESSAGE = """⏰ 等待支付确认

请在3分钟内完成支付
订单将在超时后自动取消

📝 订单信息：
• 订单号：{payment_id}
• 金额：¥{amount}
• 将获得：{credits} 积分

💡 支付完成后积分自动到账"""

PAYMENT_TIMEOUT_MESSAGE = """⏰ 支付已超时

订单已自动取消，积分未扣除
您可以重新选择套餐进行充值"""

PAYMENT_SUCCESS_MESSAGE = """🎉 充值成功！

+{credits} 积分已到账
现在就去体验吧～"""
PAYMENT_FAILED_MESSAGE = "支付失败，请重试"

# Payment timeout duration (in seconds)
PAYMENT_TIMEOUT_SECONDS = 180  # 3 minutes

# Button labels
REFRESH_QUEUE_BUTTON = "刷新队列"
CONFIRM_CREDITS_BUTTON = "✅ 确认"
CANCEL_CREDITS_BUTTON = "❌ 取消"
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
WORKFLOW_VIDEO_STYLE_A = "i2v_undress_douxiong.json"
WORKFLOW_VIDEO_STYLE_B = "i2v_undress_liujing.json"
WORKFLOW_VIDEO_STYLE_C = "i2v_undress_shejing.json"

# Node IDs in workflows
NODE_LOAD_IMAGE = "7"  # Image workflow
NODE_SAVE_IMAGE = "27"  # Image workflow
NODE_LOAD_IMAGE_VIDEO = "267"  # Video workflows
NODE_SAVE_VIDEO = "245"  # Video workflows

# Video processing messages
VIDEO_SEND_IMAGE_PROMPT = "📸 请上传照片\n\n💡 视频生成需要一些时间，请耐心等待～"
VIDEO_STYLE_SELECTION_MESSAGE = """🎬 选择视频风格

💳 每次消费：30积分

请选择您想要的动态效果："""

# Video processing button labels
VIDEO_STYLE_A_BUTTON = "脱衣+抖胸"
VIDEO_STYLE_B_BUTTON = "脱衣+下体流精"
VIDEO_STYLE_C_BUTTON = "脱衣+ 吃吊喝精"
BACK_TO_MENU_BUTTON = "🏠 返回主菜单"

# Workflow display names for confirmation
WORKFLOW_NAME_IMAGE = "图片脱衣"
WORKFLOW_NAME_VIDEO_A = "脱衣+抖胸"
WORKFLOW_NAME_VIDEO_B = "脱衣+下体流精"
WORKFLOW_NAME_VIDEO_C = "脱衣+ 吃吊喝精"

# Top-up packages (amount in CNY: credits)
TOPUP_PACKAGES = {
    1: 2,       # ¥1 = 2积分
    10: 30,     # ¥10 = 30积分
    30: 120,    # ¥30 = 120积分
    50: 250,    # ¥50 = 250积分
    100: 600    # ¥100 = 600积分
}
