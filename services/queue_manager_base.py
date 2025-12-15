"""
Base Queue Manager for Application-Layer Priority Queue System

This module provides the core queue management logic for ComfyUI job submission
with VIP priority support. It maintains two queues (VIP and regular) and submits
jobs to ComfyUI one at a time, tracking only our submitted jobs.
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)


@dataclass
class QueuedJob:
    """Represents a job in the application queue"""
    job_id: str                    # Unique job identifier (user_id + timestamp)
    user_id: int                   # Telegram user ID
    workflow: dict                 # ComfyUI workflow JSON
    prompt_id: Optional[str] = None  # ComfyUI prompt_id (set after submission)

    # Callbacks
    on_queued: Optional[Callable] = None      # Called when added to queue
    on_submitted: Optional[Callable] = None   # Called when submitted to ComfyUI
    on_completed: Optional[Callable] = None   # Called when job completes
    on_error: Optional[Callable] = None       # Called on error

    # Metadata (optional, for logging/debugging)
    workflow_type: str = "unknown"  # e.g., "image_undress", "video_douxiong"
    created_at: datetime = field(default_factory=datetime.utcnow)


class QueueManagerBase:
    """
    Base class for queue managers that handle VIP priority and controlled submission.

    Features:
    - Two-tier queue system (VIP and regular)
    - Strict 1-at-a-time submission to ComfyUI
    - Tracks only our submitted jobs (ignores other projects)
    - Automatic retry on submission failure
    - Completion detection via polling
    """

    def __init__(self, comfyui_service, max_comfyui_queue_size=1, check_interval=3):
        """
        Initialize queue manager.

        Args:
            comfyui_service: ComfyUIService instance for API calls
            max_comfyui_queue_size: Max jobs to have in ComfyUI (default: 1)
            check_interval: Seconds between queue checks (default: 3)
        """
        self.comfyui_service = comfyui_service
        self.max_comfyui_queue_size = max_comfyui_queue_size
        self.check_interval = check_interval

        # Two-tier queues
        self.vip_queue = deque()      # Black Gold VIP only
        self.regular_queue = deque()  # Everyone else (including regular VIP)

        # Track our submitted jobs
        self.submitted_jobs: Dict[str, QueuedJob] = {}  # {prompt_id: QueuedJob}
        self.current_job_id: Optional[str] = None       # Currently processing job's prompt_id

        # Background processor
        self.processing_task = None
        self.running = False
        self._lock = asyncio.Lock()  # Prevent race conditions

        logger.info(f"Initialized {self.__class__.__name__} with check_interval={check_interval}s")

    async def start(self):
        """Start the background queue processing loop"""
        if self.running:
            logger.warning(f"{self.__class__.__name__} already running")
            return

        self.running = True
        self.processing_task = asyncio.create_task(self._process_queue_loop())
        logger.info(f"{self.__class__.__name__} started")

    async def stop(self):
        """Stop the background queue processing loop"""
        if not self.running:
            return

        self.running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        logger.info(f"{self.__class__.__name__} stopped")

    async def queue_job(self, job: QueuedJob, is_vip: bool):
        """
        Add job to appropriate queue (VIP or regular).

        Args:
            job: QueuedJob instance
            is_vip: True for Black Gold VIP (priority queue)
        """
        async with self._lock:
            if is_vip:
                self.vip_queue.append(job)
                logger.info(f"Added VIP job {job.job_id} (user {job.user_id}, type: {job.workflow_type})")
            else:
                self.regular_queue.append(job)
                logger.info(f"Added regular job {job.job_id} (user {job.user_id}, type: {job.workflow_type})")

        # Trigger on_queued callback
        if job.on_queued:
            position = self._get_queue_position(job)
            try:
                await job.on_queued(position)
            except Exception as e:
                logger.error(f"Error in on_queued callback: {e}", exc_info=True)

    def _get_queue_position(self, job: QueuedJob) -> int:
        """
        Calculate job's position in APPLICATION queue.

        Returns:
            Position (1-indexed), includes currently processing task in position count
        """
        position = 1 if self.current_job_id else 0  # Start at 1 if job is processing (position 0 means next to be submitted)

        # Check VIP queue first (higher priority)
        for q_job in self.vip_queue:
            if q_job.job_id == job.job_id:
                return position if position > 0 else 1  # Return at least position 1
            position += 1

        # Check regular queue
        for q_job in self.regular_queue:
            if q_job.job_id == job.job_id:
                return position if position > 0 else 1  # Return at least position 1
            position += 1

        return position if position > 0 else 1  # Return at least position 1

    async def _process_queue_loop(self):
        """Background loop: check completion and submit next job"""
        logger.info(f"{self.__class__.__name__} background loop started")

        while self.running:
            try:
                # Check if current job completed
                if self.current_job_id:
                    completed = await self._check_job_completed(self.current_job_id)
                    if completed:
                        logger.info(f"Job {self.current_job_id} completed")
                        await self._handle_job_completion(self.current_job_id)
                        self.current_job_id = None

                # Submit next job if slot available
                if not self.current_job_id:
                    await self._submit_next_job()

            except Exception as e:
                logger.error(f"Queue processing error: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

        logger.info(f"{self.__class__.__name__} background loop stopped")

    async def _check_job_completed(self, prompt_id: str) -> bool:
        """
        Poll GET /history/{prompt_id} to check completion.

        Args:
            prompt_id: ComfyUI prompt ID

        Returns:
            True if job exists in history (completed)
        """
        try:
            history = await self.comfyui_service.get_history(prompt_id)
            return history is not None  # Job exists in history = completed
        except Exception as e:
            logger.warning(f"Error checking completion for {prompt_id}: {e}")
            return False

    async def _submit_next_job(self):
        """Pop next job from queues (VIP first) and submit to ComfyUI"""
        async with self._lock:
            job = None

            # Priority: VIP queue first
            if self.vip_queue:
                job = self.vip_queue.popleft()
                logger.info(f"Popped VIP job {job.job_id}")
            elif self.regular_queue:
                job = self.regular_queue.popleft()
                logger.info(f"Popped regular job {job.job_id}")

            if not job:
                return  # No jobs to submit

        # Submit to ComfyUI with retry logic (outside lock)
        success = await self._submit_with_retry(job)

        if success:
            self.current_job_id = job.prompt_id
            self.submitted_jobs[job.prompt_id] = job
            logger.info(f"Job {job.job_id} submitted successfully as {job.prompt_id}")

            # Trigger on_submitted callback
            if job.on_submitted:
                try:
                    await job.on_submitted(job.prompt_id)
                except Exception as e:
                    logger.error(f"Error in on_submitted callback: {e}", exc_info=True)
        else:
            logger.error(f"Job {job.job_id} failed to submit after retries")
            # Failed after retries: trigger error callback
            if job.on_error:
                try:
                    await job.on_error("Failed to submit job to ComfyUI after 3 attempts")
                except Exception as e:
                    logger.error(f"Error in on_error callback: {e}", exc_info=True)

    async def _submit_with_retry(self, job: QueuedJob, max_retries=2) -> bool:
        """
        Submit job with retry logic (retry 2 times on failure).

        Args:
            job: QueuedJob to submit
            max_retries: Number of retry attempts (default: 2)

        Returns:
            True if submission succeeded, False otherwise
        """
        for attempt in range(max_retries + 1):
            try:
                prompt_id = await self.comfyui_service.queue_prompt(job.workflow)
                job.prompt_id = prompt_id
                logger.info(f"Submit attempt {attempt + 1} succeeded: {job.job_id} -> {prompt_id}")
                return True
            except Exception as e:
                logger.warning(f"Submit attempt {attempt + 1} failed for {job.job_id}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1)  # Wait 1 second before retry

        return False  # All retries failed

    async def _handle_job_completion(self, prompt_id: str):
        """
        Handle completed job: retrieve results, trigger callback.

        Args:
            prompt_id: ComfyUI prompt ID of completed job
        """
        job = self.submitted_jobs.pop(prompt_id, None)
        if not job:
            logger.warning(f"Completed job {prompt_id} not found in submitted_jobs")
            return

        try:
            # Retrieve result from ComfyUI history
            history = await self.comfyui_service.get_history(prompt_id)

            logger.info(f"Job {job.job_id} (prompt {prompt_id}) completed successfully")

            # Trigger completion callback
            if job.on_completed:
                await job.on_completed(prompt_id, history)

        except Exception as e:
            logger.error(f"Error handling completion for {prompt_id}: {e}", exc_info=True)
            if job.on_error:
                try:
                    await job.on_error(f"Error retrieving results: {str(e)}")
                except Exception as callback_error:
                    logger.error(f"Error in on_error callback: {callback_error}", exc_info=True)

    def get_queue_status(self) -> dict:
        """
        Return current queue status for user display.

        Returns:
            Dict with queue sizes and processing status
        """
        return {
            'vip_queue_size': len(self.vip_queue),
            'regular_queue_size': len(self.regular_queue),
            'processing': bool(self.current_job_id),
            'total_queued': len(self.vip_queue) + len(self.regular_queue),
            'current_job_id': self.current_job_id
        }

    def _get_job_position(self, job_id: str) -> Optional[int]:
        """
        Get position of a specific job in the queue by job_id.

        Args:
            job_id: The job_id to find

        Returns:
            Position (1-indexed) if found, None if not in queue
        """
        # Find job in VIP queue
        for job in self.vip_queue:
            if job.job_id == job_id:
                return self._get_queue_position(job)

        # Find job in regular queue
        for job in self.regular_queue:
            if job.job_id == job_id:
                return self._get_queue_position(job)

        # Not found in either queue
        return None

    def get_queue_info(self) -> str:
        """Get human-readable queue status string"""
        status = self.get_queue_status()
        return (f"VIP: {status['vip_queue_size']}, "
                f"Regular: {status['regular_queue_size']}, "
                f"Processing: {'Yes' if status['processing'] else 'No'}")
