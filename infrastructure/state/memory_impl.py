"""
In-memory state manager implementation.

This provides transient state storage using Python dictionaries, which:
- Simple testing and development (no Redis required)
- Fast operations (no network overhead)
- State lost on bot restart (not persistent)
- Single bot instance only (no horizontal scaling)

Useful for: local development, unit tests, CI/CD pipelines
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

from .manager import StateManager

logger = logging.getLogger('mark4_bot')


class InMemoryStateManager(StateManager):
    """
    Transient state management with in-memory dictionaries.

    Key features:
    - No external dependencies (pure Python)
    - Fast operations (no I/O)
    - State lost on restart (not persistent)
    - Thread-safe with asyncio locks

    Use cases:
    - Local development without Redis
    - Unit tests
    - CI/CD pipelines
    """

    def __init__(self):
        """Initialize in-memory state manager."""
        # User states: {user_id: {state: 'processing', ...}}
        self._states: Dict[int, Dict[str, Any]] = {}

        # Queue messages: {user_id: message_data}
        self._queue_messages: Dict[int, Any] = {}

        # Confirmation messages: {user_id: message_data}
        self._confirmation_messages: Dict[int, Any] = {}

        # Cleanup tasks: {user_id: asyncio.Task}
        self._cleanup_tasks: Dict[int, asyncio.Task] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info("Initialized InMemoryStateManager")

    # User State Management

    async def get_state(self, user_id: int) -> Dict[str, Any]:
        """Get user state from memory."""
        async with self._lock:
            return self._states.get(user_id, {}).copy()

    async def set_state(self, user_id: int, state: Dict[str, Any]):
        """Set user state in memory."""
        async with self._lock:
            self._states[user_id] = state.copy()
            logger.debug(f"Set state for user {user_id}")

    async def update_state(self, user_id: int, **kwargs):
        """Update user state (read-modify-write)."""
        async with self._lock:
            if user_id not in self._states:
                self._states[user_id] = {}
            self._states[user_id].update(kwargs)
            logger.debug(f"Updated state for user {user_id}: {kwargs}")

    async def reset_state(self, user_id: int):
        """Reset user state to empty."""
        async with self._lock:
            self._states[user_id] = {}
            logger.debug(f"Reset state for user {user_id}")

    async def is_state(self, user_id: int, state_value: str) -> bool:
        """Check if user is in a specific state."""
        state = await self.get_state(user_id)
        return state.get('state') == state_value

    async def get_state_value(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get a specific value from user state."""
        state = await self.get_state(user_id)
        return state.get(key, default)

    async def has_state(self, user_id: int) -> bool:
        """Check if user has any state stored."""
        state = await self.get_state(user_id)
        return bool(state)

    # Queue Message Management

    async def set_queue_message(self, user_id: int, message: Any):
        """Store queue message reference."""
        async with self._lock:
            # Store as dict: {chat_id, message_id}
            self._queue_messages[user_id] = {
                'chat_id': message.chat_id,
                'message_id': message.message_id
            }
            logger.debug(f"Set queue message for user {user_id}")

    async def get_queue_message(self, user_id: int) -> Optional[Any]:
        """
        Get stored queue message.

        Note: Returns a dict with {chat_id, message_id}, not the actual Message object.
        The caller must reconstruct the message if needed.
        """
        async with self._lock:
            return self._queue_messages.get(user_id)

    async def remove_queue_message(self, user_id: int):
        """Remove queue message from storage."""
        async with self._lock:
            if user_id in self._queue_messages:
                del self._queue_messages[user_id]
                logger.debug(f"Removed queue message for user {user_id}")

    async def has_queue_message(self, user_id: int) -> bool:
        """Check if user has a queue message stored."""
        async with self._lock:
            return user_id in self._queue_messages

    # Confirmation Message Management

    async def set_confirmation_message(self, user_id: int, message: Any):
        """Store confirmation message reference."""
        async with self._lock:
            self._confirmation_messages[user_id] = {
                'chat_id': message.chat_id,
                'message_id': message.message_id
            }
            logger.debug(f"Set confirmation message for user {user_id}")

    async def get_confirmation_message(self, user_id: int) -> Optional[Any]:
        """Get stored confirmation message."""
        async with self._lock:
            return self._confirmation_messages.get(user_id)

    async def remove_confirmation_message(self, user_id: int):
        """Remove confirmation message from storage."""
        async with self._lock:
            if user_id in self._confirmation_messages:
                del self._confirmation_messages[user_id]
                logger.debug(f"Removed confirmation message for user {user_id}")

    async def has_confirmation_message(self, user_id: int) -> bool:
        """Check if user has a confirmation message stored."""
        async with self._lock:
            return user_id in self._confirmation_messages

    # Cleanup Task Management

    async def set_cleanup_task(self, user_id: int, task: asyncio.Task):
        """Store cleanup task reference."""
        async with self._lock:
            # Cancel existing task if any
            if user_id in self._cleanup_tasks:
                old_task = self._cleanup_tasks[user_id]
                if not old_task.done():
                    old_task.cancel()

            self._cleanup_tasks[user_id] = task
            logger.debug(f"Set cleanup task for user {user_id}")

    async def get_cleanup_task(self, user_id: int) -> Optional[asyncio.Task]:
        """Get cleanup task."""
        async with self._lock:
            return self._cleanup_tasks.get(user_id)

    async def cancel_cleanup_task(self, user_id: int) -> bool:
        """Cancel and remove cleanup task."""
        async with self._lock:
            if user_id in self._cleanup_tasks:
                task = self._cleanup_tasks[user_id]
                if not task.done():
                    task.cancel()
                del self._cleanup_tasks[user_id]
                logger.debug(f"Cancelled cleanup task for user {user_id}")
                return True
            return False

    async def has_cleanup_task(self, user_id: int) -> bool:
        """Check if cleanup task exists."""
        async with self._lock:
            return user_id in self._cleanup_tasks

    # Utility Methods

    async def clear_all_user_data(self, user_id: int):
        """Clear all data for a user."""
        await self.reset_state(user_id)
        await self.remove_queue_message(user_id)
        await self.remove_confirmation_message(user_id)
        await self.cancel_cleanup_task(user_id)
        logger.info(f"Cleared all data for user {user_id}")

    async def get_all_processing_users(self) -> list:
        """Get list of all users currently in processing state."""
        processing_users = []
        async with self._lock:
            for user_id, state in self._states.items():
                if state.get('state') == 'processing':
                    processing_users.append(user_id)
        return processing_users

    async def get_stats(self) -> Dict[str, int]:
        """Get statistics about current state."""
        async with self._lock:
            processing_count = sum(
                1 for state in self._states.values()
                if state.get('state') == 'processing'
            )

            return {
                'total_users': len(self._states),
                'processing': processing_count,
                'queue_messages': len(self._queue_messages),
                'cleanup_tasks': len(self._cleanup_tasks)
            }

    # Testing Helpers

    async def clear_all(self):
        """
        Clear all stored data.

        Useful for: test cleanup, resetting state between test runs
        """
        async with self._lock:
            # Cancel all cleanup tasks
            for task in self._cleanup_tasks.values():
                if not task.done():
                    task.cancel()

            # Clear all dictionaries
            self._states.clear()
            self._queue_messages.clear()
            self._confirmation_messages.clear()
            self._cleanup_tasks.clear()

            logger.info("Cleared all in-memory state")

    async def get_all_users(self) -> list[int]:
        """
        Get list of all user IDs with state.

        Useful for: testing, debugging
        """
        async with self._lock:
            return list(self._states.keys())
