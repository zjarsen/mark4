"""
Notification service for sending messages to users via Telegram.

This refactored version provides:
- Better error handling (no silent failures)
- Organized by message type
- Better logging
- Type hints
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import TelegramError
import logging
from typing import Optional

logger = logging.getLogger('mark4_bot')


class NotificationService:
    """
    Service for sending notifications and messages to users via Telegram.

    Organized into categories:
    - Queue notifications (position, updates)
    - Processing notifications (status, completion)
    - Media delivery (images, videos)
    - Credit confirmations
    - Errors and warnings
    """

    def __init__(self):
        """Initialize notification service."""
        logger.info("Initialized NotificationService")

    # Queue Notifications

    async def send_queue_position(
        self,
        bot,
        chat_id: int,
        position: int,
        total: int,
        prompt_id: str
    ) -> Optional[Message]:
        """
        Send queue position message with refresh button.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            position: Position in queue
            total: Total queue size
            prompt_id: Prompt ID for callback data

        Returns:
            Sent Message object or None if failed
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

        except TelegramError as e:
            logger.error(f"Telegram error sending queue position to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending queue position to {chat_id}: {e}", exc_info=True)
            return None

    async def update_queue_position(
        self,
        message: Message,
        position: int,
        total: int,
        prompt_id: str
    ) -> bool:
        """
        Update existing queue position message.

        Args:
            message: Message object to update
            position: New position
            total: Total queue size
            prompt_id: Prompt ID for callback data

        Returns:
            True if updated successfully, False otherwise
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
            return True

        except TelegramError as e:
            logger.warning(f"Telegram error updating queue position: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating queue position: {e}")
            return False

    async def send_queue_total(
        self,
        bot,
        chat_id: int,
        total: int
    ) -> bool:
        """
        Send total queue size message.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            total: Total queue size

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from core.constants import QUEUE_TOTAL_TEMPLATE

            text = QUEUE_TOTAL_TEMPLATE.format(total=total)
            await bot.send_message(chat_id=chat_id, text=text)

            logger.debug(f"Sent queue total to user {chat_id}: {total}")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending queue total to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending queue total to {chat_id}: {e}")
            return False

    # Processing Notifications

    async def send_processing_status(
        self,
        bot,
        chat_id: int
    ) -> bool:
        """
        Send 'processing' status message.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from core.constants import PROCESSING_IN_PROGRESS

            await bot.send_message(chat_id=chat_id, text=PROCESSING_IN_PROGRESS)
            logger.debug(f"Sent processing status to user {chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending processing status to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending processing status to {chat_id}: {e}")
            return False

    async def send_completion_notification(
        self,
        bot,
        chat_id: int
    ) -> bool:
        """
        Send completion notification.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from core.constants import PROCESSING_COMPLETE_MESSAGE

            await bot.send_message(chat_id=chat_id, text=PROCESSING_COMPLETE_MESSAGE)
            logger.info(f"Sent completion notification to user {chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending completion notification to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending completion notification to {chat_id}: {e}")
            return False

    # Media Delivery

    async def send_processed_image(
        self,
        bot,
        chat_id: int,
        image_path: str
    ) -> Optional[Message]:
        """
        Send processed image to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            image_path: Path to image file

        Returns:
            Sent Message object or None if failed
        """
        try:
            with open(image_path, 'rb') as photo:
                message = await bot.send_photo(chat_id=chat_id, photo=photo)

            logger.info(f"Sent processed image to user {chat_id}")
            return message

        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            return None
        except TelegramError as e:
            logger.error(f"Telegram error sending image to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending processed image to {chat_id}: {e}", exc_info=True)
            return None

    async def send_processed_video(
        self,
        bot,
        chat_id: int,
        video_path: str
    ) -> Optional[Message]:
        """
        Send processed video to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            video_path: Path to video file

        Returns:
            Sent Message object or None if failed
        """
        try:
            with open(video_path, 'rb') as video:
                message = await bot.send_video(chat_id=chat_id, video=video)

            logger.info(f"Sent processed video to user {chat_id}")
            return message

        except FileNotFoundError:
            logger.error(f"Video file not found: {video_path}")
            return None
        except TelegramError as e:
            logger.error(f"Telegram error sending video to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending processed video to {chat_id}: {e}", exc_info=True)
            return None

    # Credit Confirmations

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
    ) -> Optional[Message]:
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
            Sent Message object or None if failed
        """
        try:
            from core.constants import (
                CREDIT_CONFIRMATION_MESSAGE,
                CREDIT_CONFIRMATION_FREE_TRIAL_MESSAGE,
                VIP_CONFIRMATION_MESSAGE,
                CONFIRM_CREDITS_BUTTON,
                CANCEL_CREDITS_BUTTON
            )

            # Build message text
            if is_vip:
                # VIP confirmation message (simplified)
                text = VIP_CONFIRMATION_MESSAGE.format(balance=int(balance))
            elif is_free_trial:
                if not cooldown_info:
                    cooldown_info = ""
                text = CREDIT_CONFIRMATION_FREE_TRIAL_MESSAGE.format(
                    workflow_name=workflow_name,
                    balance=int(balance),
                    cooldown_info=cooldown_info
                )
            else:
                remaining = balance - cost
                text = CREDIT_CONFIRMATION_MESSAGE.format(
                    workflow_name=workflow_name,
                    balance=int(balance),
                    cost=int(cost),
                    remaining=int(remaining)
                )

            # Build inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        CONFIRM_CREDITS_BUTTON,
                        callback_data=f"confirm_credits_{workflow_type}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        CANCEL_CREDITS_BUTTON,
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

        except TelegramError as e:
            logger.error(f"Telegram error sending credit confirmation to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending credit confirmation to {chat_id}: {e}", exc_info=True)
            return None

    # Errors and Warnings

    async def send_error_message(
        self,
        bot,
        chat_id: int,
        error_text: str = None
    ) -> bool:
        """
        Send error message to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            error_text: Optional custom error text

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from core.constants import ERROR_MESSAGE

            text = error_text if error_text else ERROR_MESSAGE

            await bot.send_message(chat_id=chat_id, text=text)
            logger.debug(f"Sent error message to user {chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending error message to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending error message to {chat_id}: {e}")
            return False

    async def send_warning_message(
        self,
        bot,
        chat_id: int,
        warning_text: str
    ) -> bool:
        """
        Send warning message to user.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            warning_text: Warning text to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await bot.send_message(chat_id=chat_id, text=f"⚠️ {warning_text}")
            logger.debug(f"Sent warning message to user {chat_id}")
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending warning to {chat_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending warning to {chat_id}: {e}")
            return False

    # Utility Methods

    async def delete_message_safe(self, message: Message) -> bool:
        """
        Safely delete a message (don't raise error if it fails).

        Args:
            message: Message object to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            await message.delete()
            logger.debug("Deleted message successfully")
            return True

        except TelegramError as e:
            logger.debug(f"Could not delete message (Telegram error): {e}")
            return False
        except Exception as e:
            logger.debug(f"Could not delete message: {e}")
            return False

    async def send_text(
        self,
        bot,
        chat_id: int,
        text: str,
        reply_markup=None
    ) -> Optional[Message]:
        """
        Generic text message sender with optional keyboard.

        Args:
            bot: Telegram Bot instance
            chat_id: Chat ID to send to
            text: Message text
            reply_markup: Optional reply markup

        Returns:
            Sent Message object or None if failed
        """
        try:
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
            logger.debug(f"Sent text message to user {chat_id}")
            return message

        except TelegramError as e:
            logger.error(f"Telegram error sending text to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error sending text to {chat_id}: {e}")
            return None
