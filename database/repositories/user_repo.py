"""
User repository for database operations.

This replaces the user-related methods from the old database_service.py
with a cleaner, more maintainable implementation.
"""

import logging
from typing import Optional, List
from datetime import datetime

from .base import BaseRepository
from ..models import User, row_to_user
from ..exceptions import IntegrityError, NotFoundError

logger = logging.getLogger('mark4_bot')


class UserRepository(BaseRepository):
    """Repository for user-related database operations."""

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID (returns None if not found).

        Note: Unlike the old implementation, this does NOT create
        a user if not found. Use create() separately for that.

        Args:
            user_id: Telegram user ID

        Returns:
            User model or None if not found
        """
        query = "SELECT * FROM users WHERE user_id = ?"
        row = self._fetch_one(query, (user_id,))
        return row_to_user(row) if row else None

    def create(self, user_id: int, username: str = None) -> User:
        """
        Create new user with default values.

        Args:
            user_id: Telegram user ID
            username: Telegram username (optional)

        Returns:
            Newly created User model

        Raises:
            IntegrityError: If user already exists
        """
        query = """
            INSERT INTO users (
                user_id, telegram_username, credit_balance,
                free_image_processing_used, vip_tier
            )
            VALUES (?, ?, 0.0, 0, 'none')
        """
        try:
            self._execute(query, (user_id, username))
            logger.info(f"Created user: {user_id}")
            return self.get_by_id(user_id)
        except IntegrityError:
            # User already exists (race condition)
            logger.warning(f"User {user_id} already exists")
            return self.get_by_id(user_id)

    def get_or_create(self, user_id: int, username: str = None) -> User:
        """
        Get user by ID, create if doesn't exist.

        This replicates the old behavior of get_user() for compatibility.

        Args:
            user_id: Telegram user ID
            username: Telegram username (optional)

        Returns:
            User model
        """
        user = self.get_by_id(user_id)
        if not user:
            user = self.create(user_id, username)
        return user

    def update_balance(self, user_id: int, new_balance: float) -> bool:
        """
        Update user's credit balance.

        Args:
            user_id: User ID
            new_balance: New balance amount

        Returns:
            True if successful

        Raises:
            QueryError: On database error
        """
        query = """
            UPDATE users
            SET credit_balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (new_balance, user_id))
        logger.debug(f"Updated balance for user {user_id} to {new_balance}")
        return True

    def update_vip_tier(self, user_id: int, tier: str) -> bool:
        """
        Update user's VIP tier.

        Args:
            user_id: User ID
            tier: VIP tier ('none', 'vip', 'black_gold')

        Returns:
            True if successful

        Raises:
            ValueError: If tier is invalid
            QueryError: On database error
        """
        if tier not in ['none', 'vip', 'black_gold']:
            raise ValueError(f"Invalid VIP tier: {tier}")

        query = """
            UPDATE users
            SET vip_tier = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (tier, user_id))
        logger.info(f"Updated VIP tier for user {user_id} to {tier}")
        return True

    def mark_free_trial_used(self, user_id: int) -> bool:
        """
        Mark free trial as used with timestamp.

        Args:
            user_id: User ID

        Returns:
            True if successful

        Raises:
            QueryError: On database error
        """
        query = """
            UPDATE users
            SET free_image_processing_used = 1,
                last_free_trial_used_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (user_id,))
        logger.debug(f"Marked free trial used for user {user_id}")
        return True

    def get_vip_users(self) -> List[User]:
        """
        Get all VIP users (vip or black_gold tier).

        Returns:
            List of User models
        """
        query = """
            SELECT * FROM users
            WHERE vip_tier IN ('vip', 'black_gold')
            ORDER BY created_at DESC
        """
        rows = self._fetch_all(query)
        return [row_to_user(row) for row in rows]

    def get_users_with_balance_above(self, min_balance: float) -> List[User]:
        """
        Get users with balance above threshold.

        Args:
            min_balance: Minimum balance threshold

        Returns:
            List of User models
        """
        query = """
            SELECT * FROM users
            WHERE credit_balance >= ?
            ORDER BY credit_balance DESC
        """
        rows = self._fetch_all(query, (min_balance,))
        return [row_to_user(row) for row in rows]

    def update_username(self, user_id: int, username: str) -> bool:
        """
        Update user's Telegram username.

        Args:
            user_id: User ID
            username: New username

        Returns:
            True if successful
        """
        query = """
            UPDATE users
            SET telegram_username = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (username, user_id))
        return True

    def update_interaction(self, user_id: int, current_date: str) -> bool:
        """
        Update user interaction tracking for daily discount system.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format

        Returns:
            True if successful
        """
        query = """
            UPDATE users
            SET interaction_days = CASE
                    WHEN last_interaction_date = ? THEN interaction_days
                    ELSE interaction_days + 1
                END,
                last_interaction_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (current_date, current_date, user_id))
        return True

    def save_daily_discount(
        self,
        user_id: int,
        tier: str,
        rate: float,
        current_date: str
    ) -> bool:
        """
        Save user's daily discount.

        Args:
            user_id: User ID
            tier: Discount tier ('SSR', 'SR', 'R', 'C')
            rate: Discount rate (0.5-0.95)
            current_date: Current date in YYYY-MM-DD format

        Returns:
            True if successful
        """
        query = """
            UPDATE users
            SET daily_discount_tier = ?,
                daily_discount_rate = ?,
                daily_discount_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (tier, rate, current_date, user_id))
        return True

    def get_discount_info(self, user_id: int) -> Optional[dict]:
        """
        Get user's discount-related information.

        Args:
            user_id: User ID

        Returns:
            Dictionary with discount info or None
        """
        query = """
            SELECT interaction_days, last_interaction_date,
                   daily_discount_tier, daily_discount_rate, daily_discount_date
            FROM users
            WHERE user_id = ?
        """
        row = self._fetch_one(query, (user_id,))
        return dict(row) if row else None

    def increment_total_spent(self, user_id: int, amount: float) -> bool:
        """
        Increment user's total spent amount.

        Args:
            user_id: User ID
            amount: Amount to add to total_spent

        Returns:
            True if successful
        """
        query = """
            UPDATE users
            SET total_spent = total_spent + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (amount, user_id))
        return True

    def get_daily_usage_count(self, user_id: int, feature_type: str, current_date: str) -> int:
        """
        Get user's daily usage count for a specific feature.

        Args:
            user_id: User ID
            feature_type: Feature type (e.g., 'image_bra')
            current_date: Current date in YYYY-MM-DD format

        Returns:
            Usage count for today
        """
        query = """
            SELECT daily_usage_count
            FROM users
            WHERE user_id = ? AND daily_usage_date = ?
        """
        row = self._fetch_one(query, (user_id, current_date))
        return row['daily_usage_count'] if row else 0

    def increment_daily_usage(self, user_id: int, current_date: str) -> bool:
        """
        Increment user's daily usage count.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format

        Returns:
            True if successful
        """
        query = """
            UPDATE users
            SET daily_usage_count = CASE
                    WHEN daily_usage_date = ? THEN daily_usage_count + 1
                    ELSE 1
                END,
                daily_usage_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """
        self._execute(query, (current_date, current_date, user_id))
        return True

    def count_total_users(self) -> int:
        """
        Get total number of users.

        Returns:
            Total user count
        """
        return self._count("SELECT COUNT(*) FROM users")

    def count_vip_users(self) -> int:
        """
        Get total number of VIP users.

        Returns:
            VIP user count
        """
        return self._count(
            "SELECT COUNT(*) FROM users WHERE vip_tier IN ('vip', 'black_gold')"
        )
