"""
Image workflow processors.

Each processor encapsulates the logic for a specific image processing workflow:
- Workflow loading and parameter injection
- Input validation
- Output extraction
- Cost calculation
"""

import json
import logging
from pathlib import Path
from typing import Optional

from ..base import WorkflowProcessor, WorkflowResult
from infrastructure.comfyui import ComfyUIClient

logger = logging.getLogger('mark4_bot')


class ImageUndressProcessor(WorkflowProcessor):
    """
    Processor for image undress workflow.

    Cost: 10 credits per use
    Input: Image file
    Output: Processed image
    """

    def __init__(self, comfyui_client: ComfyUIClient, file_service, workflow_path: Path, cost: int = 10):
        """
        Initialize image undress processor.

        Args:
            comfyui_client: ComfyUI client instance
            file_service: File service instance
            workflow_path: Path to workflow JSON file
            cost: Credit cost (default: 10)
        """
        super().__init__(comfyui_client, file_service, workflow_path, cost)
        self.workflow_type = 'image_undress'

    async def validate_input(self, input_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate input image.

        Args:
            input_path: Path to input image

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file exists
        if not Path(input_path).exists():
            return False, f"Input file not found: {input_path}"

        # Check file size (max 10MB)
        file_size = Path(input_path).stat().st_size
        if file_size > 10 * 1024 * 1024:
            return False, "Image too large (max 10MB)"

        return True, None

    def prepare_workflow(self, input_filename: str, user_id: int) -> dict:
        """
        Prepare workflow with input parameters.

        Args:
            input_filename: Name of uploaded input file
            user_id: User ID (for tracking)

        Returns:
            Workflow dictionary ready for ComfyUI
        """
        workflow = self._load_workflow()

        # Inject input filename into workflow
        # Note: This depends on workflow structure, adjust node IDs as needed
        if 'LoadImage' in workflow:
            workflow['LoadImage']['inputs']['image'] = input_filename
        elif '1' in workflow:  # Sometimes LoadImage is node "1"
            if workflow['1'].get('class_type') == 'LoadImage':
                workflow['1']['inputs']['image'] = input_filename

        logger.debug(f"Prepared undress workflow for user {user_id}: {input_filename}")
        return workflow

    async def process(self, input_filename: str, user_id: int) -> WorkflowResult:
        """
        Process image undress workflow.

        Args:
            input_filename: Name of uploaded input file
            user_id: User ID

        Returns:
            WorkflowResult with success/failure and output path
        """
        try:
            # Validate input
            is_valid, error = await self.validate_input(input_filename)
            if not is_valid:
                return WorkflowResult(
                    success=False,
                    error_message=error
                )

            # Prepare and queue workflow
            workflow = self.prepare_workflow(input_filename, user_id)
            prompt_id = await self.client.queue_prompt(workflow)

            # Wait for completion
            outputs = await self.client.wait_for_completion(prompt_id)

            # Extract output image
            output_path = await self.extract_output(outputs, user_id)

            if output_path:
                return WorkflowResult(
                    success=True,
                    output_path=output_path
                )
            else:
                return WorkflowResult(
                    success=False,
                    error_message="No output image found in workflow results"
                )

        except Exception as e:
            logger.error(f"Error processing undress workflow: {e}", exc_info=True)
            return WorkflowResult(
                success=False,
                error_message=str(e)
            )

    async def extract_output(self, outputs: dict, user_id: int) -> Optional[str]:
        """
        Extract output image from ComfyUI outputs.

        Args:
            outputs: ComfyUI outputs dictionary
            user_id: User ID

        Returns:
            Path to downloaded output file, or None if extraction failed
        """
        try:
            # Find the output node (usually SaveImage or similar)
            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    images = node_output['images']
                    if images:
                        # Get first image
                        image_info = images[0]
                        filename = image_info['filename']
                        subfolder = image_info.get('subfolder', '')

                        # Generate local output path
                        output_path = f"/tmp/{user_id}_{filename}"

                        # Download from ComfyUI
                        await self.client.download_file(
                            filename=filename,
                            output_path=output_path,
                            subfolder=subfolder,
                            file_type='output'
                        )

                        logger.info(f"Extracted output image for user {user_id}: {output_path}")
                        return output_path

            logger.error(f"No images found in outputs for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error extracting output for user {user_id}: {e}")
            return None


class PinkBraProcessor(WorkflowProcessor):
    """
    Processor for pink bra workflow (free feature).

    Cost: 0 credits (free)
    Input: Image file
    Output: Processed image with pink bra overlay
    Daily usage limit: 5 uses per non-VIP user
    """

    def __init__(self, comfyui_client: ComfyUIClient, file_service, workflow_path: Path, cost: int = 0):
        """
        Initialize pink bra processor.

        Args:
            comfyui_client: ComfyUI client instance
            file_service: File service instance
            workflow_path: Path to workflow JSON file
            cost: Credit cost (default: 0)
        """
        super().__init__(comfyui_client, file_service, workflow_path, cost)
        self.workflow_type = 'image_pink_bra'
        self.daily_limit = 5  # 5 uses per day for non-VIP

    async def validate_input(self, input_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate input image.

        Args:
            input_path: Path to input image

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file exists
        if not Path(input_path).exists():
            return False, f"Input file not found: {input_path}"

        # Check file size (max 10MB)
        file_size = Path(input_path).stat().st_size
        if file_size > 10 * 1024 * 1024:
            return False, "Image too large (max 10MB)"

        return True, None

    def prepare_workflow(self, input_filename: str, user_id: int) -> dict:
        """
        Prepare workflow with input parameters.

        Args:
            input_filename: Name of uploaded input file
            user_id: User ID (for tracking)

        Returns:
            Workflow dictionary ready for ComfyUI
        """
        workflow = self._load_workflow()

        # Inject input filename into workflow
        if 'LoadImage' in workflow:
            workflow['LoadImage']['inputs']['image'] = input_filename
        elif '1' in workflow:
            if workflow['1'].get('class_type') == 'LoadImage':
                workflow['1']['inputs']['image'] = input_filename

        logger.debug(f"Prepared pink bra workflow for user {user_id}: {input_filename}")
        return workflow

    async def process(self, input_filename: str, user_id: int) -> WorkflowResult:
        """
        Process pink bra workflow.

        Args:
            input_filename: Name of uploaded input file
            user_id: User ID

        Returns:
            WorkflowResult with success/failure and output path
        """
        try:
            # Validate input
            is_valid, error = await self.validate_input(input_filename)
            if not is_valid:
                return WorkflowResult(
                    success=False,
                    error_message=error
                )

            # Prepare and queue workflow
            workflow = self.prepare_workflow(input_filename, user_id)
            prompt_id = await self.client.queue_prompt(workflow)

            # Wait for completion
            outputs = await self.client.wait_for_completion(prompt_id)

            # Extract output image
            output_path = await self.extract_output(outputs, user_id)

            if output_path:
                return WorkflowResult(
                    success=True,
                    output_path=output_path
                )
            else:
                return WorkflowResult(
                    success=False,
                    error_message="No output image found in workflow results"
                )

        except Exception as e:
            logger.error(f"Error processing pink bra workflow: {e}", exc_info=True)
            return WorkflowResult(
                success=False,
                error_message=str(e)
            )

    async def extract_output(self, outputs: dict, user_id: int) -> Optional[str]:
        """
        Extract output image from ComfyUI outputs.

        Args:
            outputs: ComfyUI outputs dictionary
            user_id: User ID

        Returns:
            Path to downloaded output file, or None if extraction failed
        """
        try:
            # Find the output node
            for node_id, node_output in outputs.items():
                if 'images' in node_output:
                    images = node_output['images']
                    if images:
                        image_info = images[0]
                        filename = image_info['filename']
                        subfolder = image_info.get('subfolder', '')

                        # Generate local output path
                        output_path = f"/tmp/{user_id}_{filename}"

                        # Download from ComfyUI
                        await self.client.download_file(
                            filename=filename,
                            output_path=output_path,
                            subfolder=subfolder,
                            file_type='output'
                        )

                        logger.info(f"Extracted pink bra output for user {user_id}: {output_path}")
                        return output_path

            logger.error(f"No images found in pink bra outputs for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"Error extracting pink bra output for user {user_id}: {e}")
            return None
