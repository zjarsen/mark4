"""
Redis-based state manager implementation.

This provides persistent state storage using Redis, which:
- Survives bot restarts
- Supports multiple bot instances (horizontal scaling)
- Automatic cleanup via TTL
- Atomic operations

Requires: redis[asyncio] package
"""

import json
import logging
from typing import Dict, Any, Optional
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from .manager import StateManager

logger = logging.getLogger('mark4_bot')


class RedisStateManager(StateManager):
    """
    Persistent state management with Redis.

    Key features:
    - State survives bot restarts
    - Supports multiple bot instances
    - Automatic cleanup via TTL (1 hour default)
    - Thread-safe and async-safe
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 3600):
        """
        Initialize Redis state manager.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for state entries (default: 1 hour)

        Raises:
            ImportError: If redis package is not installed
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is required for RedisStateManager. "
                "Install with: pip install redis[asyncio]"
            )

        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self._client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = await redis.from_url(self.redis_url, decode_responses=True)
                    logger.info(f"Connected to Redis: {self.redis_url}")
        return self._client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    # User State Management

    async def get_state(self, user_id: int) -> Dict[str, Any]:
        """Get user state from Redis."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:state"
            data = await client.get(key)
            if data:
                return json.loads(data)
            return {}
        except Exception as e:
            logger.error(f"Error getting state for user {user_id}: {e}")
            return {}

    async def set_state(self, user_id: int, state: Dict[str, Any]):
        """Set user state in Redis with TTL."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:state"
            await client.setex(key, self.ttl, json.dumps(state))
            logger.debug(f"Set state for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting state for user {user_id}: {e}")

    async def update_state(self, user_id: int, **kwargs):
        """Update user state (read-modify-write)."""
        try:
            state = await self.get_state(user_id)
            state.update(kwargs)
            await self.set_state(user_id, state)
            logger.debug(f"Updated state for user {user_id}: {kwargs}")
        except Exception as e:
            logger.error(f"Error updating state for user {user_id}: {e}")

    async def reset_state(self, user_id: int):
        """Reset user state to empty."""
        await self.set_state(user_id, {})
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
        try:
            client = await self._get_client()
            key = f"user:{user_id}:queue_msg"
            # Store as JSON: {chat_id, message_id}
            value = json.dumps({
                'chat_id': message.chat_id,
                'message_id': message.message_id
            })
            await client.setex(key, self.ttl, value)
            logger.debug(f"Set queue message for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting queue message for user {user_id}: {e}")

    async def get_queue_message(self, user_id: int) -> Optional[Any]:
        """
        Get stored queue message.

        Note: Returns a dict with {chat_id, message_id}, not the actual Message object.
        The caller must reconstruct the message if needed.
        """
        try:
            client = await self._get_client()
            key = f"user:{user_id}:queue_msg"
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting queue message for user {user_id}: {e}")
            return None

    async def remove_queue_message(self, user_id: int):
        """Remove queue message from storage."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:queue_msg"
            await client.delete(key)
            logger.debug(f"Removed queue message for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing queue message for user {user_id}: {e}")

    async def has_queue_message(self, user_id: int) -> bool:
        """Check if user has a queue message stored."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:queue_msg"
            exists = await client.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Error checking queue message for user {user_id}: {e}")
            return False

    # Confirmation Message Management

    async def set_confirmation_message(self, user_id: int, message: Any):
        """Store confirmation message reference."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:confirm_msg"
            value = json.dumps({
                'chat_id': message.chat_id,
                'message_id': message.message_id
            })
            await client.setex(key, self.ttl, value)
            logger.debug(f"Set confirmation message for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting confirmation message for user {user_id}: {e}")

    async def get_confirmation_message(self, user_id: int) -> Optional[Any]:
        """Get stored confirmation message."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:confirm_msg"
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting confirmation message for user {user_id}: {e}")
            return None

    async def remove_confirmation_message(self, user_id: int):
        """Remove confirmation message from storage."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:confirm_msg"
            await client.delete(key)
            logger.debug(f"Removed confirmation message for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing confirmation message for user {user_id}: {e}")

    async def has_confirmation_message(self, user_id: int) -> bool:
        """Check if user has a confirmation message stored."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:confirm_msg"
            exists = await client.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Error checking confirmation message for user {user_id}: {e}")
            return False

    # Cleanup Task Management
    # Note: Tasks cannot be serialized to Redis, so we track task IDs only
    # Actual task management remains in-memory

    async def set_cleanup_task(self, user_id: int, task: Any):
        """
        Store cleanup task reference.

        Note: asyncio.Task cannot be serialized to Redis.
        We store a marker that a task exists, but the actual task
        object must be managed separately (in-memory).
        """
        try:
            client = await self._get_client()
            key = f"user:{user_id}:cleanup_task"
            await client.setex(key, self.ttl, "exists")
            logger.debug(f"Marked cleanup task for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting cleanup task for user {user_id}: {e}")

    async def get_cleanup_task(self, user_id: int) -> Optional[Any]:
        """Get cleanup task (returns marker, not actual task)."""
        # Tasks cannot be retrieved from Redis
        # This is a limitation of the Redis implementation
        return None

    async def cancel_cleanup_task(self, user_id: int) -> bool:
        """Remove cleanup task marker."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:cleanup_task"
            result = await client.delete(key)
            if result:
                logger.debug(f"Cancelled cleanup task marker for user {user_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Error cancelling cleanup task for user {user_id}: {e}")
            return False

    async def has_cleanup_task(self, user_id: int) -> bool:
        """Check if cleanup task marker exists."""
        try:
            client = await self._get_client()
            key = f"user:{user_id}:cleanup_task"
            exists = await client.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Error checking cleanup task for user {user_id}: {e}")
            return False

    # Utility Methods

    async def clear_all_user_data(self, user_id: int):
        """Clear all data for a user."""
        await self.reset_state(user_id)
        await self.remove_queue_message(user_id)
        await self.remove_confirmation_message(user_id)
        await self.cancel_cleanup_task(user_id)
        logger.info(f"Cleared all data for user {user_id}")

    async def get_all_processing_users(self) -> list:
        """
        Get list of all users currently in processing state.

        Note: This requires scanning all user state keys, which can be slow.
        """
        try:
            client = await self._get_client()
            processing_users = []

            # Scan for all user state keys
            async for key in client.scan_iter("user:*:state"):
                # Extract user_id from key (format: user:<user_id>:state)
                user_id = int(key.split(':')[1])
                if await self.is_state(user_id, 'processing'):
                    processing_users.append(user_id)

            return processing_users
        except Exception as e:
            logger.error(f"Error getting processing users: {e}")
            return []

    async def get_stats(self) -> Dict[str, int]:
        """Get statistics about current state."""
        try:
            client = await self._get_client()

            # Count keys by pattern
            state_keys = 0
            queue_keys = 0
            cleanup_keys = 0

            async for key in client.scan_iter("user:*:state"):
                state_keys += 1
            async for key in client.scan_iter("user:*:queue_msg"):
                queue_keys += 1
            async for key in client.scan_iter("user:*:cleanup_task"):
                cleanup_keys += 1

            processing = len(await self.get_all_processing_users())

            return {
                'total_users': state_keys,
                'processing': processing,
                'queue_messages': queue_keys,
                'cleanup_tasks': cleanup_keys
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_users': 0,
                'processing': 0,
                'queue_messages': 0,
                'cleanup_tasks': 0
            }
