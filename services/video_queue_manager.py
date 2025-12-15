"""
Video Queue Manager

Manages priority queue for video workflows (douxiong, liujing, shejing).
Extends QueueManagerBase with video-specific configuration.
"""

import logging
from services.queue_manager_base import QueueManagerBase

logger = logging.getLogger(__name__)


class VideoQueueManager(QueueManagerBase):
    """Queue manager for video workflows (douxiong, liujing, shejing)"""

    def __init__(self, comfyui_service):
        """
        Initialize video queue manager.

        Args:
            comfyui_service: ComfyUIService instance for video server
        """
        super().__init__(
            comfyui_service=comfyui_service,
            max_comfyui_queue_size=1,  # Strict 1-at-a-time control
            check_interval=3            # Check every 3 seconds
        )
        self.server_name = "video"
        logger.info("VideoQueueManager initialized for video workflows")
