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
MENU_OPTION_IMAGE = "1. 📸 图生图类脱衣！✨"
MENU_OPTION_VIDEO = "2. 🎬 图生成视频类脱衣！✨"
MENU_OPTION_TOPUP = "3. 💳 充值积分 🎁 每日抽最高5折！"
MENU_OPTION_BALANCE_HISTORY = "4. 📊 积分余额 & 充值记录"
MENU_OPTION_CHECK_QUEUE = "5. 查看当前队列"

# Message templates
WELCOME_MESSAGE = """✨ 欢迎体验顶级AI脱衣神器！

🎰 **每日幸运折扣**
• 💰 最高可享5折优惠！
• 🎁 每日24:00重置，手慢无
• ⚡ **充值前记得先抽折扣！**

🎁 **新人福利**
• 粉色蕾丝风格 - 永久免费
• 脱到精光风格 - 每2天免费1次

🎨 **核心功能**
• 📸 图片脱衣（10积分/次）- 多种风格
• 🎬 动态视频（30积分/次）- 3种特效
• 🔥 顶级AI模型 - 效果逼真

💎 **VIP会员特权**
• 永久VIP（¥173）- 无限使用所有功能
• 黑金VIP（¥281）- 无限使用 + 优先处理
• 一次付费，终身享用

🎁 **点击下方按钮，立即抽取今日幸运折扣！**"""

SELECT_FUNCTION_MESSAGE = ""
SEND_IMAGE_PROMPT = """📸 请上传您的照片，让AI开始创作～

图片脱衣模型展示✨✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/5)

💡 上传照片后，AI将自动开始处理"""

# Image style selection message
IMAGE_STYLE_SELECTION_MESSAGE = """🎨 选择脱衣风格

模型效果展示：

1. 粉色蕾丝内衣示例✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/25)

2. 脱到精光示例✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/29)

请选择您想要的风格："""

# Demo video links
DEMO_LINK_BRA = "https://t.me/zuiqiangtuoyi/25"
DEMO_LINK_UNDRESS = "https://t.me/zuiqiangtuoyi/29"

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

# Top-up packages message variants (based on discount tier)
TOPUP_PACKAGES_MESSAGE_WITH_DISCOUNT = """💳 充值套餐

🔥🔥🔥 **今日超级幸运！** 🔥🔥🔥
⚡ _您的专属折扣已解锁，点击下方按钮查看！_
💰 **最高可享5折优惠** - 限今日24:00前有效

━━━━━━━━━━━━━━━━━━━━

🔥 超值套餐推荐：
1️⃣ ¥11 = 30积分 ⭐
2️⃣ ¥32 = 120积分 🔥
3️⃣ ¥54 = 250积分 💎
4️⃣ ¥108 = 600积分 👑
5️⃣ ¥173 = 永久VIP ⭐⭐⭐ 【老板主推·无限使用】
6️⃣ ¥281 = 永久黑金VIP 👑👑👑 【无限使用+无需排队】

✨ 充值优势：
• 积分永久有效
• 充值后立即到账
• 支持微信/支付宝

⏰ **别忘了先领取今日折扣！点击下方【幸运折扣】按钮** ⏰"""

TOPUP_PACKAGES_MESSAGE_NORMAL = """💳 充值套餐

🎰 **今日幸运折扣已开启** - 点击下方按钮查看折扣！
💡 _每日随机5%-50%折扣，今天试试运气？_

━━━━━━━━━━━━━━━━━━━━

🔥 超值套餐推荐：
1️⃣ ¥11 = 30积分 ⭐
2️⃣ ¥32 = 120积分 🔥
3️⃣ ¥54 = 250积分 💎
4️⃣ ¥108 = 600积分 👑
5️⃣ ¥173 = 永久VIP ⭐⭐⭐ 【老板主推·无限使用】
6️⃣ ¥281 = 永久黑金VIP 👑👑👑 【无限使用+无需排队】

✨ 充值优势：
• 积分永久有效
• 充值后立即到账
• 支持微信/支付宝"""

TOPUP_PACKAGES_MESSAGE_NO_DISCOUNT = """💳 充值套餐

🎁 **首次充值福利** - 先抽取今日幸运折扣！
💰 _最高可享5折优惠_ | 每日重置 | 限时24小时

━━━━━━━━━━━━━━━━━━━━

🔥 超值套餐推荐：
1️⃣ ¥11 = 30积分 ⭐
2️⃣ ¥32 = 120积分 🔥
3️⃣ ¥54 = 250积分 💎
4️⃣ ¥108 = 600积分 👑
5️⃣ ¥173 = 永久VIP ⭐⭐⭐ 【老板主推·无限使用】
6️⃣ ¥281 = 永久黑金VIP 👑👑👑 【无限使用+无需排队】

✨ 充值优势：
• 积分永久有效
• 充值后立即到账
• 支持微信/支付宝"""

# Legacy message (kept for backwards compatibility)
TOPUP_PACKAGES_MESSAGE = TOPUP_PACKAGES_MESSAGE_NO_DISCOUNT

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
💡 **若支付宝显示"限制收款"，重新发起即可切换可用的二维码**
⚠️ **支付完成后确认界面可能无响应，请返回机器人查看充值成功消息**
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
TOPUP_10_BUTTON = "¥11 = 30积分"
TOPUP_30_BUTTON = "¥32 = 120积分"
TOPUP_50_BUTTON = "¥54 = 250积分"
TOPUP_100_BUTTON = "¥108 = 600积分"
TOPUP_VIP_BUTTON = "¥173 = 永久VIP"
TOPUP_BLACK_GOLD_VIP_BUTTON = "¥281 = 永久黑金VIP"

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

# Video processing messages
VIDEO_SEND_IMAGE_PROMPT = "📸 请上传照片\n\n💡 视频生成需要一些时间，请耐心等待～"
VIDEO_STYLE_SELECTION_MESSAGE = """🎬 选择视频风格

模型效果展示：

1. 视频模型1示例：✨✨脱衣+抖胸✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/13)

2. 视频模型2示例：✨✨脱衣+下体流精✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/15)

3. 视频模型3示例：✨✨脱衣+吃吊喝精✨✨：
[🔞点击观看🔞](https://t.me/zuiqiangtuoyi/19)

请选择您想要的动态效果："""

# Video processing button labels
VIDEO_STYLE_A_BUTTON = "脱衣+抖胸（30积分）"
VIDEO_STYLE_B_BUTTON = "脱衣+下体流精（30积分）"
VIDEO_STYLE_C_BUTTON = "脱衣+ 吃吊喝精（30积分）"

# Image processing button labels
IMAGE_STYLE_BRA_BUTTON = "🎁 粉色蕾丝内衣 ✨永久免费✨"
IMAGE_STYLE_UNDRESS_BUTTON = "脱到精光（10积分）"

BACK_TO_MENU_BUTTON = "🏠 返回主菜单"

# Workflow display names for confirmation
WORKFLOW_NAME_IMAGE = "图片脱衣"

# Image workflow display names for confirmation
WORKFLOW_NAME_IMAGE_BRA = "粉色蕾丝内衣"
WORKFLOW_NAME_IMAGE_UNDRESS = "脱到精光"

WORKFLOW_NAME_VIDEO_A = "脱衣+抖胸"
WORKFLOW_NAME_VIDEO_B = "脱衣+下体流精"
WORKFLOW_NAME_VIDEO_C = "脱衣+ 吃吊喝精"

# Top-up packages (amount in CNY: credits)
TOPUP_PACKAGES = {
    10: 30,         # ¥10 = 30积分
    30: 120,        # ¥30 = 120积分
    50: 250,        # ¥50 = 250积分
    100: 600,       # ¥100 = 600积分
    160: 99999999,  # ¥160 = 永久VIP (unlimited credits)
    260: 99999999   # ¥260 = 永久黑金VIP (unlimited credits)
}

# VIP System Messages
VIP_CONFIRMATION_MESSAGE = """👑 VIP会员确认

本次使用：免费 (VIP特权)
当前余额：{balance} 积分

✨ VIP用户享受无限使用权限"""

VIP_PURCHASE_SUCCESS_MESSAGE = """🎉 恭喜您成为{tier}！

✨ 您的专属特权：
{benefits}

现在就去无限体验吧～"""

VIP_BENEFITS_REGULAR = """• 无限使用所有功能
• 无需积分消耗
• 永久有效"""

VIP_BENEFITS_BLACK_GOLD = """• 无限使用所有功能
• 优先处理队列 ⚡
• 无需积分消耗
• 永久有效"""

VIP_STATUS_BADGE = "👑 {tier}用户"

# VIP Daily Limit Messages (cute and flirty)
VIP_DAILY_LIMIT_REACHED_REGULAR = """主人~♡ 人家今天已经帮你处理50次了，累死宝宝了啦~ 🥺

明天0点就能继续玩啦，记得想人家哦~ 💋

当前使用：{current_usage}/{limit} 次 ✨"""

VIP_DAILY_LIMIT_REACHED_BLACK_GOLD = """主人大人~♡ 100次都被你玩遍了呢~ 人家真的需要休息啦~ 😘

明天0点就能继续陪你玩啦，等我哦~ 💕

当前使用：{current_usage}/{limit} 次 ✨"""

BRA_DAILY_LIMIT_REACHED = """哎呀！你今天的粉色蕾丝内衣免费使用次数已经用完啦！😅

📊 今日使用情况:
   • 已使用: {current_usage}/{limit} 次
   • 重置时间: 明天凌晨 00:00 (GMT+8)

💡 小贴士：
   • 其他付费功能（脱到精光、视频处理等）没有每日限制
   • 有积分就能随时使用哦！

💎 或者升级VIP享受无限使用！

明天见！💕"""

# VIP Balance Display
BALANCE_MESSAGE_VIP = """💰 我的账户

会员等级：{vip_badge}
当前余额：{balance} 积分 (无限使用)
累计消费：{total_spent} 积分

✨ VIP特权生效中"""

# Daily Lucky Discount System
DISCOUNT_TIERS = {
    'SSR': {'rate': 0.5, 'display': 'SSR神级运气', 'emoji': '🎊', 'off': '50%'},
    'SR': {'rate': 0.7, 'display': 'SR超级运气', 'emoji': '🎉', 'off': '30%'},
    'R': {'rate': 0.85, 'display': 'R运气不错', 'emoji': '✨', 'off': '15%'},
    'C': {'rate': 0.95, 'display': 'C普通运气', 'emoji': '🍀', 'off': '5%'}
}

# Lucky discount button labels
LUCKY_DISCOUNT_BUTTON_HOT = "🔥💰 点我领取今日超级折扣！ 💰🔥"
LUCKY_DISCOUNT_BUTTON_NORMAL = "🎰 每日幸运折扣 - 点击查看"
LUCKY_DISCOUNT_BUTTON = LUCKY_DISCOUNT_BUTTON_NORMAL  # Default
LUCKY_DISCOUNT_BUTTON_REVEALED = "{emoji} **{tier}** - {off}折扣已激活"

LUCKY_DISCOUNT_CELEBRATION_SSR = """🎊🎊🎊 **恭喜恭喜！神级运气！** 🎊🎊🎊

**您抽到了 SSR 神级折扣！**
🔥🔥 **全场5折优惠** 🔥🔥

💰 **永久VIP 仅需 ¥87**（原价¥173）
💎 **所有套餐5折** - 省钱一半！

⏰ 限今日24:00前有效 - 抓紧时间抢购！

_立即选择套餐，享受神级折扣！_"""

LUCKY_DISCOUNT_CELEBRATION_SR = """🎉🎉🎉 **恭喜您！超级幸运！** 🎉🎉🎉

**您抽到了 SR 超级折扣！**
⭐⭐ **全场7折优惠** ⭐⭐

💰 **永久VIP 仅需 ¥121**（原价¥173）
💎 **所有套餐7折** - 超值划算！

⏰ 限今日24:00前有效 - 机不可失！

_立即选择套餐，享受超级折扣！_"""

LUCKY_DISCOUNT_REVEALED_R = """✨ **今日运气不错！R级折扣**

全场85折，省15%！
💡 _提示：连续使用可提升折扣等级哦_

💰 **永久VIP 仅需 ¥147**（原价¥173）

⏰ 限今日有效 - 立即使用！"""

LUCKY_DISCOUNT_REVEALED_C = """🍀 **今日折扣已开启！C级折扣**

全场95折，虽然不多但也是优惠！
🎯 _坚持使用，下次可能抽到5折哦_

💰 **永久VIP 仅需 ¥164**（原价¥173）

⏰ 限今日有效 - 不用白不用！"""

LUCKY_DISCOUNT_ALREADY_REVEALED = """⚡ **您今日的折扣已激活！**

当前折扣：**{tier}** ({off}折)
有效期至：**今日24:00** ⏰

💡 所有套餐价格已显示折扣后价格
🔥 _限时优惠，抓紧充值！_

━━━━━━━━━━━━━━━━━━━━
选择下方套餐，立即享受折扣！"""
