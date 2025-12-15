"""
Image Queue Manager

Manages priority queue for image workflows (undress, bra).
Extends QueueManagerBase with image-specific configuration.
"""

import logging
from services.queue_manager_base import QueueManagerBase

logger = logging.getLogger(__name__)


class ImageQueueManager(QueueManagerBase):
    """Queue manager for image workflows (undress, bra)"""

    def __init__(self, comfyui_service):
        """
        Initialize image queue manager.

        Args:
            comfyui_service: ComfyUIService instance for image server
        """
        super().__init__(
            comfyui_service=comfyui_service,
            max_comfyui_queue_size=1,  # Strict 1-at-a-time control
            check_interval=3            # Check every 3 seconds
        )
        self.server_name = "image"
        logger.info("ImageQueueManager initialized for image workflows")
