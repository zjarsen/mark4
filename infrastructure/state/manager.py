"""
Abstract state manager interface.

This defines the contract that all state manager implementations must follow,
allowing easy swapping between Redis (production) and in-memory (testing).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class StateManager(ABC):
    """
    Abstract state manager interface.

    Implementations:
    - RedisStateManager: Persistent state using Redis (production)
    - InMemoryStateManager: Volatile state using Python dict (testing)
    """

    # User State Management

    @abstractmethod
    async def get_state(self, user_id: int) -> Dict[str, Any]:
        """
        Get user state dictionary.

        Args:
            user_id: Telegram user ID

        Returns:
            User state dictionary (empty dict if not found)
        """
        pass

    @abstractmethod
    async def set_state(self, user_id: int, state: Dict[str, Any]):
        """
        Set complete user state.

        Args:
            user_id: Telegram user ID
            state: Complete state dictionary
        """
        pass

    @abstractmethod
    async def update_state(self, user_id: int, **kwargs):
        """
        Update user state with new key-value pairs.

        Args:
            user_id: Telegram user ID
            **kwargs: Key-value pairs to update in state
        """
        pass

    @abstractmethod
    async def reset_state(self, user_id: int):
        """
        Reset user state to empty.

        Args:
            user_id: Telegram user ID
        """
        pass

    @abstractmethod
    async def is_state(self, user_id: int, state_value: str) -> bool:
        """
        Check if user is in a specific state.

        Args:
            user_id: Telegram user ID
            state_value: State value to check (e.g., 'processing')

        Returns:
            True if user is in specified state
        """
        pass

    @abstractmethod
    async def get_state_value(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Get a specific value from user state.

        Args:
            user_id: Telegram user ID
            key: State key to retrieve
            default: Default value if key not found

        Returns:
            Value associated with key, or default
        """
        pass

    @abstractmethod
    async def has_state(self, user_id: int) -> bool:
        """
        Check if user has any state stored.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has state
        """
        pass

    # Queue Message Management

    @abstractmethod
    async def set_queue_message(self, user_id: int, message: Any):
        """
        Store queue status message for later updates/deletion.

        Args:
            user_id: Telegram user ID
            message: Telegram Message object
        """
        pass

    @abstractmethod
    async def get_queue_message(self, user_id: int) -> Optional[Any]:
        """
        Get stored queue message.

        Args:
            user_id: Telegram user ID

        Returns:
            Message object or None
        """
        pass

    @abstractmethod
    async def remove_queue_message(self, user_id: int):
        """
        Remove queue message from storage.

        Args:
            user_id: Telegram user ID
        """
        pass

    @abstractmethod
    async def has_queue_message(self, user_id: int) -> bool:
        """
        Check if user has a queue message stored.

        Args:
            user_id: Telegram user ID

        Returns:
            True if queue message exists
        """
        pass

    # Confirmation Message Management

    @abstractmethod
    async def set_confirmation_message(self, user_id: int, message: Any):
        """
        Store credit confirmation message for later deletion.

        Args:
            user_id: Telegram user ID
            message: Telegram Message object
        """
        pass

    @abstractmethod
    async def get_confirmation_message(self, user_id: int) -> Optional[Any]:
        """
        Get stored confirmation message.

        Args:
            user_id: Telegram user ID

        Returns:
            Message object or None
        """
        pass

    @abstractmethod
    async def remove_confirmation_message(self, user_id: int):
        """
        Remove confirmation message from storage.

        Args:
            user_id: Telegram user ID
        """
        pass

    @abstractmethod
    async def has_confirmation_message(self, user_id: int) -> bool:
        """
        Check if user has a confirmation message stored.

        Args:
            user_id: Telegram user ID

        Returns:
            True if confirmation message exists
        """
        pass

    # Cleanup Task Management

    @abstractmethod
    async def set_cleanup_task(self, user_id: int, task: Any):
        """
        Store cleanup task for cancellation if needed.

        Args:
            user_id: Telegram user ID
            task: asyncio Task object
        """
        pass

    @abstractmethod
    async def get_cleanup_task(self, user_id: int) -> Optional[Any]:
        """
        Get stored cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            Task object or None
        """
        pass

    @abstractmethod
    async def cancel_cleanup_task(self, user_id: int) -> bool:
        """
        Cancel and remove cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            True if task was cancelled, False if no task exists
        """
        pass

    @abstractmethod
    async def has_cleanup_task(self, user_id: int) -> bool:
        """
        Check if user has a cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            True if cleanup task exists
        """
        pass

    # Utility Methods

    @abstractmethod
    async def clear_all_user_data(self, user_id: int):
        """
        Clear all data associated with a user.

        Args:
            user_id: Telegram user ID
        """
        pass

    @abstractmethod
    async def get_all_processing_users(self) -> list:
        """
        Get list of all users currently in processing state.

        Returns:
            List of user IDs
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about current state.

        Returns:
            Dictionary with stats (total_users, processing, queue_messages, cleanup_tasks)
        """
        pass
