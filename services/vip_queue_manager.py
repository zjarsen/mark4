"""VIP Queue Manager - Application-level priority queue for VIP users."""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Callable
from datetime import datetime

logger = logging.getLogger('mark4_bot')


@dataclass
class QueuedJob:
    """Represents a queued workflow job."""
    user_id: int
    workflow_data: Dict
    is_vip: bool
    queued_at: datetime
    callback: Callable


class VIPQueueManager:
    """Manages priority queue for VIP vs regular users."""

    def __init__(self, comfyui_service, max_comfyui_queue_size=10):
        """
        Initialize VIP queue manager.

        Args:
            comfyui_service: ComfyUI service instance for checking queue
            max_comfyui_queue_size: Max jobs to keep in ComfyUI queue
        """
        self.comfyui_service = comfyui_service
        self.max_comfyui_queue_size = max_comfyui_queue_size

        # Two separate queues
        self.vip_queue = deque()
        self.regular_queue = deque()

        # Track jobs currently submitted to ComfyUI
        self.submitted_jobs: Dict[str, QueuedJob] = {}

        # Background processor task
        self.processor_task: Optional[asyncio.Task] = None
        self.running = False

        logger.info("VIP Queue Manager initialized")

    async def start(self):
        """Start background queue processor."""
        if not self.running:
            self.running = True
            self.processor_task = asyncio.create_task(self._process_queue_loop())
            logger.info("VIP Queue Manager started")

    async def stop(self):
        """Stop background queue processor."""
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("VIP Queue Manager stopped")

    async def queue_job(
        self,
        user_id: int,
        workflow_data: Dict,
        is_vip: bool,
        callback: Callable
    ) -> str:
        """
        Queue a job for processing.

        Args:
            user_id: User ID
            workflow_data: Workflow dict ready for ComfyUI
            is_vip: True if user is 黑金VIP (priority)
            callback: Async function to call when job submitted

        Returns:
            job_id: Unique job identifier
        """
        job = QueuedJob(
            user_id=user_id,
            workflow_data=workflow_data,
            is_vip=is_vip,
            queued_at=datetime.now(),
            callback=callback
        )

        # Add to appropriate queue
        if is_vip:
            self.vip_queue.append(job)
            logger.info(f"Added VIP job for user {user_id} to priority queue")
        else:
            self.regular_queue.append(job)
            logger.info(f"Added regular job for user {user_id} to queue")

        # Trigger immediate processing check
        await self._process_queue()

        return f"job_{user_id}_{int(datetime.now().timestamp())}"

    async def _process_queue_loop(self):
        """Background task that processes queue every 3 seconds."""
        while self.running:
            try:
                await self._process_queue()
                await asyncio.sleep(3)  # Check every 3 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}")

    async def _process_queue(self):
        """Process queued jobs and submit to ComfyUI if space available."""
        try:
            # Check ComfyUI queue size
            queue_info = await self.comfyui_service.get_queue_info()
            current_size = len(queue_info.get('queue_pending', []))

            # Calculate available slots
            available_slots = self.max_comfyui_queue_size - current_size

            if available_slots <= 0:
                logger.debug("ComfyUI queue full, waiting...")
                return

            # Submit jobs: VIP first, then regular
            submitted = 0

            # Process VIP queue first
            while self.vip_queue and submitted < available_slots:
                job = self.vip_queue.popleft()
                await self._submit_job(job)
                submitted += 1

            # Process regular queue if VIP queue empty
            while self.regular_queue and submitted < available_slots:
                job = self.regular_queue.popleft()
                await self._submit_job(job)
                submitted += 1

            if submitted > 0:
                logger.info(f"Submitted {submitted} jobs to ComfyUI")

        except Exception as e:
            logger.error(f"Error processing queue: {str(e)}")

    async def _submit_job(self, job: QueuedJob):
        """Submit job to ComfyUI and call callback."""
        try:
            # Submit to ComfyUI
            prompt_id = await self.comfyui_service.queue_prompt(job.workflow_data)

            # Track submitted job
            self.submitted_jobs[prompt_id] = job

            # Call callback with prompt_id
            await job.callback(prompt_id)

            logger.info(
                f"Submitted {'VIP' if job.is_vip else 'regular'} job "
                f"for user {job.user_id}, prompt_id: {prompt_id}"
            )

        except Exception as e:
            logger.error(f"Error submitting job for user {job.user_id}: {str(e)}")

    def get_queue_stats(self) -> Dict:
        """Get current queue statistics."""
        return {
            'vip_queue_size': len(self.vip_queue),
            'regular_queue_size': len(self.regular_queue),
            'total_queued': len(self.vip_queue) + len(self.regular_queue),
            'submitted_jobs': len(self.submitted_jobs)
        }
