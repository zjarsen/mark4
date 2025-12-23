"""
Image workflow service - handles image processing workflows.

This is extracted from the 1,580-line WorkflowService god object,
focusing only on image-related operations.

Responsibilities:
- Image workflow orchestration
- Credit checking for image workflows
- Queue management for image processing
- User notifications for image workflows
"""

import asyncio
import logging
from typing import Optional

from ..base import BaseWorkflowService, WorkflowResult
from domain.credits.exceptions import InsufficientCreditsError

logger = logging.getLogger('mark4_bot')


class ImageWorkflowService(BaseWorkflowService):
    """
    Service for image processing workflows.

    Handles:
    - Image undress workflow (10 credits)
    - Image bra workflow (free)
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
        image_processors: dict
    ):
        """
        Initialize image workflow service.

        Args:
            credit_service: CreditService instance
            state_manager: StateManager instance
            notification_service: NotificationService instance
            file_service: FileService instance
            queue_manager: ImageQueueManager instance
            image_processors: Dict of style -> ImageProcessor instances
                             e.g., {'bra': BraProcessor, 'undress': UndressProcessor}
        """
        super().__init__(credit_service, state_manager, notification_service, file_service)
        self.queue = queue_manager
        self.processors = image_processors

    async def start_workflow(
        self,
        bot,
        user_id: int,
        image_path: str,
        style: str = 'undress'
    ) -> tuple[bool, Optional[str]]:
        """
        Start image processing workflow.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            image_path: Path to uploaded image
            style: Processing style ('bra', 'undress')

        Returns:
            Tuple of (success, error_message)

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        logger.info(f"ImageWorkflowService.start_workflow called - user: {user_id}, style: {style}, image_path: {image_path}")
        logger.info(f"Available processors: {list(self.processors.keys())}")

        try:
            # Get processor for style
            if style not in self.processors:
                return False, f"Unknown style: {style}"

            processor = self.processors[style]

            # Validate input
            is_valid, error_msg = await processor.validate_input(image_path)
            if not is_valid:
                return False, error_msg

            # Check if VIP (unlimited access, per user decision to remove VIP limits)
            user = self.credits.users.get_by_id(user_id)
            is_vip = user and user.get('vip_tier') in ['vip', 'black_gold']

            # Check credits (unless free style or VIP)
            if style != 'i2i_1' and not is_vip:
                # Check free trial first
                has_trial = await self.credits.has_free_trial(user_id)
                if not has_trial:
                    # Check credit balance
                    balance = await self.credits.get_balance(user_id)
                    if balance < processor.cost:
                        raise InsufficientCreditsError(user_id, processor.cost, balance)

            # Update state
            await self.state.update_state(
                user_id,
                state='processing',
                workflow_type='image',
                style=style,
                uploaded_image_path=image_path
            )

            # Upload image to ComfyUI first
            from pathlib import Path
            from datetime import datetime
            image_filename = Path(image_path).name

            logger.info(f"Uploading image to ComfyUI: {image_filename}")
            await processor.comfyui.upload_image(image_path, image_filename)
            logger.info(f"Image uploaded successfully: {image_filename}")

            # Prepare workflow with filename (not full path)
            workflow = processor.prepare_workflow(image_filename, user_id)

            # Create job with complete workflow and callbacks
            from services.queue_manager_base import QueuedJob
            job_id = f"{user_id}_{int(datetime.utcnow().timestamp() * 1000)}"

            job = QueuedJob(
                job_id=job_id,
                user_id=user_id,
                workflow=workflow,
                workflow_type=style,
                on_submitted=lambda prompt_id: self._handle_submitted(
                    bot, user_id, prompt_id, image_filename, style
                ),
                on_completed=lambda prompt_id, history: self._handle_completed(
                    bot, user_id, prompt_id, history, image_filename, style
                ),
                on_error=lambda error_msg: self._handle_error(
                    bot, user_id, error_msg, processor.cost if style != 'i2i_1' else 0
                )
            )

            # Queue the job (Black Gold VIP gets priority)
            is_black_gold_vip = user and user.get('vip_tier') == 'black_gold'
            await self.queue.queue_job(job, is_vip=is_black_gold_vip)

            logger.info(f"Started image workflow for user {user_id}, style: {style}")
            return True, None

        except InsufficientCreditsError:
            raise  # Re-raise for handler to catch
        except Exception as e:
            import traceback
            logger.error(f"Error starting image workflow for user {user_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
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

            logger.debug(f"Image workflow submitted for user {user_id}: {prompt_id}")

        except Exception as e:
            logger.error(f"Error in image submitted handler: {e}")

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

            # Extract outputs from ComfyUI history structure
            # History structure: {prompt: [...], outputs: {node_id: {images: [...]}}}
            outputs = history.get('outputs', {})

            logger.debug(f"History keys for user {user_id}: {list(history.keys())}")
            logger.debug(f"Outputs keys for user {user_id}: {list(outputs.keys())}")

            # Extract output from ComfyUI outputs
            output_path = await processor.extract_output(outputs, user_id)

            if output_path:
                # Send result to user
                await self.notifier.send_processed_image(
                    bot, user_id, output_path
                )

                # Deduct credits (if not free style)
                if style != 'i2i_1':
                    try:
                        await self.credits.deduct_credits(
                            user_id,
                            'image_processing',
                            reference_id=prompt_id,
                            feature_type=f'image_{style}'
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
                await self._schedule_cleanup(user_id, output_path)

                logger.info(f"Image workflow completed for user {user_id}")

            else:
                await bot.send_message(
                    user_id,
                    "❌ 处理失败: No output image found"
                )

            # Reset state
            await self.state.reset_state(user_id)

        except Exception as e:
            logger.error(f"Error in image completed handler: {e}")
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
            await self.state.reset_state(user_id)

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

    async def _schedule_cleanup(self, user_id: int, output_path: str):
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
        if await self.state.has_cleanup_task(user_id):
            await self.state.cancel_cleanup_task(user_id)

        # Start new cleanup task
        task = asyncio.create_task(cleanup_task())
        await self.state.set_cleanup_task(user_id, task)

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
            await self.state.cancel_cleanup_task(user_id)

            # Reset state
            await self.state.reset_state(user_id)

            logger.info(f"Cancelled workflow for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling workflow: {e}")
            return False
