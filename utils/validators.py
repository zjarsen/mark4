"""Input validation utilities."""

from pathlib import Path
import logging

logger = logging.getLogger('mark4_bot')


def validate_image_format(filename: str, allowed_formats: list) -> bool:
    """
    Validate if file has allowed image extension.

    Args:
        filename: Filename to check
        allowed_formats: List of allowed extensions (without dot)

    Returns:
        True if valid format
    """
    ext = Path(filename).suffix.lower().lstrip('.')
    return ext in allowed_formats


def validate_file_size(file_size: int, max_size_mb: int = 20) -> bool:
    """
    Validate file size.

    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB

    Returns:
        True if size is acceptable
    """
    max_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_bytes


def validate_user_id(user_id: any) -> bool:
    """
    Validate user ID.

    Args:
        user_id: User ID to validate

    Returns:
        True if valid
    """
    if user_id is None:
        return False

    if isinstance(user_id, int):
        return user_id > 0

    if isinstance(user_id, str):
        try:
            return int(user_id) > 0
        except ValueError:
            return False

    return False


def validate_prompt_id(prompt_id: str) -> bool:
    """
    Validate prompt ID format.

    Args:
        prompt_id: Prompt ID to validate

    Returns:
        True if valid
    """
    if not prompt_id or not isinstance(prompt_id, str):
        return False

    # Basic validation - not empty and reasonable length
    return 0 < len(prompt_id) < 200


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']

    sanitized = filename
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '_')

    # Limit length
    if len(sanitized) > 200:
        ext = Path(sanitized).suffix
        name = Path(sanitized).stem[:190]
        sanitized = f"{name}{ext}"

    return sanitized
