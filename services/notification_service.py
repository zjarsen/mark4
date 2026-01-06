"""Notification service for sending messages to users."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger('mark4_bot')


class NotificationService:
    """Service for sending notifications and messages to users."""

    def __init__(self, config, translation_service=None):
        """
        Initialize notification service.

        Args:
            config: Configuration object
            translation_service: Translation service for i18n
        """
        self.config = config
        self.translation_service = translation_service

    async def send_queue_position(
        self,
        bot,
        chat_id: int,
        position: int,
        total: int,
        prompt_id: str
    ):
        """
        Send queue position message with refresh button.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            position: Position in queue
            total: Total queue size
            prompt_id: Prompt ID for callback data

        Returns:
            Sent Message object
        """
        try:
            if self.translation_service:
                text = self.translation_service.get(
                    chat_id, 'queue.status', position=position, total=total
                )
                button_text = self.translation_service.get(chat_id, 'buttons.refresh_queue')
            else:
                text = f"⏳ 已进入处理队列\n\n您的位置：第 *{position}* 位\n队列总数：*{total}* 人\n\n💡 提示：点击下方按钮可随时查看 *最新排位*"
                button_text = "刷新队列"

            keyboard = [[
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"refresh_{prompt_id}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )

            logger.info(f"Sent queue position to user {chat_id}: {position}/{total}")
            return message

        except Exception as e:
            logger.error(f"Error sending queue position: {str(e)}")
            raise

    async def update_queue_position(
        self,
        message,
        position: int,
        total: int,
        prompt_id: str
    ):
        """
        Update existing queue position message.

        Args:
            message: Message object to update
            position: New position
            total: Total queue size
            prompt_id: Prompt ID for callback data
        """
        try:
            # Get chat_id from message
            chat_id = message.chat_id

            if self.translation_service:
                text = self.translation_service.get(
                    chat_id, 'queue.status', position=position, total=total
                )
                button_text = self.translation_service.get(chat_id, 'buttons.refresh_queue')
            else:
                text = f"⏳ 已进入处理队列\n\n您的位置：第 *{position}* 位\n队列总数：*{total}* 人\n\n💡 提示：点击下方按钮可随时查看 *最新排位*"
                button_text = "刷新队列"

            keyboard = [[
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"refresh_{prompt_id}"
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.edit_text(text=text, reply_markup=reply_markup)

            logger.debug(f"Updated queue position: {position}/{total}")

        except Exception as e:
            logger.error(f"Error updating queue position: {str(e)}")

    async def send_processing_status(self, bot, chat_id: int):
        """
        Send 'processing' status message.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
        """
        try:
            if self.translation_service:
                text = self.translation_service.get(chat_id, 'processing.in_progress')
            else:
                text = "处理中..."

            await bot.send_message(chat_id=chat_id, text=text)
            logger.debug(f"Sent processing status to user {chat_id}")

        except Exception as e:
            logger.error(f"Error sending processing status: {str(e)}")

    async def send_completion_notification(self, bot, chat_id: int):
        """
        Send completion notification.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
        """
        try:
            if self.translation_service:
                message = self.translation_service.get(chat_id, 'processing.complete')
            else:
                message = "🎉 创作完成！\n\n⏰ 作品将在 *5分钟后* 自动清理\n请 *及时保存* 到相册～\n\n💡 提示：长按图片即可保存"

            await bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Sent completion notification to user {chat_id}")

        except Exception as e:
            logger.error(f"Error sending completion notification: {str(e)}")

    async def send_processed_image(self, bot, chat_id: int, image_path: str):
        """
        Send processed image to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            image_path: Path to image file

        Returns:
            Sent Message object
        """
        try:
            with open(image_path, 'rb') as photo:
                message = await bot.send_photo(chat_id=chat_id, photo=photo)

            logger.info(f"Sent processed image to user {chat_id}")
            return message

        except Exception as e:
            logger.error(f"Error sending processed image: {str(e)}")
            raise

    async def send_processed_video(self, bot, chat_id: int, video_path: str):
        """
        Send processed video to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            video_path: Path to video file

        Returns:
            Sent Message object
        """
        try:
            with open(video_path, 'rb') as video:
                message = await bot.send_video(chat_id=chat_id, video=video)

            logger.info(f"Sent processed video to user {chat_id}")
            return message

        except Exception as e:
            logger.error(f"Error sending processed video: {str(e)}")
            raise

    async def send_credit_confirmation(
        self,
        bot,
        chat_id: int,
        workflow_name: str,
        workflow_type: str,
        balance: float,
        cost: float,
        is_free_trial: bool = False,
        cooldown_info: str = None,
        is_vip: bool = False
    ):
        """
        Send credit confirmation message with confirm/cancel buttons (VIP-aware).

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            workflow_name: Display name of the workflow (e.g., "图片脱衣")
            workflow_type: Type of workflow ('image' or 'video_a'/'video_b'/'video_c')
            balance: Current credit balance
            cost: Cost of this operation
            is_free_trial: Whether this is a free trial use
            cooldown_info: Optional cooldown information text
            is_vip: Whether user is VIP (bypasses credit check)

        Returns:
            Sent Message object
        """
        try:
            # Build message text
            if is_vip:
                # VIP confirmation message (simplified)
                if self.translation_service:
                    text = self.translation_service.get(
                        chat_id, 'vip.confirmation', balance=int(balance)
                    )
                else:
                    text = f"👑 VIP会员确认\n\n本次使用：免费 (VIP特权)\n当前余额：{int(balance)} 积分\n\n✨ VIP用户享受无限使用权限"
            elif is_free_trial:
                if not cooldown_info:
                    cooldown_info = ""
                if self.translation_service:
                    text = self.translation_service.get(
                        chat_id, 'credits.confirmation_free_trial',
                        workflow_name=workflow_name,
                        balance=int(balance),
                        cooldown_info=cooldown_info
                    )
                else:
                    text = f"🎁 免费体验\n\n*{workflow_name}*\n\n本次使用：*免费*\n当前余额：*{int(balance)}* 积分\n\n{cooldown_info}\n\n✨ 确认后 *立即* 开始处理"
            else:
                remaining = balance - cost
                if self.translation_service:
                    text = self.translation_service.get(
                        chat_id, 'credits.confirmation',
                        workflow_name=workflow_name,
                        balance=int(balance),
                        cost=int(cost),
                        remaining=int(remaining)
                    )
                else:
                    text = f"📋 确认使用积分\n\n*{workflow_name}*\n\n💰 消费明细：\n• 当前余额：*{int(balance)}* 积分\n• 本次消费：*{int(cost)}* 积分\n• 确认后余额：*{int(remaining)}* 积分\n\n✨ 确认后 *立即* 开始处理"

            # Get button text
            if self.translation_service:
                confirm_text = self.translation_service.get(chat_id, 'buttons.confirm')
                cancel_text = self.translation_service.get(chat_id, 'buttons.cancel')
            else:
                confirm_text = "✅ 确认"
                cancel_text = "❌ 取消"

            # Build inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        confirm_text,
                        callback_data=f"confirm_credits_{workflow_type}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        cancel_text,
                        callback_data="cancel_credits"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )

            logger.info(
                f"Sent credit confirmation to user {chat_id}: "
                f"{workflow_name}, VIP={is_vip}, free_trial={is_free_trial}"
            )
            return message

        except Exception as e:
            logger.error(f"Error sending credit confirmation: {str(e)}")
            raise

    async def send_error_message(self, bot, chat_id: int, error_text: str = None):
        """
        Send error message to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            error_text: Optional custom error text
        """
        try:
            if error_text:
                text = error_text
            elif self.translation_service:
                text = self.translation_service.get(chat_id, 'errors.system')
            else:
                text = "❌ *系统繁忙*\n\n请稍后重试\n如问题持续出现，请 *联系客服*"

            await bot.send_message(chat_id=chat_id, text=text)
            logger.debug(f"Sent error message to user {chat_id}")

        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

    async def delete_message_safe(self, message):
        """
        Safely delete a message (don't raise error if it fails).

        Args:
            message: Message object to delete
        """
        try:
            await message.delete()
            logger.debug("Deleted message successfully")

        except Exception as e:
            logger.debug(f"Could not delete message: {str(e)}")

    async def send_queue_total(self, bot, chat_id: int, total: int):
        """
        Send total queue size message.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            total: Total queue size
        """
        try:
            if self.translation_service:
                text = self.translation_service.get(chat_id, 'queue.total', total=total)
            else:
                text = f"当前队列总人数为：*{total}*"

            await bot.send_message(chat_id=chat_id, text=text)

            logger.debug(f"Sent queue total to user {chat_id}: {total}")

        except Exception as e:
            logger.error(f"Error sending queue total: {str(e)}")
