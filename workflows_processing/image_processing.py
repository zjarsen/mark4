"""Image processing workflow implementation."""

import asyncio
from pathlib import Path
from typing import Dict
import logging
from .base_workflow import BaseWorkflow

logger = logging.getLogger('mark4_bot')


class ImageProcessingWorkflow(BaseWorkflow):
    """Workflow for processing images (clothing removal)."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename."""
        from core.constants import WORKFLOW_IMAGE_PROCESSING
        return WORKFLOW_IMAGE_PROCESSING

    def get_output_node_id(self) -> str:
        """Return output node ID."""
        from core.constants import NODE_SAVE_IMAGE
        return NODE_SAVE_IMAGE

    async def prepare_workflow(self, **params) -> Dict:
        """
        Load workflow and inject image filename.

        Args:
            **params: Must contain 'filename' key

        Returns:
            Workflow dictionary with injected filename

        Raises:
            KeyError: If 'filename' not in params
        """
        if 'filename' not in params:
            raise KeyError("'filename' is required in params")

        filename = params['filename']

        # Load base workflow
        workflow = self.load_workflow_json()

        # Inject image filename into LoadImage node
        from core.constants import NODE_LOAD_IMAGE
        if NODE_LOAD_IMAGE in workflow:
            workflow[NODE_LOAD_IMAGE]["inputs"]["image"] = filename
            logger.debug(f"Injected filename '{filename}' into node {NODE_LOAD_IMAGE}")
        else:
            logger.warning(
                f"LoadImage node '{NODE_LOAD_IMAGE}' not found in workflow"
            )

        return workflow

    async def handle_completion(
        self,
        bot,
        user_id: int,
        filename: str,
        outputs: Dict,
        state_manager,
        notification_service
    ):
        """
        Handle completion: download image, send to user, schedule cleanup.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            filename: Original uploaded filename
            outputs: Outputs from ComfyUI
            state_manager: State manager instance
            notification_service: Notification service instance
        """
        try:
            # Extract output image info
            output_image = self.extract_output_image(outputs)

            # Generate output path
            output_path = self.file_service.get_output_path(filename)

            # Download processed image
            await self.download_output_image(output_image, output_path)

            # Send image to user (priority: send first)
            message = await notification_service.send_processed_image(
                bot,
                user_id,
                output_path
            )

            # Send completion notification
            await notification_service.send_completion_notification(bot, user_id)

            # Delete queue message if exists
            if state_manager.has_queue_message(user_id):
                queue_msg = state_manager.get_queue_message(user_id)
                await notification_service.delete_message_safe(queue_msg)
                state_manager.remove_queue_message(user_id)

            # Schedule cleanup after timeout
            cleanup_task = asyncio.create_task(
                self._cleanup_after_timeout(
                    bot,
                    user_id,
                    filename,
                    output_path,
                    message.message_id,
                    state_manager
                )
            )
            state_manager.set_cleanup_task(user_id, cleanup_task)

            # Reset user state
            state_manager.reset_state(user_id)

            logger.info(f"Completed workflow for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling completion for user {user_id}: {str(e)}")
            await notification_service.send_error_message(
                bot,
                user_id,
                "处理完成但发送失败，请联系管理员"
            )

    async def _cleanup_after_timeout(
        self,
        bot,
        user_id: int,
        original_filename: str,
        output_path: str,
        message_id: int,
        state_manager
    ):
        """
        Delete files and message after timeout.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            original_filename: Original upload filename
            output_path: Path to processed output file
            message_id: Message ID of sent image
            state_manager: State manager instance
        """
        try:
            # Wait for cleanup timeout
            await asyncio.sleep(self.config.CLEANUP_TIMEOUT)

            logger.info(
                f"Starting cleanup for user {user_id} after "
                f"{self.config.CLEANUP_TIMEOUT}s timeout"
            )

            # Delete user upload
            self.file_service.delete_user_upload(original_filename)

            # Delete processed output
            output_filename = Path(output_path).name
            self.file_service.delete_processed_output(output_filename)

            # Delete image message from chat
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
                logger.debug(f"Deleted image message for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not delete image message: {str(e)}")

            # Remove cleanup task reference
            if state_manager.has_cleanup_task(user_id):
                state_manager.cancel_cleanup_task(user_id)

            logger.info(f"Cleanup completed for user {user_id}")

        except asyncio.CancelledError:
            logger.debug(f"Cleanup task cancelled for user {user_id}")

        except Exception as e:
            logger.error(f"Error during cleanup for user {user_id}: {str(e)}")


class ImageProcessingStyleBase(BaseWorkflow):
    """Base class for image processing with different styles."""

    def get_output_node_id(self) -> str:
        """Return output node ID for image workflows."""
        from core.constants import NODE_SAVE_IMAGE
        return NODE_SAVE_IMAGE

    async def prepare_workflow(self, **params) -> Dict:
        """
        Load workflow and inject image filename.

        Args:
            **params: Must contain 'filename' key

        Returns:
            Workflow dictionary ready for queueing

        Raises:
            KeyError: If required params missing
        """
        if 'filename' not in params:
            raise KeyError("'filename' is required in params")

        filename = params['filename']
        workflow = self.load_workflow_json()

        # Inject filename into load image node
        from core.constants import NODE_LOAD_IMAGE
        if NODE_LOAD_IMAGE in workflow:
            workflow[NODE_LOAD_IMAGE]["inputs"]["image"] = filename
        else:
            logger.warning(f"Node {NODE_LOAD_IMAGE} not found in workflow")

        return workflow

    async def handle_completion(
        self,
        bot,
        user_id: int,
        filename: str,
        outputs: Dict,
        state_manager,
        notification_service
    ):
        """
        Handle completion: download image, send to user, schedule cleanup.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            filename: Original uploaded filename
            outputs: Outputs from ComfyUI
            state_manager: State manager instance
            notification_service: Notification service instance
        """
        try:
            # Extract output image info
            output_image = self.extract_output_image(outputs)

            # Generate output path
            output_path = self.file_service.get_output_path(filename)

            # Download processed image
            await self.download_output_image(output_image, output_path)

            # Send image to user (priority: send first)
            message = await notification_service.send_processed_image(
                bot,
                user_id,
                output_path
            )

            # Send completion notification
            await notification_service.send_completion_notification(bot, user_id)

            # Delete queue message if exists
            if state_manager.has_queue_message(user_id):
                queue_msg = state_manager.get_queue_message(user_id)
                await notification_service.delete_message_safe(queue_msg)
                state_manager.remove_queue_message(user_id)

            # Schedule cleanup after timeout
            cleanup_task = asyncio.create_task(
                self._cleanup_after_timeout(
                    bot,
                    user_id,
                    filename,
                    output_path,
                    message.message_id,
                    state_manager
                )
            )
            state_manager.set_cleanup_task(user_id, cleanup_task)

            # Reset user state
            state_manager.reset_state(user_id)

            logger.info(f"Completed workflow for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling completion for user {user_id}: {str(e)}")
            await notification_service.send_error_message(
                bot,
                user_id,
                "处理完成但发送失败，请联系管理员"
            )

    async def _cleanup_after_timeout(
        self,
        bot,
        user_id: int,
        original_filename: str,
        output_path: str,
        message_id: int,
        state_manager
    ):
        """
        Delete files and message after timeout.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            original_filename: Original upload filename
            output_path: Path to processed output file
            message_id: Message ID of sent image
            state_manager: State manager instance
        """
        try:
            # Wait for cleanup timeout
            await asyncio.sleep(self.config.CLEANUP_TIMEOUT)

            logger.info(
                f"Starting cleanup for user {user_id} after "
                f"{self.config.CLEANUP_TIMEOUT}s timeout"
            )

            # Delete user upload
            self.file_service.delete_user_upload(original_filename)

            # Delete processed output
            output_filename = Path(output_path).name
            self.file_service.delete_processed_output(output_filename)

            # Delete image message from chat
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
                logger.debug(f"Deleted image message for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not delete image message: {str(e)}")

            # Remove cleanup task reference
            if state_manager.has_cleanup_task(user_id):
                state_manager.cancel_cleanup_task(user_id)

            logger.info(f"Cleanup completed for user {user_id}")

        except asyncio.CancelledError:
            logger.debug(f"Cleanup task cancelled for user {user_id}")

        except Exception as e:
            logger.error(f"Error during cleanup for user {user_id}: {str(e)}")


class ImageProcessingStyleBra(ImageProcessingStyleBase):
    """Image processing workflow for Bra style (粉色蕾丝内衣)."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename for Bra style."""
        from core.constants import WORKFLOW_IMAGE_STYLE_BRA
        return WORKFLOW_IMAGE_STYLE_BRA


class ImageProcessingStyleUndress(ImageProcessingStyleBase):
    """Image processing workflow for Undress style (脱到精光)."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename for Undress style."""
        from core.constants import WORKFLOW_IMAGE_STYLE_UNDRESS
        return WORKFLOW_IMAGE_STYLE_UNDRESS
