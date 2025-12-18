"""
Video workflow service - handles video processing workflows.

This is extracted from the 1,580-line WorkflowService god object,
focusing only on video-related operations.

Responsibilities:
- Video workflow orchestration (3 styles: douxiong, liujing, shejing)
- Credit checking for video workflows (30 credits per use)
- Queue management for video processing
- User notifications for video workflows
"""

import asyncio
import logging
from typing import Optional

from ..base import BaseWorkflowService, WorkflowResult
from domain.credits.exceptions import InsufficientCreditsError

logger = logging.getLogger('mark4_bot')


class VideoWorkflowService(BaseWorkflowService):
    """
    Service for video processing workflows.

    Handles:
    - Video style A (douxiong) - 30 credits
    - Video style B (liujing) - 30 credits
    - Video style C (shejing) - 30 credits
    - Queue management
    - Credit deduction
    - User notifications
    """

    def __init__(
        self,
        credit_service,
        state_manager,
        notification_service,
        file_service,
        queue_manager,
        video_processors: dict
    ):
        """
        Initialize video workflow service.

        Args:
            credit_service: CreditService instance
            state_manager: StateManager instance
            notification_service: NotificationService instance
            file_service: FileService instance
            queue_manager: VideoQueueManager instance
            video_processors: Dict of style -> VideoProcessor instances
                            e.g., {'style_a': StyleAProcessor, ...}
        """
        super().__init__(credit_service, state_manager, notification_service, file_service)
        self.queue = queue_manager
        self.processors = video_processors

    async def start_workflow(
        self,
        bot,
        user_id: int,
        image_path: str,
        style: str
    ) -> tuple[bool, Optional[str]]:
        """
        Start video processing workflow.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            image_path: Path to uploaded image (will be converted to video)
            style: Processing style ('style_a', 'style_b', 'style_c')

        Returns:
            Tuple of (success, error_message)

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        try:
            # Get processor for style
            if style not in self.processors:
                return False, f"Unknown video style: {style}"

            processor = self.processors[style]

            # Validate input
            is_valid, error_msg = await processor.validate_input(image_path)
            if not is_valid:
                return False, error_msg

            # Check if VIP (unlimited access, per user decision to remove VIP limits)
            user = await self.credits.users.get_by_id(user_id)
            is_vip = user and user.get('vip_tier') in ['vip', 'black_gold']

            # Check credits (unless VIP)
            if not is_vip:
                balance = await self.credits.get_balance(user_id)
                if balance < processor.cost:
                    raise InsufficientCreditsError(user_id, processor.cost, balance)

            # Update state
            self.state.update_state(
                user_id,
                state='processing',
                workflow_type='video',
                style=style,
                uploaded_image_path=image_path
            )

            # Queue the job
            from services.queue_manager_base import QueuedJob
            job = QueuedJob(
                user_id=user_id,
                workflow_type='video',
                input_path=image_path,
                style=style
            )

            # Add to queue with callbacks
            await self.queue.add_to_queue(
                job,
                on_submitted=lambda prompt_id: self._handle_submitted(
                    bot, user_id, prompt_id, image_path, style
                ),
                on_completed=lambda prompt_id, history: self._handle_completed(
                    bot, user_id, prompt_id, history, image_path, style
                ),
                on_error=lambda error_msg: self._handle_error(
                    bot, user_id, error_msg, processor.cost
                )
            )

            logger.info(f"Started video workflow for user {user_id}, style: {style}")
            return True, None

        except InsufficientCreditsError:
            raise  # Re-raise for handler to catch
        except Exception as e:
            logger.error(f"Error starting video workflow for user {user_id}: {e}")
            return False, str(e)

    async def _handle_submitted(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str,
        style: str
    ):
        """
        Handle workflow submission (queued to ComfyUI).

        Args:
            bot: Telegram bot instance
            user_id: User ID
            prompt_id: ComfyUI prompt ID
            filename: Input filename
            style: Processing style
        """
        try:
            # Send queue position message
            await self._send_queue_position_message(bot, user_id, 0, prompt_id)

            # Start monitoring
            asyncio.create_task(
                self._monitor_and_complete(bot, user_id, prompt_id, filename, style)
            )

            logger.debug(f"Video workflow submitted for user {user_id}: {prompt_id}")

        except Exception as e:
            logger.error(f"Error in video submitted handler: {e}")

    async def _handle_completed(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        history: dict,
        filename: str,
        style: str
    ):
        """
        Handle workflow completion.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            prompt_id: ComfyUI prompt ID
            history: ComfyUI history
            filename: Input filename
            style: Processing style
        """
        try:
            processor = self.processors[style]

            # Extract output
            result = await processor.process(filename, user_id)

            if result.success:
                # Send result to user
                await self.notifier.send_processed_video(
                    bot, user_id, result.output_path
                )

                # Deduct credits
                try:
                    await self.credits.deduct_credits(
                        user_id,
                        'video_processing',
                        reference_id=prompt_id,
                        feature_type=f'video_{style}'
                    )
                    logger.info(
                        f"Deducted {processor.cost} credits from user {user_id}"
                    )
                except InsufficientCreditsError as e:
                    logger.warning(
                        f"Credit deduction failed after processing: {e}"
                    )
                    # Processing already done, send warning but don't fail
                    await bot.send_message(
                        user_id,
                        "⚠️ 积分不足，本次使用已记为欠费"
                    )

                # Send completion notification
                await self.notifier.send_completion_notification(bot, user_id)

                # Delete queue messages
                await self._delete_queue_messages(bot, user_id)

                # Schedule cleanup
                self._schedule_cleanup(user_id, result.output_path)

                logger.info(f"Video workflow completed for user {user_id}")

            else:
                await bot.send_message(
                    user_id,
                    f"❌ 处理失败: {result.error_message}"
                )

            # Reset state
            self.state.reset_state(user_id)

        except Exception as e:
            logger.error(f"Error in video completed handler: {e}")
            await self._handle_error(bot, user_id, str(e), 0)

    async def _handle_error(
        self,
        bot,
        user_id: int,
        error_msg: str,
        refund_amount: float
    ):
        """
        Handle workflow error with optional credit refund.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            error_msg: Error message
            refund_amount: Credits to refund (if deducted)
        """
        try:
            # Send error message
            await bot.send_message(
                user_id,
                f"❌ 处理失败: {error_msg}\n\n如果扣除了积分，将自动退回。"
            )

            # Refund credits if applicable
            if refund_amount > 0:
                try:
                    await self.credits.add_credits(
                        user_id,
                        refund_amount,
                        description="处理失败退款"
                    )
                    logger.info(f"Refunded {refund_amount} credits to user {user_id}")
                except Exception as e:
                    logger.error(f"Error refunding credits: {e}")

            # Delete queue messages
            await self._delete_queue_messages(bot, user_id)

            # Reset state
            self.state.reset_state(user_id)

        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    async def _monitor_and_complete(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str,
        style: str
    ):
        """
        Monitor ComfyUI processing and complete workflow.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            prompt_id: ComfyUI prompt ID
            filename: Input filename
            style: Processing style
        """
        try:
            # Wait for completion
            # This will be handled by queue manager callbacks
            pass

        except Exception as e:
            logger.error(f"Error monitoring workflow: {e}")
            await self._handle_error(bot, user_id, str(e), 0)

    def _schedule_cleanup(self, user_id: int, output_path: str):
        """
        Schedule cleanup of output file after timeout.

        Args:
            user_id: User ID
            output_path: Path to output file
        """
        async def cleanup_task():
            try:
                await asyncio.sleep(300)  # 5 minutes
                self.files.delete_file(output_path)
                logger.debug(f"Cleaned up file for user {user_id}: {output_path}")
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

        # Cancel existing cleanup task if any
        if self.state.has_cleanup_task(user_id):
            self.state.cancel_cleanup_task(user_id)

        # Start new cleanup task
        task = asyncio.create_task(cleanup_task())
        self.state.set_cleanup_task(user_id, task)

    async def get_queue_status(self, user_id: int) -> dict:
        """
        Get queue status for user.

        Args:
            user_id: User ID

        Returns:
            Dict with queue information
        """
        return await self.queue.get_user_queue_status(user_id)

    async def cancel_workflow(self, user_id: int) -> bool:
        """
        Cancel active workflow for user.

        Args:
            user_id: User ID

        Returns:
            True if cancelled
        """
        try:
            # Remove from queue
            await self.queue.remove_user_job(user_id)

            # Cancel cleanup task
            self.state.cancel_cleanup_task(user_id)

            # Reset state
            self.state.reset_state(user_id)

            logger.info(f"Cancelled workflow for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}")
            return False
