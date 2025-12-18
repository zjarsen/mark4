"""
ComfyUI-specific exceptions.

This hierarchy replaces generic Exception raises in ComfyUI client,
providing specific error types for better error handling.
"""


class ComfyUIError(Exception):
    """Base exception for all ComfyUI-related errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize ComfyUI error.

        Args:
            message: Human-readable error message
            details: Optional dict with additional context (status code, response, etc.)
        """
        super().__init__(message)
        self.details = details or {}


class ConnectionError(ComfyUIError):
    """Failed to connect to ComfyUI server."""

    def __init__(self, server_url: str, reason: str):
        """
        Initialize connection error.

        Args:
            server_url: ComfyUI server URL that failed
            reason: Underlying reason (network error, SSL, etc.)
        """
        super().__init__(
            f"Failed to connect to ComfyUI server: {server_url}",
            {'server_url': server_url, 'reason': reason}
        )
        self.server_url = server_url
        self.reason = reason


class UploadError(ComfyUIError):
    """Failed to upload file to ComfyUI server."""

    def __init__(self, filename: str, status_code: int = None, response: str = None):
        """
        Initialize upload error.

        Args:
            filename: Filename that failed to upload
            status_code: HTTP status code (if available)
            response: Server response text (if available)
        """
        msg = f"Failed to upload file: {filename}"
        if status_code:
            msg += f" (status {status_code})"

        super().__init__(msg, {
            'filename': filename,
            'status_code': status_code,
            'response': response
        })
        self.filename = filename
        self.status_code = status_code
        self.response = response


class QueueError(ComfyUIError):
    """Failed to queue workflow or retrieve queue information."""

    def __init__(self, operation: str, reason: str, status_code: int = None):
        """
        Initialize queue error.

        Args:
            operation: Operation that failed ('queue', 'get_info', 'get_position')
            reason: Reason for failure
            status_code: HTTP status code (if available)
        """
        super().__init__(
            f"Queue operation '{operation}' failed: {reason}",
            {'operation': operation, 'reason': reason, 'status_code': status_code}
        )
        self.operation = operation
        self.reason = reason
        self.status_code = status_code


class ProcessingError(ComfyUIError):
    """Error during workflow processing on ComfyUI server."""

    def __init__(self, prompt_id: str, error_type: str, message: str):
        """
        Initialize processing error.

        Args:
            prompt_id: The prompt ID that failed
            error_type: Type of error ('execution_error', 'node_error', etc.)
            message: Error message from ComfyUI
        """
        super().__init__(
            f"Processing failed for prompt {prompt_id}: {message}",
            {'prompt_id': prompt_id, 'error_type': error_type}
        )
        self.prompt_id = prompt_id
        self.error_type = error_type


class DownloadError(ComfyUIError):
    """Failed to download processed file from ComfyUI server."""

    def __init__(self, filename: str, status_code: int = None, subfolder: str = ""):
        """
        Initialize download error.

        Args:
            filename: Filename that failed to download
            status_code: HTTP status code (if available)
            subfolder: Subfolder location
        """
        msg = f"Failed to download file: {filename}"
        if subfolder:
            msg += f" (subfolder: {subfolder})"
        if status_code:
            msg += f" (status {status_code})"

        super().__init__(msg, {
            'filename': filename,
            'status_code': status_code,
            'subfolder': subfolder
        })
        self.filename = filename
        self.status_code = status_code
        self.subfolder = subfolder


class TimeoutError(ComfyUIError):
    """Operation timed out waiting for ComfyUI."""

    def __init__(self, operation: str, timeout_seconds: int, prompt_id: str = None):
        """
        Initialize timeout error.

        Args:
            operation: Operation that timed out ('processing', 'upload', 'download')
            timeout_seconds: Timeout duration in seconds
            prompt_id: Optional prompt ID (for processing timeouts)
        """
        msg = f"Operation '{operation}' timed out after {timeout_seconds}s"
        if prompt_id:
            msg += f" (prompt_id: {prompt_id})"

        super().__init__(msg, {
            'operation': operation,
            'timeout_seconds': timeout_seconds,
            'prompt_id': prompt_id
        })
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.prompt_id = prompt_id


class InvalidResponseError(ComfyUIError):
    """ComfyUI server returned invalid/unexpected response format."""

    def __init__(self, endpoint: str, expected: str, received: str):
        """
        Initialize invalid response error.

        Args:
            endpoint: API endpoint that returned invalid response
            expected: What was expected
            received: What was actually received
        """
        super().__init__(
            f"Invalid response from {endpoint}: expected {expected}, got {received}",
            {'endpoint': endpoint, 'expected': expected, 'received': received}
        )
        self.endpoint = endpoint
        self.expected = expected
        self.received = received
