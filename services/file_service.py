"""File management service for uploads, downloads, and cleanup."""

from pathlib import Path
import time
from typing import Optional
import logging

logger = logging.getLogger('mark4_bot')


class FileService:
    """Service for handling all file operations."""

    def __init__(self, config):
        """
        Initialize file service.

        Args:
            config: Configuration object
        """
        self.config = config
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.config.USER_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.config.COMFYUI_RETRIEVE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Ensured directories exist: "
            f"uploads={self.config.USER_UPLOADS_DIR}, "
            f"retrieve={self.config.COMFYUI_RETRIEVE_DIR}"
        )

    def generate_filename(self, user_id: int, extension: str) -> str:
        """
        Generate unique filename for user upload.

        Args:
            user_id: Telegram user ID
            extension: File extension (without dot)

        Returns:
            Filename in format: {user_id}_{timestamp}.{extension}
        """
        timestamp = int(time.time())
        filename = f"{user_id}_{timestamp}.{extension}"
        logger.debug(f"Generated filename: {filename}")
        return filename

    def is_valid_image_format(self, filename: str) -> bool:
        """
        Check if file has valid image extension.

        Args:
            filename: Name of file to check

        Returns:
            True if extension is in allowed formats
        """
        ext = Path(filename).suffix.lower().lstrip('.')
        is_valid = ext in self.config.ALLOWED_IMAGE_FORMATS
        logger.debug(f"File {filename} format valid: {is_valid}")
        return is_valid

    async def download_telegram_photo(
        self,
        photo,
        user_id: int,
        bot
    ) -> str:
        """
        Download photo from Telegram servers.

        Args:
            photo: Telegram PhotoSize object
            user_id: Telegram user ID
            bot: Telegram Bot instance

        Returns:
            Local file path where photo was saved
        """
        import asyncio

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Getting file info for user {user_id} (attempt {attempt + 1}/{max_retries})")
                file = await bot.get_file(photo.file_id)

                logger.info(f"File ID: {photo.file_id}, Size: {photo.file_size}, Path: {file.file_path}")

                filename = self.generate_filename(user_id, 'jpg')
                local_path = self.config.USER_UPLOADS_DIR / filename

                logger.info(f"Downloading to: {local_path}")
                await file.download_to_drive(str(local_path))

                logger.info(f"Successfully downloaded photo for user {user_id} to {local_path}")
                return str(local_path)

            except Exception as e:
                logger.error(
                    f"Error downloading photo for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to download photo after {max_retries} attempts")
                    raise

    async def download_telegram_document(
        self,
        document,
        user_id: int,
        bot
    ) -> str:
        """
        Download document from Telegram servers.

        Args:
            document: Telegram Document object
            user_id: Telegram user ID
            bot: Telegram Bot instance

        Returns:
            Local file path where document was saved

        Raises:
            ValueError: If document format is invalid
        """
        import asyncio

        # Validate format first
        if not self.is_valid_image_format(document.file_name):
            raise ValueError(f"Invalid image format: {document.file_name}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Getting document info for user {user_id} (attempt {attempt + 1}/{max_retries})")
                file = await bot.get_file(document.file_id)

                logger.info(f"File ID: {document.file_id}, Name: {document.file_name}, Size: {document.file_size}")

                ext = Path(document.file_name).suffix.lstrip('.')
                filename = self.generate_filename(user_id, ext)
                local_path = self.config.USER_UPLOADS_DIR / filename

                logger.info(f"Downloading to: {local_path}")
                await file.download_to_drive(str(local_path))

                logger.info(f"Successfully downloaded document for user {user_id} to {local_path}")
                return str(local_path)

            except Exception as e:
                logger.error(
                    f"Error downloading document for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to download document after {max_retries} attempts")
                    raise

    def get_output_path(self, original_filename: str) -> str:
        """
        Generate output path for processed image.

        Args:
            original_filename: Original upload filename

        Returns:
            Path to save processed output
        """
        base_name = Path(original_filename).stem
        output_filename = f"{base_name}_complete.jpg"
        output_path = self.config.COMFYUI_RETRIEVE_DIR / output_filename
        return str(output_path)

    def delete_file(self, filepath: str) -> bool:
        """
        Delete a file if it exists.

        Args:
            filepath: Path to file to delete

        Returns:
            True if file was deleted, False if it didn't exist
        """
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {filepath}")
                return True
            else:
                logger.debug(f"File not found for deletion: {filepath}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {str(e)}")
            return False

    def delete_user_upload(self, filename: str) -> bool:
        """
        Delete file from user uploads directory.

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted successfully
        """
        filepath = self.config.USER_UPLOADS_DIR / filename
        return self.delete_file(str(filepath))

    def delete_processed_output(self, filename: str) -> bool:
        """
        Delete file from ComfyUI retrieve directory.

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted successfully
        """
        filepath = self.config.COMFYUI_RETRIEVE_DIR / filename
        return self.delete_file(str(filepath))

    def cleanup_user_files(self, user_id: int):
        """
        Delete all files associated with a specific user.

        Args:
            user_id: Telegram user ID
        """
        pattern = f"{user_id}_*"

        # Clean uploads directory
        deleted_count = 0
        for file in self.config.USER_UPLOADS_DIR.glob(pattern):
            if file.is_file():
                file.unlink()
                deleted_count += 1

        # Clean retrieve directory
        for file in self.config.COMFYUI_RETRIEVE_DIR.glob(pattern):
            if file.is_file():
                file.unlink()
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} files for user {user_id}")

    def get_file_size(self, filepath: str) -> Optional[int]:
        """
        Get size of file in bytes.

        Args:
            filepath: Path to file

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        try:
            path = Path(filepath)
            if path.exists():
                return path.stat().st_size
            return None

        except Exception as e:
            logger.error(f"Error getting file size for {filepath}: {str(e)}")
            return None

    def list_user_files(self, user_id: int) -> dict:
        """
        List all files for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with 'uploads' and 'processed' lists of filenames
        """
        pattern = f"{user_id}_*"

        uploads = [
            f.name for f in self.config.USER_UPLOADS_DIR.glob(pattern)
            if f.is_file()
        ]

        processed = [
            f.name for f in self.config.COMFYUI_RETRIEVE_DIR.glob(pattern)
            if f.is_file()
        ]

        return {
            'uploads': uploads,
            'processed': processed
        }

    def get_directory_size(self, directory: Path) -> int:
        """
        Get total size of all files in directory.

        Args:
            directory: Path to directory

        Returns:
            Total size in bytes
        """
        try:
            total_size = sum(
                f.stat().st_size for f in directory.glob('**/*') if f.is_file()
            )
            return total_size

        except Exception as e:
            logger.error(f"Error calculating directory size: {str(e)}")
            return 0

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        return {
            'uploads_dir_size': self.get_directory_size(self.config.USER_UPLOADS_DIR),
            'retrieve_dir_size': self.get_directory_size(self.config.COMFYUI_RETRIEVE_DIR),
            'uploads_count': len(list(self.config.USER_UPLOADS_DIR.glob('*'))),
            'retrieve_count': len(list(self.config.COMFYUI_RETRIEVE_DIR.glob('*')))
        }
