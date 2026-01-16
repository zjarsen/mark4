"""Video processing workflow implementations."""

import asyncio
from pathlib import Path
from typing import Dict
import logging
from .base_workflow import BaseWorkflow

logger = logging.getLogger('mark4_bot')


class VideoProcessingWorkflowBase(BaseWorkflow):
    """Base class for all video processing workflows."""

    def extract_output_image(self, outputs: Dict) -> Dict:
        """
        Extract output video info from outputs dictionary.
        Overrides base class to handle video output structure.

        Args:
            outputs: Outputs dictionary from ComfyUI

        Returns:
            Dictionary with video file info

        Raises:
            ValueError: If output node or video not found
        """
        node_id = self.get_output_node_id()

        if node_id not in outputs:
            raise ValueError(f"Output node '{node_id}' not found in outputs")

        node_output = outputs[node_id]

        # VHS_VideoCombine can output videos in different keys
        # Try common keys: 'gifs', 'videos', or fall back to 'images'
        for key in ['gifs', 'videos', 'images']:
            if key in node_output and node_output[key]:
                logger.debug(f"Found video output in key '{key}'")
                return node_output[key][0]

        # If no standard keys found, log the available keys for debugging
        available_keys = list(node_output.keys())
        logger.error(f"No video output found. Available keys: {available_keys}")
        raise ValueError(f"No video output in node '{node_id}'. Available keys: {available_keys}")

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

        # Inject image filename into LoadImage node (video workflows use node 267)
        from core.constants import NODE_LOAD_IMAGE_VIDEO
        if NODE_LOAD_IMAGE_VIDEO in workflow:
            workflow[NODE_LOAD_IMAGE_VIDEO]["inputs"]["image"] = filename
            logger.debug(f"Injected filename '{filename}' into node {NODE_LOAD_IMAGE_VIDEO}")
        else:
            logger.warning(
                f"LoadImage node '{NODE_LOAD_IMAGE_VIDEO}' not found in workflow"
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
        Handle completion: download video, send to user, schedule cleanup.
        NO REFUND POLICY - credits already deducted before queueing.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            filename: Original uploaded filename
            outputs: Outputs from ComfyUI
            state_manager: State manager instance
            notification_service: Notification service instance
        """
        try:
            # Extract output video info (uses same method as image)
            output_data = self.extract_output_image(outputs)

            # Generate output path
            output_path = self.file_service.get_output_path(filename)

            # Download processed video
            await self.download_output_image(output_data, output_path)

            # Send video to user (priority: send first)
            message = await notification_service.send_processed_video(
                bot,
                user_id,
                output_path
            )

            # Send completion notification
            await notification_service.send_completion_notification(bot, user_id)

            # Delete queue/processing message if exists
            state = state_manager.get_state(user_id)
            queue_msg_id = state.get('queue_message_id')
            if queue_msg_id:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=queue_msg_id)
                    logger.info(f"Deleted queue/processing message {queue_msg_id} for user {user_id}")
                except Exception as e:
                    logger.warning(f"Could not delete queue/processing message {queue_msg_id}: {e}")

            # Schedule 5-minute cleanup
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

            # Reset state
            state_manager.reset_state(user_id)

            logger.info(f"Video processing completed for user {user_id}")

        except Exception as e:
            logger.error(f"Error handling video completion for user {user_id}: {str(e)}")
            # Get error message with translation fallback
            if notification_service.translation_service:
                error_msg = notification_service.translation_service.get(
                    user_id,
                    'errors.completion_send_failed'
                )
            else:
                error_msg = "处理完成但发送失败，请联系管理员"

            await notification_service.send_error_message(
                bot,
                user_id,
                error_msg
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
        Delete files and message after timeout (5 minutes).

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            original_filename: Original uploaded filename
            output_path: Path to output file
            message_id: Message ID to delete
            state_manager: State manager instance
        """
        try:
            # Wait for cleanup timeout
            await asyncio.sleep(self.config.CLEANUP_TIMEOUT)

            # Delete uploaded file
            self.file_service.delete_user_upload(original_filename)

            # Delete processed output
            self.file_service.delete_processed_output(Path(output_path).name)

            # Delete message from chat
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
            except Exception as e:
                logger.debug(f"Could not delete video message: {e}")

            # Remove cleanup task reference
            if state_manager.has_cleanup_task(user_id):
                state_manager.cancel_cleanup_task(user_id)

            logger.info(f"Cleaned up video files and message for user {user_id}")

        except asyncio.CancelledError:
            logger.debug(f"Cleanup task cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in cleanup for user {user_id}: {str(e)}")


class VideoProcessingStyleA(VideoProcessingWorkflowBase):
    """Video processing workflow for i2v_1 style."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename for i2v_1 style."""
        from core.styles import get_style
        return get_style('i2v_1').workflow_file

    def get_output_node_id(self) -> str:
        """Return output node ID for i2v_1 style."""
        from core.constants import NODE_SAVE_VIDEO
        return NODE_SAVE_VIDEO


class VideoProcessingStyleB(VideoProcessingWorkflowBase):
    """Video processing workflow for i2v_2 style."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename for i2v_2 style."""
        from core.styles import get_style
        return get_style('i2v_2').workflow_file

    def get_output_node_id(self) -> str:
        """Return output node ID for i2v_2 style."""
        from core.constants import NODE_SAVE_VIDEO
        return NODE_SAVE_VIDEO


class VideoProcessingStyleC(VideoProcessingWorkflowBase):
    """Video processing workflow for i2v_3 style."""

    def get_workflow_filename(self) -> str:
        """Return workflow JSON filename for i2v_3 style."""
        from core.styles import get_style
        return get_style('i2v_3').workflow_file

    def get_output_node_id(self) -> str:
        """Return output node ID for i2v_3 style."""
        from core.constants import NODE_SAVE_VIDEO
        return NODE_SAVE_VIDEO
