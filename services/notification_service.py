"""Notification service for sending messages to users."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger('mark4_bot')


class NotificationService:
    """Service for sending notifications and messages to users."""

    def __init__(self, config):
        """
        Initialize notification service.

        Args:
            config: Configuration object
        """
        self.config = config

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
            from core.constants import QUEUE_STATUS_TEMPLATE, REFRESH_QUEUE_BUTTON

            text = QUEUE_STATUS_TEMPLATE.format(position=position, total=total)

            keyboard = [[
                InlineKeyboardButton(
                    REFRESH_QUEUE_BUTTON,
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
            from core.constants import QUEUE_STATUS_TEMPLATE, REFRESH_QUEUE_BUTTON

            text = QUEUE_STATUS_TEMPLATE.format(position=position, total=total)

            keyboard = [[
                InlineKeyboardButton(
                    REFRESH_QUEUE_BUTTON,
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
            from core.constants import PROCESSING_IN_PROGRESS

            await bot.send_message(chat_id=chat_id, text=PROCESSING_IN_PROGRESS)
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
            from core.constants import PROCESSING_COMPLETE_MESSAGE

            await bot.send_message(chat_id=chat_id, text=PROCESSING_COMPLETE_MESSAGE)
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

    async def send_error_message(self, bot, chat_id: int, error_text: str = None):
        """
        Send error message to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            error_text: Optional custom error text
        """
        try:
            from core.constants import ERROR_MESSAGE

            text = error_text if error_text else ERROR_MESSAGE

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
            from core.constants import QUEUE_TOTAL_TEMPLATE

            text = QUEUE_TOTAL_TEMPLATE.format(total=total)
            await bot.send_message(chat_id=chat_id, text=text)

            logger.debug(f"Sent queue total to user {chat_id}: {total}")

        except Exception as e:
            logger.error(f"Error sending queue total: {str(e)}")
