"""
File management service for uploads, downloads, and cleanup.

This refactored version provides:
- Better error handling with specific exceptions
- Async file operations where beneficial
- Type hints for all methods
- Organized by functionality
"""

from pathlib import Path
import asyncio
import time
import logging
from typing import Optional, Dict, List
from telegram.error import TelegramError

logger = logging.getLogger('mark4_bot')


class FileService:
    """
    Service for handling all file operations.

    Organized into categories:
    - Directory management
    - Filename generation and validation
    - Telegram downloads (photos, documents)
    - File operations (delete, cleanup)
    - Storage statistics
    """

    def __init__(self, uploads_dir: Path, retrieve_dir: Path, allowed_formats: set):
        """
        Initialize file service.

        Args:
            uploads_dir: Directory for user uploads
            retrieve_dir: Directory for ComfyUI processed files
            allowed_formats: Set of allowed image extensions (without dots)
        """
        self.uploads_dir = Path(uploads_dir)
        self.retrieve_dir = Path(retrieve_dir)
        self.allowed_formats = allowed_formats

        self._ensure_directories()
        logger.info(
            f"Initialized FileService: "
            f"uploads={self.uploads_dir}, retrieve={self.retrieve_dir}"
        )

    # Directory Management

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.retrieve_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(
            f"Ensured directories exist: "
            f"uploads={self.uploads_dir}, retrieve={self.retrieve_dir}"
        )

    # Filename Operations

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
        is_valid = ext in self.allowed_formats
        logger.debug(f"File {filename} format valid: {is_valid}")
        return is_valid

    def get_output_path(self, original_filename: str, suffix: str = "_complete") -> str:
        """
        Generate output path for processed file.

        Args:
            original_filename: Original upload filename
            suffix: Suffix to add before extension (default: "_complete")

        Returns:
            Path to save processed output
        """
        base_name = Path(original_filename).stem
        extension = Path(original_filename).suffix
        output_filename = f"{base_name}{suffix}{extension}"
        output_path = self.retrieve_dir / output_filename
        return str(output_path)

    # Telegram Download Operations

    async def download_telegram_photo(
        self,
        photo,
        user_id: int,
        bot,
        max_retries: int = 3
    ) -> str:
        """
        Download photo from Telegram servers with retry logic.

        Args:
            photo: Telegram PhotoSize object
            user_id: Telegram user ID
            bot: Telegram Bot instance
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Local file path where photo was saved

        Raises:
            TelegramError: If download fails after all retries
        """
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Getting file info for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                file = await bot.get_file(photo.file_id)

                logger.info(
                    f"File ID: {photo.file_id}, "
                    f"Size: {photo.file_size}, "
                    f"Path: {file.file_path}"
                )

                filename = self.generate_filename(user_id, 'jpg')
                local_path = self.uploads_dir / filename

                logger.info(f"Downloading to: {local_path}")
                await file.download_to_drive(str(local_path))

                logger.info(
                    f"Successfully downloaded photo for user {user_id} to {local_path}"
                )
                return str(local_path)

            except TelegramError as e:
                logger.error(
                    f"Telegram error downloading photo for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to download photo after {max_retries} attempts"
                    )
                    raise

            except Exception as e:
                logger.error(
                    f"Unexpected error downloading photo for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}",
                    exc_info=True
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def download_telegram_document(
        self,
        document,
        user_id: int,
        bot,
        max_retries: int = 3
    ) -> str:
        """
        Download document from Telegram servers with retry logic.

        Args:
            document: Telegram Document object
            user_id: Telegram user ID
            bot: Telegram Bot instance
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Local file path where document was saved

        Raises:
            ValueError: If document format is invalid
            TelegramError: If download fails after all retries
        """
        # Validate format first
        if not self.is_valid_image_format(document.file_name):
            raise ValueError(f"Invalid image format: {document.file_name}")

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Getting document info for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                file = await bot.get_file(document.file_id)

                logger.info(
                    f"File ID: {document.file_id}, "
                    f"Name: {document.file_name}, "
                    f"Size: {document.file_size}"
                )

                ext = Path(document.file_name).suffix.lstrip('.')
                filename = self.generate_filename(user_id, ext)
                local_path = self.uploads_dir / filename

                logger.info(f"Downloading to: {local_path}")
                await file.download_to_drive(str(local_path))

                logger.info(
                    f"Successfully downloaded document for user {user_id} to {local_path}"
                )
                return str(local_path)

            except TelegramError as e:
                logger.error(
                    f"Telegram error downloading document for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}"
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to download document after {max_retries} attempts"
                    )
                    raise

            except ValueError:
                raise  # Re-raise validation errors immediately
            except Exception as e:
                logger.error(
                    f"Unexpected error downloading document for user {user_id} "
                    f"(attempt {attempt + 1}/{max_retries}): {e}",
                    exc_info=True
                )

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise

    # File Operations

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

        except PermissionError as e:
            logger.error(f"Permission denied deleting file {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filepath}: {e}")
            return False

    def delete_user_upload(self, filename: str) -> bool:
        """
        Delete file from user uploads directory.

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted successfully
        """
        filepath = self.uploads_dir / filename
        return self.delete_file(str(filepath))

    def delete_processed_output(self, filename: str) -> bool:
        """
        Delete file from ComfyUI retrieve directory.

        Args:
            filename: Name of file to delete

        Returns:
            True if deleted successfully
        """
        filepath = self.retrieve_dir / filename
        return self.delete_file(str(filepath))

    def cleanup_user_files(self, user_id: int) -> int:
        """
        Delete all files associated with a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Number of files deleted
        """
        pattern = f"{user_id}_*"
        deleted_count = 0

        # Clean uploads directory
        try:
            for file in self.uploads_dir.glob(pattern):
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        except Exception as e:
            logger.error(f"Error cleaning uploads for user {user_id}: {e}")

        # Clean retrieve directory
        try:
            for file in self.retrieve_dir.glob(pattern):
                if file.is_file():
                    file.unlink()
                    deleted_count += 1
        except Exception as e:
            logger.error(f"Error cleaning retrieve for user {user_id}: {e}")

        logger.info(f"Cleaned up {deleted_count} files for user {user_id}")
        return deleted_count

    # File Information

    def file_exists(self, filepath: str) -> bool:
        """
        Check if file exists.

        Args:
            filepath: Path to file

        Returns:
            True if file exists
        """
        return Path(filepath).exists()

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
            logger.error(f"Error getting file size for {filepath}: {e}")
            return None

    def list_user_files(self, user_id: int) -> Dict[str, List[str]]:
        """
        List all files for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with 'uploads' and 'processed' lists of filenames
        """
        pattern = f"{user_id}_*"

        try:
            uploads = [
                f.name for f in self.uploads_dir.glob(pattern)
                if f.is_file()
            ]
        except Exception as e:
            logger.error(f"Error listing uploads for user {user_id}: {e}")
            uploads = []

        try:
            processed = [
                f.name for f in self.retrieve_dir.glob(pattern)
                if f.is_file()
            ]
        except Exception as e:
            logger.error(f"Error listing processed files for user {user_id}: {e}")
            processed = []

        return {
            'uploads': uploads,
            'processed': processed
        }

    # Storage Statistics

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
            logger.error(f"Error calculating directory size for {directory}: {e}")
            return 0

    def get_storage_stats(self) -> Dict[str, int]:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics:
                - uploads_dir_size: Total size of uploads directory (bytes)
                - retrieve_dir_size: Total size of retrieve directory (bytes)
                - uploads_count: Number of files in uploads directory
                - retrieve_count: Number of files in retrieve directory
        """
        try:
            uploads_count = len(list(self.uploads_dir.glob('*')))
        except Exception as e:
            logger.error(f"Error counting uploads: {e}")
            uploads_count = 0

        try:
            retrieve_count = len(list(self.retrieve_dir.glob('*')))
        except Exception as e:
            logger.error(f"Error counting retrieve files: {e}")
            retrieve_count = 0

        return {
            'uploads_dir_size': self.get_directory_size(self.uploads_dir),
            'retrieve_dir_size': self.get_directory_size(self.retrieve_dir),
            'uploads_count': uploads_count,
            'retrieve_count': retrieve_count
        }

    # Utility Methods

    def cleanup_old_files(self, max_age_seconds: int) -> int:
        """
        Delete files older than specified age.

        Args:
            max_age_seconds: Maximum age of files to keep

        Returns:
            Number of files deleted
        """
        import time

        current_time = time.time()
        deleted_count = 0

        # Clean uploads directory
        try:
            for file in self.uploads_dir.glob('*'):
                if file.is_file():
                    file_age = current_time - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file.name} (age: {file_age}s)")
        except Exception as e:
            logger.error(f"Error cleaning old uploads: {e}")

        # Clean retrieve directory
        try:
            for file in self.retrieve_dir.glob('*'):
                if file.is_file():
                    file_age = current_time - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file.name} (age: {file_age}s)")
        except Exception as e:
            logger.error(f"Error cleaning old retrieve files: {e}")

        logger.info(f"Cleaned up {deleted_count} old files (max_age={max_age_seconds}s)")
        return deleted_count
