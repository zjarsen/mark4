"""Base workflow class for all processing workflows."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import json
import logging

logger = logging.getLogger('mark4_bot')


class BaseWorkflow(ABC):
    """Abstract base class for all workflow implementations."""

    def __init__(self, config, comfyui_service, file_service):
        """
        Initialize base workflow.

        Args:
            config: Configuration object
            comfyui_service: ComfyUI service instance
            file_service: File service instance
        """
        self.config = config
        self.comfyui_service = comfyui_service
        self.file_service = file_service

    @abstractmethod
    def get_workflow_filename(self) -> str:
        """
        Get the workflow JSON filename.

        Returns:
            Filename of workflow JSON (e.g., 'qwen_image_edit_final.json')
        """
        pass

    @abstractmethod
    def get_output_node_id(self) -> str:
        """
        Get the node ID that contains output image.

        Returns:
            Node ID as string (e.g., '27')
        """
        pass

    @abstractmethod
    async def prepare_workflow(self, **params) -> Dict:
        """
        Load and prepare workflow with parameters.

        Args:
            **params: Parameters to inject into workflow

        Returns:
            Workflow dictionary ready for queueing
        """
        pass

    @abstractmethod
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
        Handle workflow completion and deliver results.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            filename: Original filename
            outputs: Output dictionary from ComfyUI
            state_manager: State manager instance
            notification_service: Notification service instance
        """
        pass

    def load_workflow_json(self) -> Dict:
        """
        Load workflow JSON from file.

        Returns:
            Workflow dictionary

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            json.JSONDecodeError: If workflow JSON is invalid
        """
        workflow_path = self.config.WORKFLOWS_DIR / self.get_workflow_filename()

        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)

            logger.debug(f"Loaded workflow from {workflow_path}")
            return workflow

        except FileNotFoundError:
            logger.error(f"Workflow file not found: {workflow_path}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in workflow file {workflow_path}: {str(e)}")
            raise

    async def upload_image(self, local_path: str, filename: str):
        """
        Upload image to ComfyUI server.

        Args:
            local_path: Path to local image file
            filename: Filename to use on server

        Returns:
            Upload result from ComfyUI
        """
        return await self.comfyui_service.upload_image(local_path, filename)

    async def queue_workflow(self, **params) -> str:
        """
        Prepare and queue workflow.

        Args:
            **params: Parameters for workflow preparation

        Returns:
            prompt_id: Unique ID for tracking
        """
        workflow = await self.prepare_workflow(**params)
        prompt_id = await self.comfyui_service.queue_prompt(workflow)

        logger.info(
            f"Queued {self.__class__.__name__} workflow, "
            f"prompt_id: {prompt_id}"
        )

        return prompt_id

    def extract_output_image(self, outputs: Dict) -> Dict:
        """
        Extract output image info from outputs dictionary.

        Args:
            outputs: Outputs dictionary from ComfyUI

        Returns:
            Dictionary with image info (filename, etc.)

        Raises:
            ValueError: If output node or image not found
        """
        node_id = self.get_output_node_id()

        if node_id not in outputs:
            raise ValueError(f"Output node '{node_id}' not found in outputs")

        if 'images' not in outputs[node_id]:
            raise ValueError(f"No images in output node '{node_id}'")

        if not outputs[node_id]['images']:
            raise ValueError(f"Images array empty in output node '{node_id}'")

        return outputs[node_id]['images'][0]

    async def download_output_image(
        self,
        output_image_info: Dict,
        output_path: str
    ):
        """
        Download processed output image.

        Args:
            output_image_info: Dictionary with 'filename' key
            output_path: Local path to save image

        Raises:
            KeyError: If 'filename' not in output_image_info
        """
        if 'filename' not in output_image_info:
            raise KeyError("'filename' not found in output image info")

        filename = output_image_info['filename']
        await self.comfyui_service.download_image(filename, output_path)

        logger.info(f"Downloaded output image to {output_path}")
