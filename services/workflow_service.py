"""Workflow orchestration service."""

import asyncio
from pathlib import Path
import logging
from workflows_processing.image_processing import ImageProcessingWorkflow

logger = logging.getLogger('mark4_bot')


class WorkflowService:
    """Service for orchestrating workflow processing."""

    def __init__(
        self,
        config,
        comfyui_service,
        file_service,
        notification_service,
        queue_service,
        state_manager,
        credit_service=None
    ):
        """
        Initialize workflow service.

        Args:
            config: Configuration object
            comfyui_service: ComfyUI service instance
            file_service: File service instance
            notification_service: Notification service instance
            queue_service: Queue service instance
            state_manager: State manager instance
            credit_service: CreditService instance (optional for backwards compatibility)
        """
        self.config = config
        self.comfyui_service = comfyui_service
        self.file_service = file_service
        self.notification_service = notification_service
        self.queue_service = queue_service
        self.state_manager = state_manager
        self.credit_service = credit_service

        # Initialize workflow implementations
        self.image_workflow = ImageProcessingWorkflow(
            config,
            comfyui_service,
            file_service
        )

    async def start_image_workflow(
        self,
        update,
        context,
        local_path: str,
        user_id: int
    ):
        """
        Start image processing workflow.

        Args:
            update: Telegram Update object
            context: Telegram Context object
            local_path: Path to uploaded image
            user_id: User ID
        """
        try:
            filename = Path(local_path).name

            # Check credits if credit service is available
            if self.credit_service:
                has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                    user_id,
                    'image_processing'
                )

                if not has_sufficient:
                    # Insufficient credits
                    from core.constants import INSUFFICIENT_CREDITS_MESSAGE
                    await update.message.reply_text(
                        INSUFFICIENT_CREDITS_MESSAGE.format(
                            balance=balance,
                            required=cost
                        )
                    )
                    logger.warning(
                        f"User {user_id} has insufficient credits: "
                        f"balance={balance}, required={cost}"
                    )
                    self.state_manager.reset_state(user_id)
                    return

                # Check if using free trial
                has_free_trial = await self.credit_service.has_free_trial(user_id)
                if has_free_trial:
                    from core.constants import FREE_TRIAL_MESSAGE
                    await update.message.reply_text(FREE_TRIAL_MESSAGE)
                    logger.info(f"User {user_id} using free trial for image processing")

            # Upload image to ComfyUI
            await self.image_workflow.upload_image(local_path, filename)

            # Queue workflow
            prompt_id = await self.image_workflow.queue_workflow(filename=filename)

            # Deduct credits after successful queue
            if self.credit_service:
                success, new_balance = await self.credit_service.deduct_credits(
                    user_id,
                    'image_processing',
                    reference_id=prompt_id
                )
                if success:
                    logger.info(
                        f"Deducted credits for user {user_id}, "
                        f"new balance: {new_balance}"
                    )
                else:
                    logger.error(f"Failed to deduct credits for user {user_id}")

            # Update user state
            self.state_manager.update_state(
                user_id,
                state='processing',
                prompt_id=prompt_id,
                filename=filename
            )

            # Show initial queue position
            await self._show_queue_position(update, user_id, prompt_id)

            # Start monitoring in background
            asyncio.create_task(
                self._monitor_and_complete(
                    context.bot,
                    user_id,
                    prompt_id,
                    filename
                )
            )

            logger.info(
                f"Started image workflow for user {user_id}, "
                f"prompt_id: {prompt_id}"
            )

        except Exception as e:
            logger.error(f"Error starting image workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                context.bot,
                user_id,
                "上传失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)

    async def _show_queue_position(self, update, user_id: int, prompt_id: str):
        """
        Display initial queue position to user.

        Args:
            update: Telegram Update object
            user_id: User ID
            prompt_id: Prompt ID
        """
        try:
            position, total = await self.queue_service.get_queue_position(prompt_id)

            message = await self.notification_service.send_queue_position(
                update.message.get_bot(),
                user_id,
                position,
                total,
                prompt_id
            )

            # Store message for later updates/deletion
            self.state_manager.set_queue_message(user_id, message)

        except Exception as e:
            logger.error(f"Error showing queue position for user {user_id}: {str(e)}")

    async def _monitor_and_complete(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str
    ):
        """
        Monitor processing and handle completion.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            prompt_id: Prompt ID to monitor
            filename: Original filename
        """
        async def completion_callback(outputs):
            """Called when processing completes."""
            await self.image_workflow.handle_completion(
                bot,
                user_id,
                filename,
                outputs,
                self.state_manager,
                self.notification_service
            )

        # Start monitoring
        await self.queue_service.monitor_processing(
            bot,
            user_id,
            prompt_id,
            completion_callback
        )

    async def start_video_workflow(
        self,
        update,
        context,
        local_path: str,
        user_id: int
    ):
        """
        Start video processing workflow (future implementation).

        Args:
            update: Telegram Update object
            context: Telegram Context object
            local_path: Path to uploaded file
            user_id: User ID
        """
        # TODO: Implement video workflow
        from core.constants import FEATURE_NOT_IMPLEMENTED
        await update.message.reply_text(FEATURE_NOT_IMPLEMENTED)
        logger.info(f"Video workflow requested by user {user_id} (not implemented)")

    async def cancel_user_workflow(self, user_id: int) -> bool:
        """
        Cancel user's current workflow if any.

        Args:
            user_id: User ID

        Returns:
            True if cancelled, False if no active workflow
        """
        state = self.state_manager.get_state(user_id)

        if state.get('state') == 'processing':
            prompt_id = state.get('prompt_id')

            if prompt_id:
                # Try to cancel on ComfyUI (may not be supported)
                await self.comfyui_service.cancel_prompt(prompt_id)

                # Cancel cleanup task if exists
                self.state_manager.cancel_cleanup_task(user_id)

                # Delete queue message if exists
                if self.state_manager.has_queue_message(user_id):
                    queue_msg = self.state_manager.get_queue_message(user_id)
                    await self.notification_service.delete_message_safe(queue_msg)
                    self.state_manager.remove_queue_message(user_id)

                # Reset state
                self.state_manager.reset_state(user_id)

                logger.info(f"Cancelled workflow for user {user_id}")
                return True

        return False
