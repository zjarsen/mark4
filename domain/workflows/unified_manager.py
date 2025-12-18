"""
Unified Workflow Manager - Compatibility Layer

This provides a unified interface for handlers that expect the old
monolithic WorkflowService, but delegates to the new separate
ImageWorkflowService and VideoWorkflowService.

This is a temporary compatibility layer for Phase 5 migration.
"""

import logging
from typing import Optional, Dict, Any
from telegram import Bot

from domain.workflows.image.service import ImageWorkflowService
from domain.workflows.video.service import VideoWorkflowService

logger = logging.getLogger('mark4_bot')


class UnifiedWorkflowManager:
    """
    Unified interface for both image and video workflows.

    Delegates to ImageWorkflowService and VideoWorkflowService based on
    the workflow type requested by handlers.
    """

    def __init__(
        self,
        image_service: ImageWorkflowService,
        video_service: VideoWorkflowService
    ):
        """
        Initialize unified workflow manager.

        Args:
            image_service: Image workflow service
            video_service: Video workflow service
        """
        self.image_service = image_service
        self.video_service = video_service

        # Track which service each user is using
        self._user_workflow_types: Dict[int, str] = {}  # user_id -> 'image' or 'video'

    # ==================== Image Workflow Methods ====================

    async def start_image_workflow(
        self,
        bot: Bot,
        user_id: int,
        chat_id: int,
        message_id: int,
        input_path: str,
        workflow_type: str
    ) -> bool:
        """
        Start image undress workflow (old interface).

        Args:
            bot: Telegram bot instance
            user_id: User's Telegram ID
            chat_id: Chat ID
            message_id: Message ID
            input_path: Path to input image
            workflow_type: Type of workflow (e.g., 'image_undress')

        Returns:
            bool: True if workflow started successfully
        """
        self._user_workflow_types[user_id] = 'image'

        # Map old workflow_type to new processor type
        if workflow_type == 'pink_bra':
            processor_type = 'pink_bra'
        else:
            processor_type = 'undress'

        return await self.image_service.start_workflow(
            bot=bot,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            input_path=input_path,
            processor_type=processor_type
        )

    async def start_image_workflow_with_style(
        self,
        bot: Bot,
        user_id: int,
        chat_id: int,
        message_id: int,
        input_path: str,
        workflow_type: str
    ) -> bool:
        """
        Start image workflow with style selection (old interface).

        This is an alias for start_image_workflow for backward compatibility.
        """
        return await self.start_image_workflow(
            bot, user_id, chat_id, message_id, input_path, workflow_type
        )

    async def proceed_with_image_workflow(self, bot: Bot, user_id: int) -> bool:
        """
        Proceed with image undress workflow after confirmation (old interface).

        Args:
            bot: Telegram bot instance
            user_id: User's Telegram ID

        Returns:
            bool: True if workflow proceeded successfully
        """
        self._user_workflow_types[user_id] = 'image'

        # The new architecture handles confirmation in start_workflow
        # This method is called after user confirms, so just return True
        # The actual processing happens in start_workflow
        logger.debug(f"proceed_with_image_workflow called for user {user_id} (handled by new architecture)")
        return True

    async def proceed_with_image_workflow_with_style(self, bot: Bot, user_id: int) -> bool:
        """
        Proceed with image workflow with style (old interface).

        This is an alias for proceed_with_image_workflow for backward compatibility.
        """
        return await self.proceed_with_image_workflow(bot, user_id)

    # ==================== Video Workflow Methods ====================

    async def start_video_workflow(
        self,
        bot: Bot,
        user_id: int,
        chat_id: int,
        message_id: int,
        input_path: str,
        style: str
    ) -> bool:
        """
        Start video workflow (old interface).

        Args:
            bot: Telegram bot instance
            user_id: User's Telegram ID
            chat_id: Chat ID
            message_id: Message ID
            input_path: Path to input image
            style: Video style ('douxiong', 'liujing', or 'shejing')

        Returns:
            bool: True if workflow started successfully
        """
        self._user_workflow_types[user_id] = 'video'

        # Map style to processor type
        style_map = {
            'douxiong': 'style_a',
            'liujing': 'style_b',
            'shejing': 'style_c'
        }
        processor_type = style_map.get(style, 'style_a')

        return await self.video_service.start_workflow(
            bot=bot,
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            input_path=input_path,
            processor_type=processor_type
        )

    async def proceed_with_video_workflow(self, bot: Bot, user_id: int) -> bool:
        """
        Proceed with video workflow after confirmation (old interface).

        Args:
            bot: Telegram bot instance
            user_id: User's Telegram ID

        Returns:
            bool: True if workflow proceeded successfully
        """
        self._user_workflow_types[user_id] = 'video'

        # The new architecture handles confirmation in start_workflow
        logger.debug(f"proceed_with_video_workflow called for user {user_id} (handled by new architecture)")
        return True

    # ==================== Common Methods ====================

    async def cancel_user_workflow(self, user_id: int) -> bool:
        """
        Cancel any active workflow for a user (old interface).

        Args:
            user_id: User's Telegram ID

        Returns:
            bool: True if workflow was cancelled
        """
        # Try to determine which service this user is using
        workflow_type = self._user_workflow_types.get(user_id)

        # Try both services (one will succeed, one will return False)
        image_cancelled = await self.image_service.cancel_workflow(user_id)
        video_cancelled = await self.video_service.cancel_workflow(user_id)

        # Clean up tracking
        if user_id in self._user_workflow_types:
            del self._user_workflow_types[user_id]

        return image_cancelled or video_cancelled

    async def get_queue_status(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get queue status for user or entire application (old interface).

        Args:
            user_id: Optional user ID to get specific user's status

        Returns:
            dict: Queue status information
        """
        if user_id is not None:
            # Get status for specific user
            workflow_type = self._user_workflow_types.get(user_id)

            if workflow_type == 'video':
                return await self.video_service.get_queue_status(user_id)
            else:
                # Default to image service
                return await self.image_service.get_queue_status(user_id)
        else:
            # Get application-wide status (combine both services)
            image_status = await self.image_service.get_queue_status(0)  # Dummy user_id
            video_status = await self.video_service.get_queue_status(0)

            return {
                'image': image_status,
                'video': video_status,
                'total_queued': image_status.get('queued', 0) + video_status.get('queued', 0),
                'total_processing': image_status.get('processing', 0) + video_status.get('processing', 0)
            }
