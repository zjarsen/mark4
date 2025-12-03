"""ComfyUI API integration service."""

import aiohttp
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger('mark4_bot')


class ComfyUIService:
    """Service for interacting with ComfyUI server API."""

    def __init__(self, config, workflow_type: str):
        """
        Initialize ComfyUI service.

        Args:
            config: Configuration object
            workflow_type: Workflow type ('image_undress', 'video_douxiong', 'video_liujing', 'video_shejing')
        """
        self.config = config
        self.workflow_type = workflow_type

        # Get workflow-specific URLs
        urls = config.get_workflow_urls(workflow_type)
        self.upload_url = urls['upload_url']
        self.prompt_url = urls['prompt_url']
        self.queue_url = urls['queue_url']
        self.history_url = urls['history_url']
        self.view_url = urls['view_url']

        # Extract base server URL for other endpoints
        self.server_url = config.COMFYUI_IMAGE_UNDRESS_SERVER if workflow_type == 'image_undress' else \
                         config.COMFYUI_VIDEO_DOUXIONG_SERVER if workflow_type == 'video_douxiong' else \
                         config.COMFYUI_VIDEO_LIUJING_SERVER if workflow_type == 'video_liujing' else \
                         config.COMFYUI_VIDEO_SHEJING_SERVER

    async def upload_image(self, local_path: str, filename: str) -> Dict:
        """
        Upload image to ComfyUI server.

        Args:
            local_path: Path to local image file
            filename: Filename to use on server

        Returns:
            Response JSON from server

        Raises:
            Exception: If upload fails
        """
        try:
            # Disable SSL verification for servers with certificate issues
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                with open(local_path, 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field(
                        'image',
                        f,
                        filename=filename,
                        content_type='image/jpeg'
                    )

                    logger.info(f"Uploading to: {self.upload_url}")

                    async with session.post(self.upload_url, data=form) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error(
                                f"Upload failed - Status: {resp.status}, "
                                f"URL: {self.upload_url}, "
                                f"Response: {error_text[:200]}"
                            )
                            raise Exception(
                                f"Upload failed with status {resp.status}: {error_text}"
                            )
                        result = await resp.json()
                        logger.info(f"Successfully uploaded image: {filename}")
                        return result

        except Exception as e:
            logger.error(f"Error uploading image {filename}: {str(e)}")
            raise

    async def queue_prompt(self, workflow: Dict) -> str:
        """
        Queue a workflow for processing.

        Args:
            workflow: Workflow dictionary (from JSON file with parameters injected)

        Returns:
            prompt_id: Unique ID for tracking this processing request

        Raises:
            Exception: If queueing fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                prompt_data = {"prompt": workflow}

                async with session.post(
                    self.prompt_url,
                    json=prompt_data
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(
                            f"Queue failed with status {resp.status}: {error_text}"
                        )

                    result = await resp.json()
                    prompt_id = result.get('prompt_id')

                    if not prompt_id:
                        raise Exception("No prompt_id in response")

                    logger.info(f"Successfully queued workflow, prompt_id: {prompt_id}")
                    return prompt_id

        except Exception as e:
            logger.error(f"Error queueing prompt: {str(e)}")
            raise

    async def get_queue_info(self) -> Dict:
        """
        Get current queue information from ComfyUI server.

        Returns:
            Dictionary with keys:
                - pending: List of pending queue items
                - running: List of running queue items
                - total: Total number of items in queue

        Raises:
            Exception: If request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.queue_url) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to get queue info: {resp.status}")

                    data = await resp.json()
                    pending = data.get('queue_pending', [])
                    running = data.get('queue_running', [])

                    return {
                        'pending': pending,
                        'running': running,
                        'total': len(pending) + len(running)
                    }

        except Exception as e:
            logger.error(f"Error getting queue info: {str(e)}")
            raise

    async def get_queue_position(self, prompt_id: str) -> Tuple[int, int]:
        """
        Get position of a specific prompt in the queue.

        Args:
            prompt_id: The prompt ID to find

        Returns:
            Tuple of (position, total_queue_size)
            - position: 1-indexed position (0 if not found/completed)
            - total: Total items in queue

        Raises:
            Exception: If request fails
        """
        try:
            queue_info = await self.get_queue_info()

            # Check pending queue
            for idx, item in enumerate(queue_info['pending']):
                # Queue item format: [queue_number, prompt_id, ...]
                if len(item) > 1 and item[1] == prompt_id:
                    position = idx + 1
                    logger.debug(
                        f"Found prompt {prompt_id} at position {position} "
                        f"of {queue_info['total']}"
                    )
                    return position, queue_info['total']

            # Check running queue
            if queue_info['running']:
                for item in queue_info['running']:
                    if len(item) > 1 and item[1] == prompt_id:
                        logger.debug(f"Prompt {prompt_id} is currently running")
                        return 0, queue_info['total']  # Return 0 to indicate running (not waiting in queue)

            # Not found - either completed or doesn't exist
            logger.debug(f"Prompt {prompt_id} not in queue (completed or not found)")
            return 0, queue_info['total']

        except Exception as e:
            logger.error(f"Error getting queue position for {prompt_id}: {str(e)}")
            # Return -1 to indicate error
            return -1, -1

    async def check_completion(self, prompt_id: str) -> Optional[Dict]:
        """
        Check if processing is complete and return outputs.

        Args:
            prompt_id: The prompt ID to check

        Returns:
            Dictionary of outputs if complete, None if still processing

        Raises:
            Exception: If request fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.history_url}/{prompt_id}"

                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"Failed to check completion for {prompt_id}: {resp.status}"
                        )
                        return None

                    history = await resp.json()

                    if prompt_id in history:
                        outputs = history[prompt_id].get('outputs', {})
                        logger.info(f"Processing completed for prompt {prompt_id}")
                        return outputs

                    return None

        except Exception as e:
            logger.error(f"Error checking completion for {prompt_id}: {str(e)}")
            return None

    async def download_image(
        self,
        filename: str,
        output_path: str,
        subfolder: str = "",
        file_type: str = "output"
    ):
        """
        Download processed image/video from ComfyUI server.

        Args:
            filename: Filename on ComfyUI server
            output_path: Local path to save file
            subfolder: Subfolder location (default: "")
            file_type: File type - "output" or "temp" (default: "output")

        Raises:
            Exception: If download fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Include subfolder and type in URL for ComfyUI compatibility
                url = f"{self.view_url}?filename={filename}&subfolder={subfolder}&type={file_type}"

                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise Exception(
                            f"Download failed with status {resp.status}"
                        )

                    with open(output_path, 'wb') as f:
                        f.write(await resp.read())

                    logger.info(
                        f"Downloaded {filename} (subfolder={subfolder}, type={file_type}) "
                        f"to {output_path}"
                    )

        except Exception as e:
            logger.error(f"Error downloading {filename}: {str(e)}")
            raise

    async def get_system_stats(self) -> Optional[Dict]:
        """
        Get system statistics from ComfyUI server (if available).

        Returns:
            Dictionary with system stats or None if unavailable
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.server_url}/system_stats"

                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None

        except Exception as e:
            logger.debug(f"System stats not available: {str(e)}")
            return None

    async def cancel_prompt(self, prompt_id: str) -> bool:
        """
        Cancel a queued or running prompt (if ComfyUI supports it).

        Args:
            prompt_id: The prompt ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.server_url}/interrupt"
                # Some ComfyUI versions might have different cancel endpoints
                async with session.post(url) as resp:
                    if resp.status == 200:
                        logger.info(f"Cancelled prompt {prompt_id}")
                        return True
                    return False

        except Exception as e:
            logger.error(f"Error cancelling prompt {prompt_id}: {str(e)}")
            return False
