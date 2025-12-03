"""Queue monitoring and management service."""

import asyncio
import logging

logger = logging.getLogger('mark4_bot')


class QueueService:
    """Service for monitoring and managing processing queues."""

    def __init__(self, config, comfyui_service, notification_service):
        """
        Initialize queue service.

        Args:
            config: Configuration object
            comfyui_service: ComfyUI service instance
            notification_service: Notification service instance
        """
        self.config = config
        self.comfyui_service = comfyui_service
        self.notification_service = notification_service

    async def get_queue_position(self, prompt_id: str) -> tuple:
        """
        Get queue position for a prompt.

        Args:
            prompt_id: Prompt ID to check

        Returns:
            Tuple of (position, total)
        """
        return await self.comfyui_service.get_queue_position(prompt_id)

    async def get_queue_total(self) -> int:
        """
        Get total number of items in queue.

        Returns:
            Total queue size
        """
        try:
            queue_info = await self.comfyui_service.get_queue_info()
            return queue_info['total']

        except Exception as e:
            logger.error(f"Error getting queue total: {str(e)}")
            return 0

    async def monitor_processing(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        completion_callback,
        comfyui_service=None
    ):
        """
        Monitor processing until complete and call callback.

        Args:
            bot: Telegram Bot instance
            user_id: User ID for notifications
            prompt_id: Prompt ID to monitor
            completion_callback: Async function to call when complete
                                 Should accept (outputs) parameter
            comfyui_service: Optional ComfyUI service instance to use for this workflow.
                           If not provided, uses the default instance.
        """
        logger.info(f"Started monitoring prompt {prompt_id} for user {user_id}")

        # Use provided comfyui_service or fall back to default
        service = comfyui_service if comfyui_service is not None else self.comfyui_service

        while True:
            await asyncio.sleep(self.config.QUEUE_POLL_INTERVAL)

            try:
                # Check if processing is complete
                outputs = await service.check_completion(prompt_id)

                if outputs:
                    logger.info(f"Processing complete for prompt {prompt_id}")

                    # Call completion callback
                    await completion_callback(outputs)
                    break

            except Exception as e:
                logger.error(
                    f"Error monitoring prompt {prompt_id}: {str(e)}. "
                    "Will retry..."
                )
                # Continue monitoring despite errors
                await asyncio.sleep(self.config.QUEUE_POLL_INTERVAL)

    async def refresh_queue_position(
        self,
        prompt_id: str,
        queue_message
    ):
        """
        Refresh queue position in existing message.

        Args:
            prompt_id: Prompt ID to check
            queue_message: Message object to update
        """
        try:
            position, total = await self.get_queue_position(prompt_id)

            if position > 0:
                await self.notification_service.update_queue_position(
                    queue_message,
                    position,
                    total,
                    prompt_id
                )
            else:
                # Position = 0 means either running or completed
                # Check completion status to determine which message to show
                from core.constants import PROCESSING_RUNNING, PROCESSING_RETRIEVING

                outputs = await self.comfyui_service.check_completion(prompt_id)

                if outputs:
                    # Processing is complete, image is being retrieved
                    await queue_message.edit_text(PROCESSING_RETRIEVING)
                else:
                    # Still processing (running)
                    await queue_message.edit_text(PROCESSING_RUNNING)

        except Exception as e:
            logger.error(f"Error refreshing queue position: {str(e)}")
