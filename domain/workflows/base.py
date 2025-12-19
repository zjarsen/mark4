"""
Base classes for workflow domain.

Provides common functionality for all workflow types.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger('mark4_bot')


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    prompt_id: Optional[str] = None


class WorkflowProcessor(ABC):
    """
    Abstract base class for workflow processors.

    Each processor handles a specific workflow type (e.g., undress, bra, video style).
    """

    # Subclasses should define these
    feature_type: str = ""  # Feature type for tracking

    def __init__(self, comfyui_client, file_service, workflow_path=None, cost=0.0):
        """
        Initialize processor.

        Args:
            comfyui_client: ComfyUI client instance
            file_service: File service instance
            workflow_path: Path to workflow JSON file (optional)
            cost: Credit cost per use (default: 0.0)
        """
        self.comfyui = comfyui_client
        self.client = comfyui_client  # Alias for backward compatibility
        self.files = file_service
        self.workflow_file = workflow_path or ""
        self.cost = cost

    def _load_workflow(self) -> dict:
        """
        Load workflow JSON from file.

        Returns:
            Workflow dictionary

        Raises:
            FileNotFoundError: If workflow file doesn't exist
        """
        import json
        from pathlib import Path

        workflow_path = Path(self.workflow_file)
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

        with open(workflow_path, 'r') as f:
            return json.load(f)

    @abstractmethod
    async def process(self, input_path: str, user_id: int) -> WorkflowResult:
        """
        Process input file and return result.

        Args:
            input_path: Path to input file
            user_id: User ID for tracking

        Returns:
            WorkflowResult with output path or error
        """
        raise NotImplementedError

    @abstractmethod
    async def validate_input(self, input_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate input file.

        Args:
            input_path: Path to input file

        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError


class BaseWorkflowService(ABC):
    """
    Abstract base class for workflow services.

    Provides common workflow orchestration logic.
    """

    def __init__(
        self,
        credit_service,
        state_manager,
        notification_service,
        file_service
    ):
        """
        Initialize workflow service.

        Args:
            credit_service: CreditService instance
            state_manager: StateManager instance
            notification_service: NotificationService instance
            file_service: FileService instance
        """
        self.credits = credit_service
        self.state = state_manager
        self.notifier = notification_service
        self.files = file_service

    async def _send_queue_position_message(
        self,
        bot,
        user_id: int,
        position: int,
        job_id: str = None
    ):
        """
        Send queue position update to user.

        Args:
            bot: Telegram bot instance
            user_id: User ID
            position: Position in queue (0 = processing, 1+ = waiting)
            job_id: Job ID for tracking
        """
        if position == 0:
            message_text = "🔄 正在处理中..."
        else:
            message_text = f"⏳ 排队中...\n\n当前位置：第 {position} 位"

        try:
            # Delete old queue message if exists
            if self.state.has_queue_message(user_id):
                old_msg = self.state.get_queue_message(user_id)
                try:
                    await bot.delete_message(
                        chat_id=old_msg.chat_id,
                        message_id=old_msg.message_id
                    )
                except Exception as e:
                    logger.debug(f"Could not delete old queue message: {e}")
                self.state.remove_queue_message(user_id)

            # Send new queue position message
            message = await bot.send_message(
                chat_id=user_id,
                text=message_text
            )
            self.state.set_queue_message(user_id, message)
            logger.debug(f"Sent queue position {position} to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending queue position message: {e}")

    async def _send_processing_message(self, bot, user_id: int):
        """
        Send processing started message.

        Args:
            bot: Telegram bot instance
            user_id: User ID
        """
        message_text = "🔄 开始处理..."
        try:
            message = await bot.send_message(
                chat_id=user_id,
                text=message_text
            )
            self.state.set_queue_message(user_id, message)
            logger.debug(f"Sent processing message to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending processing message: {e}")

    async def _delete_queue_messages(self, bot, user_id: int):
        """
        Delete queue-related messages.

        Args:
            bot: Telegram bot instance
            user_id: User ID
        """
        if self.state.has_queue_message(user_id):
            try:
                queue_msg = self.state.get_queue_message(user_id)
                await bot.delete_message(
                    chat_id=queue_msg.chat_id,
                    message_id=queue_msg.message_id
                )
            except Exception as e:
                logger.debug(f"Could not delete queue message: {e}")
            finally:
                self.state.remove_queue_message(user_id)
