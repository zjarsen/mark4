"""Service for managing payment timeout timers and cleanup."""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional
from telegram import Bot

logger = logging.getLogger('mark4_bot')


class PaymentTimeoutService:
    """
    Manages payment timeout timers and tracks timeout messages for cleanup.

    Responsibilities:
    - Track active timeout timers per user
    - Store timeout message IDs for cleanup
    - Cancel timers when payment succeeds
    - Cleanup timeout messages on user interaction
    """

    def __init__(self, bot: Bot):
        """
        Initialize payment timeout service.

        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot

        # Track active timeout tasks: {user_id: asyncio.Task}
        self.active_timers: Dict[int, asyncio.Task] = {}

        # Track timeout messages for cleanup: {user_id: [(timeout_msg_id, menu_msg_id), ...]}
        self.timeout_messages: Dict[int, List[Tuple[int, Optional[int]]]] = {}

    def start_payment_timeout(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        payment_id: str,
        amount_cny: int,
        timeout_callback,
        delay_seconds: int = 180
    ):
        """
        Start a timeout timer for a payment.

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID where payment message was sent
            message_id: Message ID of the payment pending message
            payment_id: Payment ID for tracking
            amount_cny: Payment amount in CNY
            timeout_callback: Async function to call on timeout
            delay_seconds: Timeout delay in seconds (default: 180 = 3 minutes)
        """
        # Cancel any existing timer for this user
        self.cancel_payment_timeout(user_id)

        # Create timeout task
        async def timeout_task():
            try:
                await asyncio.sleep(delay_seconds)

                # Call the timeout callback
                await timeout_callback(user_id, chat_id, message_id, payment_id, amount_cny)

                logger.info(f"Payment timeout triggered for user {user_id}, payment {payment_id}")

            except asyncio.CancelledError:
                logger.debug(f"Payment timeout cancelled for user {user_id}, payment {payment_id}")
            except Exception as e:
                logger.error(f"Error in payment timeout task for user {user_id}: {str(e)}", exc_info=True)

        # Start the task
        task = asyncio.create_task(timeout_task())
        self.active_timers[user_id] = task

        logger.info(f"Started payment timeout for user {user_id}, payment {payment_id} ({delay_seconds}s)")

    def cancel_payment_timeout(self, user_id: int) -> bool:
        """
        Cancel active timeout timer for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            True if timer was cancelled, False if no active timer
        """
        if user_id in self.active_timers:
            task = self.active_timers[user_id]
            task.cancel()
            del self.active_timers[user_id]
            logger.debug(f"Cancelled payment timeout for user {user_id}")
            return True
        return False

    def add_timeout_messages(self, user_id: int, timeout_msg_id: int, menu_msg_id: Optional[int] = None):
        """
        Store timeout message IDs for later cleanup.

        Args:
            user_id: Telegram user ID
            timeout_msg_id: Message ID of the timeout message
            menu_msg_id: Message ID of the menu message (optional)
        """
        if user_id not in self.timeout_messages:
            self.timeout_messages[user_id] = []

        self.timeout_messages[user_id].append((timeout_msg_id, menu_msg_id))
        logger.debug(f"Stored timeout messages for user {user_id}: {timeout_msg_id}, {menu_msg_id}")

    async def cleanup_timeout_messages(self, user_id: int, chat_id: int):
        """
        Delete all stored timeout messages for a user.

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID where messages were sent
        """
        if user_id not in self.timeout_messages:
            return

        messages = self.timeout_messages[user_id]
        deleted_count = 0

        for timeout_msg_id, menu_msg_id in messages:
            try:
                # Delete timeout message
                await self.bot.delete_message(chat_id=chat_id, message_id=timeout_msg_id)
                deleted_count += 1

                # Delete menu message if exists
                if menu_msg_id:
                    try:
                        await self.bot.delete_message(chat_id=chat_id, message_id=menu_msg_id)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete menu message {menu_msg_id}: {str(e)}")

            except Exception as e:
                logger.warning(f"Failed to delete timeout message {timeout_msg_id}: {str(e)}")

        # Clear the stored messages
        del self.timeout_messages[user_id]

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} timeout messages for user {user_id}")

    def has_timeout_messages(self, user_id: int) -> bool:
        """
        Check if user has any pending timeout messages.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has timeout messages
        """
        return user_id in self.timeout_messages and len(self.timeout_messages[user_id]) > 0

    def clear_user_data(self, user_id: int):
        """
        Clear all data for a user (timer + messages).

        Args:
            user_id: Telegram user ID
        """
        self.cancel_payment_timeout(user_id)

        if user_id in self.timeout_messages:
            del self.timeout_messages[user_id]
