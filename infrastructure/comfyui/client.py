"""
ComfyUI API client with improved async I/O and error handling.

This refactored version provides:
- Specific exception types (no more generic Exception)
- Session reuse for better performance
- Proper timeout handling
- Better error messages with context
- Non-blocking I/O operations
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Tuple, Optional
from pathlib import Path

from .exceptions import (
    ConnectionError,
    UploadError,
    QueueError,
    ProcessingError,
    DownloadError,
    TimeoutError,
    InvalidResponseError
)

logger = logging.getLogger('mark4_bot')


class ComfyUIClient:
    """
    Async client for ComfyUI server API.

    Features:
    - Persistent aiohttp session (connection pooling)
    - Specific exception types for better error handling
    - Timeout support for all operations
    - Proper resource cleanup
    """

    def __init__(
        self,
        server_url: str,
        timeout_seconds: int = 300,
        disable_ssl_verify: bool = False
    ):
        """
        Initialize ComfyUI client.

        Args:
            server_url: Base ComfyUI server URL (e.g., "http://localhost:8188")
            timeout_seconds: Default timeout for operations (default: 300s)
            disable_ssl_verify: Disable SSL verification (for self-signed certs)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.disable_ssl_verify = disable_ssl_verify

        # Lazy-initialized session (created on first use)
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        logger.info(
            f"Initialized ComfyUI client for {server_url} "
            f"(timeout={timeout_seconds}s, ssl_verify={not disable_ssl_verify})"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session (lazy initialization with connection pooling)."""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    # Create connector with SSL settings
                    connector = aiohttp.TCPConnector(
                        ssl=False if self.disable_ssl_verify else None,
                        limit=10,  # Connection pool size
                        ttl_dns_cache=300  # DNS cache TTL
                    )

                    # Create timeout config
                    timeout = aiohttp.ClientTimeout(
                        total=self.timeout_seconds,
                        connect=30,  # 30s to establish connection
                        sock_read=60  # 60s between reads
                    )

                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout
                    )
                    logger.debug("Created new aiohttp session")

        return self._session

    async def close(self):
        """Close aiohttp session and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Closed ComfyUI client session")

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    # Upload Operations

    async def upload_image(
        self,
        local_path: str,
        filename: str = None,
        overwrite: bool = True
    ) -> str:
        """
        Upload image to ComfyUI server.

        Args:
            local_path: Path to local image file
            filename: Filename to use on server (defaults to basename of local_path)
            overwrite: Whether to overwrite existing file

        Returns:
            Uploaded filename on server

        Raises:
            UploadError: If upload fails
            ConnectionError: If connection fails
        """
        try:
            # Default filename to basename
            if filename is None:
                filename = Path(local_path).name

            session = await self._get_session()
            upload_url = f"{self.server_url}/upload/image"

            # Prepare multipart form data
            with open(local_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field(
                    'image',
                    f,
                    filename=filename,
                    content_type='image/jpeg'
                )
                form.add_field('overwrite', 'true' if overwrite else 'false')

                logger.info(f"Uploading {filename} to {upload_url}")

                try:
                    async with session.post(upload_url, data=form) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            logger.error(
                                f"Upload failed - Status: {resp.status}, "
                                f"Response: {error_text[:200]}"
                            )
                            raise UploadError(filename, resp.status, error_text)

                        result = await resp.json()
                        uploaded_name = result.get('name', filename)
                        logger.info(f"Successfully uploaded: {uploaded_name}")
                        return uploaded_name

                except asyncio.TimeoutError as e:
                    raise TimeoutError('upload', self.timeout_seconds) from e
                except aiohttp.ClientError as e:
                    raise ConnectionError(upload_url, str(e)) from e

        except (UploadError, ConnectionError, TimeoutError):
            raise  # Re-raise our custom exceptions
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
            raise UploadError(filename, response=str(e)) from e

    # Queue Operations

    async def queue_prompt(self, workflow: Dict) -> str:
        """
        Queue a workflow for processing.

        Args:
            workflow: Workflow dictionary (JSON with parameters)

        Returns:
            prompt_id: Unique ID for tracking this request

        Raises:
            QueueError: If queueing fails
            ConnectionError: If connection fails
        """
        try:
            session = await self._get_session()
            prompt_url = f"{self.server_url}/prompt"
            prompt_data = {"prompt": workflow}

            logger.debug(f"Queueing workflow to {prompt_url}")

            try:
                async with session.post(prompt_url, json=prompt_data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise QueueError('queue', error_text, resp.status)

                    result = await resp.json()
                    prompt_id = result.get('prompt_id')

                    if not prompt_id:
                        raise InvalidResponseError(
                            prompt_url,
                            "response with 'prompt_id'",
                            str(result)
                        )

                    logger.info(f"Successfully queued workflow, prompt_id: {prompt_id}")
                    return prompt_id

            except asyncio.TimeoutError as e:
                raise TimeoutError('queue', self.timeout_seconds) from e
            except aiohttp.ClientError as e:
                raise ConnectionError(prompt_url, str(e)) from e

        except (QueueError, ConnectionError, TimeoutError, InvalidResponseError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error queueing prompt: {e}")
            raise QueueError('queue', str(e)) from e

    async def get_queue_info(self) -> Dict:
        """
        Get current queue information.

        Returns:
            Dictionary with keys:
                - pending: List of pending queue items
                - running: List of running queue items
                - total: Total number of items

        Raises:
            QueueError: If request fails
        """
        try:
            session = await self._get_session()
            queue_url = f"{self.server_url}/queue"

            try:
                async with session.get(queue_url) as resp:
                    if resp.status != 200:
                        raise QueueError('get_info', f"Status {resp.status}", resp.status)

                    data = await resp.json()
                    pending = data.get('queue_pending', [])
                    running = data.get('queue_running', [])

                    return {
                        'pending': pending,
                        'running': running,
                        'total': len(pending) + len(running)
                    }

            except asyncio.TimeoutError as e:
                raise TimeoutError('get_queue_info', self.timeout_seconds) from e
            except aiohttp.ClientError as e:
                raise ConnectionError(queue_url, str(e)) from e

        except (QueueError, ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting queue info: {e}")
            raise QueueError('get_info', str(e)) from e

    async def get_queue_position(self, prompt_id: str) -> Tuple[int, int]:
        """
        Get position of a specific prompt in the queue.

        Args:
            prompt_id: The prompt ID to find

        Returns:
            Tuple of (position, total_queue_size)
            - position: 1-indexed position (0 if running/completed)
            - total: Total items in queue

        Raises:
            QueueError: If request fails
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
                        return 0, queue_info['total']

            # Not found - completed or doesn't exist
            logger.debug(f"Prompt {prompt_id} not in queue (completed or not found)")
            return 0, queue_info['total']

        except (QueueError, ConnectionError, TimeoutError):
            logger.error(f"Error getting queue position for {prompt_id}")
            return -1, -1  # Return -1 to indicate error

    # History Operations

    async def get_history(self, prompt_id: str) -> Optional[Dict]:
        """
        Get history entry for a specific prompt.

        Args:
            prompt_id: The prompt ID to check

        Returns:
            Dictionary with history entry if exists, None if not found

        Raises:
            ConnectionError: If connection fails
        """
        try:
            session = await self._get_session()
            history_url = f"{self.server_url}/history/{prompt_id}"

            try:
                async with session.get(history_url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"Failed to get history for {prompt_id}: {resp.status}"
                        )
                        return None

                    history = await resp.json()

                    if prompt_id in history:
                        return history[prompt_id]

                    return None

            except asyncio.TimeoutError as e:
                logger.warning(f"Timeout getting history for {prompt_id}")
                return None
            except aiohttp.ClientError as e:
                raise ConnectionError(history_url, str(e)) from e

        except ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting history for {prompt_id}: {e}")
            return None

    async def check_completion(self, prompt_id: str) -> Optional[Dict]:
        """
        Check if processing is complete and return outputs.

        Args:
            prompt_id: The prompt ID to check

        Returns:
            Dictionary of outputs if complete, None if still processing

        Raises:
            ConnectionError: If connection fails
        """
        history_entry = await self.get_history(prompt_id)

        if history_entry:
            outputs = history_entry.get('outputs', {})
            logger.info(f"Processing completed for prompt {prompt_id}")
            return outputs

        return None

    # Download Operations

    async def download_file(
        self,
        filename: str,
        output_path: str,
        subfolder: str = "",
        file_type: str = "output"
    ):
        """
        Download processed file from ComfyUI server.

        Args:
            filename: Filename on ComfyUI server
            output_path: Local path to save file
            subfolder: Subfolder location (default: "")
            file_type: File type - "output" or "temp" (default: "output")

        Raises:
            DownloadError: If download fails
            ConnectionError: If connection fails
        """
        try:
            session = await self._get_session()
            view_url = f"{self.server_url}/view"

            # Build query parameters
            params = {
                'filename': filename,
                'subfolder': subfolder,
                'type': file_type
            }

            logger.info(
                f"Downloading {filename} (subfolder={subfolder}, type={file_type})"
            )

            try:
                async with session.get(view_url, params=params) as resp:
                    if resp.status != 200:
                        raise DownloadError(filename, resp.status, subfolder)

                    # Stream download to file
                    with open(output_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)

                    logger.info(f"Downloaded {filename} to {output_path}")

            except asyncio.TimeoutError as e:
                raise TimeoutError('download', self.timeout_seconds) from e
            except aiohttp.ClientError as e:
                raise ConnectionError(view_url, str(e)) from e

        except (DownloadError, ConnectionError, TimeoutError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            raise DownloadError(filename, response=str(e)) from e

    # System Operations

    async def get_system_stats(self) -> Optional[Dict]:
        """
        Get system statistics from ComfyUI server (if available).

        Returns:
            Dictionary with system stats or None if unavailable
        """
        try:
            session = await self._get_session()
            stats_url = f"{self.server_url}/system_stats"

            async with session.get(stats_url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None

        except Exception as e:
            logger.debug(f"System stats not available: {e}")
            return None

    async def interrupt(self) -> bool:
        """
        Interrupt currently running workflow.

        Returns:
            True if interrupted successfully, False otherwise
        """
        try:
            session = await self._get_session()
            interrupt_url = f"{self.server_url}/interrupt"

            async with session.post(interrupt_url) as resp:
                if resp.status == 200:
                    logger.info("Interrupted running workflow")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error interrupting workflow: {e}")
            return False

    async def cancel_prompt(self, prompt_id: str) -> bool:
        """
        Cancel a specific queued prompt.

        Args:
            prompt_id: The prompt ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            session = await self._get_session()
            queue_url = f"{self.server_url}/queue"

            # Delete from queue
            data = {"delete": [prompt_id]}
            async with session.post(queue_url, json=data) as resp:
                if resp.status == 200:
                    logger.info(f"Cancelled prompt {prompt_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error cancelling prompt {prompt_id}: {e}")
            return False

    # Utility Methods

    async def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 2.0,
        max_wait: int = None
    ) -> Dict:
        """
        Wait for workflow completion (blocking).

        Args:
            prompt_id: The prompt ID to wait for
            poll_interval: Seconds between polls (default: 2.0)
            max_wait: Maximum seconds to wait (default: self.timeout_seconds)

        Returns:
            Dictionary of outputs when complete

        Raises:
            TimeoutError: If max_wait exceeded
            ProcessingError: If processing fails
        """
        if max_wait is None:
            max_wait = self.timeout_seconds

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise TimeoutError('processing', max_wait, prompt_id)

            # Check completion
            outputs = await self.check_completion(prompt_id)
            if outputs is not None:
                return outputs

            # Check for errors in queue
            queue_info = await self.get_queue_info()
            # If not in queue and not in history, might be an error
            # This is a simplification - actual error detection might need more logic

            await asyncio.sleep(poll_interval)

    def __repr__(self) -> str:
        """String representation."""
        return f"ComfyUIClient(server_url={self.server_url})"
