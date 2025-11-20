"""User state management for the Telegram bot."""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger('mark4_bot')


class StateManager:
    """
    Manages user states, queue messages, and cleanup tasks.

    In production, this should be backed by a database like Redis or PostgreSQL
    for persistence across bot restarts.
    """

    def __init__(self):
        """Initialize state storage."""
        self._user_states: Dict[int, Dict[str, Any]] = {}
        self._user_queue_messages: Dict[int, Any] = {}
        self._cleanup_tasks: Dict[int, Any] = {}

    # User State Management

    def get_state(self, user_id: int) -> Dict[str, Any]:
        """
        Get user state dictionary.

        Args:
            user_id: Telegram user ID

        Returns:
            User state dictionary (empty dict if user not found)
        """
        return self._user_states.get(user_id, {})

    def set_state(self, user_id: int, state: Dict[str, Any]):
        """
        Set complete user state.

        Args:
            user_id: Telegram user ID
            state: Complete state dictionary
        """
        self._user_states[user_id] = state
        logger.debug(f"Set state for user {user_id}: {state}")

    def update_state(self, user_id: int, **kwargs):
        """
        Update user state with new key-value pairs.

        Args:
            user_id: Telegram user ID
            **kwargs: Key-value pairs to update in state
        """
        if user_id not in self._user_states:
            self._user_states[user_id] = {}
        self._user_states[user_id].update(kwargs)
        logger.debug(f"Updated state for user {user_id}: {kwargs}")

    def reset_state(self, user_id: int):
        """
        Reset user state to empty.

        Args:
            user_id: Telegram user ID
        """
        self._user_states[user_id] = {}
        logger.debug(f"Reset state for user {user_id}")

    def is_state(self, user_id: int, state_value: str) -> bool:
        """
        Check if user is in a specific state.

        Args:
            user_id: Telegram user ID
            state_value: State value to check (e.g., 'processing')

        Returns:
            True if user is in specified state
        """
        return self._user_states.get(user_id, {}).get('state') == state_value

    def get_state_value(self, user_id: int, key: str, default: Any = None) -> Any:
        """
        Get a specific value from user state.

        Args:
            user_id: Telegram user ID
            key: State key to retrieve
            default: Default value if key not found

        Returns:
            Value associated with key, or default
        """
        return self._user_states.get(user_id, {}).get(key, default)

    def has_state(self, user_id: int) -> bool:
        """
        Check if user has any state stored.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user has state
        """
        return user_id in self._user_states and bool(self._user_states[user_id])

    # Queue Message Management

    def set_queue_message(self, user_id: int, message: Any):
        """
        Store queue status message for later updates/deletion.

        Args:
            user_id: Telegram user ID
            message: Telegram Message object
        """
        self._user_queue_messages[user_id] = message
        logger.debug(f"Set queue message for user {user_id}")

    def get_queue_message(self, user_id: int) -> Optional[Any]:
        """
        Get stored queue message.

        Args:
            user_id: Telegram user ID

        Returns:
            Message object or None
        """
        return self._user_queue_messages.get(user_id)

    def remove_queue_message(self, user_id: int):
        """
        Remove queue message from storage.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self._user_queue_messages:
            del self._user_queue_messages[user_id]
            logger.debug(f"Removed queue message for user {user_id}")

    def has_queue_message(self, user_id: int) -> bool:
        """
        Check if user has a queue message stored.

        Args:
            user_id: Telegram user ID

        Returns:
            True if queue message exists
        """
        return user_id in self._user_queue_messages

    # Cleanup Task Management

    def set_cleanup_task(self, user_id: int, task: Any):
        """
        Store cleanup task for cancellation if needed.

        Args:
            user_id: Telegram user ID
            task: asyncio Task object
        """
        # Cancel existing task if present
        if user_id in self._cleanup_tasks:
            self._cleanup_tasks[user_id].cancel()

        self._cleanup_tasks[user_id] = task
        logger.debug(f"Set cleanup task for user {user_id}")

    def get_cleanup_task(self, user_id: int) -> Optional[Any]:
        """
        Get stored cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            Task object or None
        """
        return self._cleanup_tasks.get(user_id)

    def cancel_cleanup_task(self, user_id: int) -> bool:
        """
        Cancel and remove cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            True if task was cancelled, False if no task exists
        """
        if user_id in self._cleanup_tasks:
            self._cleanup_tasks[user_id].cancel()
            del self._cleanup_tasks[user_id]
            logger.debug(f"Cancelled cleanup task for user {user_id}")
            return True
        return False

    def has_cleanup_task(self, user_id: int) -> bool:
        """
        Check if user has a cleanup task.

        Args:
            user_id: Telegram user ID

        Returns:
            True if cleanup task exists
        """
        return user_id in self._cleanup_tasks

    # Utility Methods

    def clear_all_user_data(self, user_id: int):
        """
        Clear all data associated with a user.

        Args:
            user_id: Telegram user ID
        """
        self.reset_state(user_id)
        self.remove_queue_message(user_id)
        self.cancel_cleanup_task(user_id)
        logger.info(f"Cleared all data for user {user_id}")

    def get_all_processing_users(self) -> list:
        """
        Get list of all users currently in processing state.

        Returns:
            List of user IDs
        """
        return [
            user_id for user_id, state in self._user_states.items()
            if state.get('state') == 'processing'
        ]

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about current state.

        Returns:
            Dictionary with stats (total_users, processing, queue_messages, cleanup_tasks)
        """
        return {
            'total_users': len(self._user_states),
            'processing': len(self.get_all_processing_users()),
            'queue_messages': len(self._user_queue_messages),
            'cleanup_tasks': len(self._cleanup_tasks)
        }
