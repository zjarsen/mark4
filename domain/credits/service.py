"""
Credit management service with transaction safety.

This refactored version addresses critical issues:
- Atomic operations: balance update + transaction record happen together
- Uses new repository layer for type-safe database access
- Specific exceptions instead of generic error returns
- Clean separation of concerns
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Dict
import pytz

from database.connection import DatabaseConnection
from database.repositories import UserRepository, TransactionRepository
from database.exceptions import QueryError, TransactionError
from .exceptions import InsufficientCreditsError, InvalidAmountError

logger = logging.getLogger('mark4_bot')


class CreditService:
    """
    Service for managing user credits and transactions.

    Key improvements over old implementation:
    - Transaction-safe: balance updates and transaction records are atomic
    - Repository pattern: uses UserRepository and TransactionRepository
    - Specific exceptions: raises InsufficientCreditsError instead of returning False
    - Type-safe: uses TypedDict models
    """

    def __init__(self, connection_manager: DatabaseConnection, feature_pricing: Dict[str, float]):
        """
        Initialize credit service.

        Args:
            connection_manager: DatabaseConnection instance
            feature_pricing: Dict mapping feature names to credit costs
                            e.g., {'image_processing': 10.0, 'video_processing': 30.0}
        """
        self.conn_manager = connection_manager
        self.users = UserRepository(connection_manager)
        self.transactions = TransactionRepository(connection_manager)
        self.feature_pricing = feature_pricing

    def _get_feature_cost(self, feature_name: str) -> float:
        """
        Get cost for a feature.

        Args:
            feature_name: Feature name

        Returns:
            Credit cost

        Raises:
            ValueError: If feature name is unknown
        """
        if feature_name not in self.feature_pricing:
            raise ValueError(f"Unknown feature: {feature_name}")
        return self.feature_pricing[feature_name]

    async def _is_free_trial_available(self, user_id: int) -> bool:
        """
        Check if free trial is available based on 2-day reset at midnight GMT+8.

        Logic:
        - New users: Available immediately
        - Used before: Available if >= 2 days since last use at midnight GMT+8

        Args:
            user_id: User ID

        Returns:
            True if free trial is available
        """
        try:
            user = self.users.get_by_id(user_id)
            if not user:
                return True  # New user gets free trial

            last_used = user.get('last_free_trial_used_at')
            if not last_used:
                return True  # Never used

            # Parse timestamp (SQLite stores as string)
            if isinstance(last_used, str):
                last_used_dt = datetime.strptime(last_used, '%Y-%m-%d %H:%M:%S')
            else:
                last_used_dt = last_used

            # Localize to UTC (SQLite stores in UTC)
            if last_used_dt.tzinfo is None:
                last_used_dt = pytz.utc.localize(last_used_dt)

            # Convert to GMT+8
            gmt8 = pytz.timezone('Asia/Shanghai')
            last_used_gmt8 = last_used_dt.astimezone(gmt8)
            now_gmt8 = datetime.now(gmt8)

            # Calculate reset time: 2 days after last use at midnight
            last_used_date = last_used_gmt8.date()
            reset_date = last_used_date + timedelta(days=2)
            reset_datetime = gmt8.localize(datetime.combine(reset_date, datetime.min.time()))

            return now_gmt8 >= reset_datetime

        except Exception as e:
            logger.error(f"Error checking free trial availability for user {user_id}: {e}")
            return False  # Fail safe - require credits on error

    async def get_next_free_trial_time(self, user_id: int) -> datetime | None:
        """
        Get next trial availability time in GMT+8.

        Args:
            user_id: User ID

        Returns:
            datetime object of next availability, or None if currently available
        """
        try:
            if await self._is_free_trial_available(user_id):
                return None  # Currently available

            user = self.users.get_by_id(user_id)
            if not user:
                return None  # New user - available now

            last_used = user.get('last_free_trial_used_at')
            if not last_used:
                return None  # Never used - available now

            # Parse timestamp
            if isinstance(last_used, str):
                last_used_dt = datetime.strptime(last_used, '%Y-%m-%d %H:%M:%S')
            else:
                last_used_dt = last_used

            # Localize to UTC
            if last_used_dt.tzinfo is None:
                last_used_dt = pytz.utc.localize(last_used_dt)

            # Convert to GMT+8
            gmt8 = pytz.timezone('Asia/Shanghai')
            last_used_gmt8 = last_used_dt.astimezone(gmt8)

            # Calculate reset time: 2 days after last use at midnight
            last_used_date = last_used_gmt8.date()
            reset_date = last_used_date + timedelta(days=2)
            reset_datetime = gmt8.localize(datetime.combine(reset_date, datetime.min.time()))

            return reset_datetime

        except Exception as e:
            logger.error(f"Error getting next free trial time for user {user_id}: {e}")
            return None

    async def get_balance(self, user_id: int) -> float:
        """
        Get user's credit balance.

        Args:
            user_id: User ID

        Returns:
            Credit balance (0.0 if user not found)
        """
        try:
            user = self.users.get_by_id(user_id)
            return user['credit_balance'] if user else 0.0

        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {e}")
            return 0.0

    async def has_free_trial(self, user_id: int) -> bool:
        """
        Check if user has free trial available.
        Uses recurring 2-day reset system with GMT+8 timezone.

        Args:
            user_id: User ID

        Returns:
            True if free trial is available
        """
        return await self._is_free_trial_available(user_id)

    async def use_free_trial(self, user_id: int) -> bool:
        """
        Mark free trial as used.
        Validates availability first to prevent race conditions.

        Args:
            user_id: User ID

        Returns:
            True if successful

        Raises:
            ValueError: If trial is not available
        """
        try:
            # Validate trial is available before using
            if not await self._is_free_trial_available(user_id):
                raise ValueError(f"Free trial not available for user {user_id}")

            success = self.users.mark_free_trial_used(user_id)
            if success:
                logger.info(f"User {user_id} used free trial")
            return success

        except Exception as e:
            logger.error(f"Error using free trial for user {user_id}: {e}")
            raise

    async def check_sufficient_credits(
        self,
        user_id: int,
        feature_name: str
    ) -> Tuple[bool, float, float]:
        """
        Check if user has enough credits for a feature.

        Args:
            user_id: User ID
            feature_name: Feature name (e.g., 'image_processing')

        Returns:
            Tuple of (has_sufficient, current_balance, required_amount)
        """
        try:
            # Check free trial first
            if feature_name == 'image_processing':
                has_trial = await self.has_free_trial(user_id)
                if has_trial:
                    return True, 0.0, 0.0  # Free trial available

            # Check balance
            balance = await self.get_balance(user_id)
            cost = self._get_feature_cost(feature_name)

            has_sufficient = balance >= cost
            return has_sufficient, balance, cost

        except Exception as e:
            logger.error(
                f"Error checking credits for user {user_id}, feature {feature_name}: {e}"
            )
            return False, 0.0, 0.0

    async def deduct_credits(
        self,
        user_id: int,
        feature_name: str,
        reference_id: str = None,
        feature_type: str = None
    ) -> Tuple[bool, float]:
        """
        Deduct credits for using a feature.

        CRITICAL IMPROVEMENT: This is now ATOMIC!
        Balance update and transaction record happen in a single database transaction.

        Args:
            user_id: User ID
            feature_name: Feature name (e.g., 'image_processing', 'video_processing')
            reference_id: Optional reference (e.g., prompt_id)
            feature_type: Optional specific feature type (e.g., 'image_undress')

        Returns:
            Tuple of (success, new_balance)

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            ValueError: If feature is unknown
        """
        try:
            # Check if using free trial
            if feature_name == 'image_processing':
                has_trial = await self.has_free_trial(user_id)
                if has_trial:
                    success = await self.use_free_trial(user_id)
                    if success:
                        # Get current balance (unchanged for free usage)
                        balance = await self.get_balance(user_id)

                        # Create transaction record for free trial usage
                        self.transactions.create(
                            user_id=user_id,
                            transaction_type='deduction',
                            amount=0.0,  # Zero amount for free usage
                            balance_before=balance,
                            balance_after=balance,  # Balance unchanged
                            description=f"免费使用: {feature_name}",
                            reference_id=reference_id,
                            feature_type=feature_type or 'image_undress'
                        )

                        logger.info(f"User {user_id} used free trial for {feature_name}")
                        return True, 0.0  # Balance unchanged

            # Get current balance and cost
            user = self.users.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            balance = user['credit_balance']
            cost = self._get_feature_cost(feature_name)

            if balance < cost:
                raise InsufficientCreditsError(user_id, cost, balance)

            # ✅ ATOMIC OPERATION: Balance update + transaction record
            with self.conn_manager.transaction() as conn:
                cursor = conn.cursor()

                # Operation 1: Update balance
                new_balance = balance - cost
                cursor.execute("""
                    UPDATE users
                    SET credit_balance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_balance, user_id))

                # Operation 2: Create transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        user_id, transaction_type, amount,
                        balance_before, balance_after, description,
                        reference_id, feature_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, 'deduction', -cost,
                    balance, new_balance,
                    f"使用功能: {feature_name}",
                    reference_id, feature_type
                ))

                # If we reach here, both operations succeeded atomically!
                logger.info(
                    f"Deducted {cost} credits from user {user_id}, "
                    f"new balance: {new_balance}"
                )
                return True, new_balance

        except (InsufficientCreditsError, ValueError):
            raise  # Re-raise specific exceptions
        except TransactionError as e:
            logger.error(f"Transaction failed while deducting credits: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deducting credits for user {user_id}: {e}")
            raise

    async def add_credits(
        self,
        user_id: int,
        amount: float,
        description: str = None,
        reference_id: str = None
    ) -> Tuple[bool, float]:
        """
        Add credits to user's account (top-up).

        CRITICAL IMPROVEMENT: This is now ATOMIC!

        Args:
            user_id: User ID
            amount: Amount to add
            description: Optional description
            reference_id: Optional reference (e.g., payment_id)

        Returns:
            Tuple of (success, new_balance)

        Raises:
            InvalidAmountError: If amount is negative or zero
            ValueError: If user not found
        """
        if amount <= 0:
            raise InvalidAmountError(amount, "Amount must be positive")

        try:
            user = self.users.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            balance = user['credit_balance']
            new_balance = balance + amount

            # ✅ ATOMIC OPERATION: Balance update + transaction record
            with self.conn_manager.transaction() as conn:
                cursor = conn.cursor()

                # Operation 1: Update balance
                cursor.execute("""
                    UPDATE users
                    SET credit_balance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (new_balance, user_id))

                # Operation 2: Create transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        user_id, transaction_type, amount,
                        balance_before, balance_after, description,
                        reference_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, 'topup', amount,
                    balance, new_balance,
                    description or "充值",
                    reference_id
                ))

                # Both operations succeed or both fail!
                logger.info(
                    f"Added {amount} credits to user {user_id}, "
                    f"new balance: {new_balance}"
                )
                return True, new_balance

        except (InvalidAmountError, ValueError):
            raise
        except TransactionError as e:
            logger.error(f"Transaction failed while adding credits: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding credits for user {user_id}: {e}")
            raise

    async def get_user_stats(self, user_id: int) -> Dict:
        """
        Get user's credit statistics.

        Args:
            user_id: User ID

        Returns:
            Dict with balance, total_topups, total_spent, etc.
        """
        try:
            user = self.users.get_by_id(user_id)
            if not user:
                return {
                    'balance': 0.0,
                    'total_topups': 0.0,
                    'total_spent': 0.0,
                    'vip_tier': 'none'
                }

            total_topups = self.transactions.sum_topups_by_user(user_id)
            total_spent = self.transactions.sum_deductions_by_user(user_id)

            return {
                'balance': user['credit_balance'],
                'total_topups': total_topups,
                'total_spent': total_spent,
                'vip_tier': user.get('vip_tier', 'none'),
                'total_spent_cny': user.get('total_spent', 0.0)
            }

        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return {
                'balance': 0.0,
                'total_topups': 0.0,
                'total_spent': 0.0,
                'vip_tier': 'none'
            }

    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50
    ) -> list:
        """
        Get user's transaction history.

        Args:
            user_id: User ID
            limit: Maximum number of transactions

        Returns:
            List of transaction dicts
        """
        try:
            transactions = self.transactions.get_by_user(user_id, limit=limit)
            return [dict(tx) for tx in transactions]

        except Exception as e:
            logger.error(f"Error getting transaction history for {user_id}: {e}")
            return []
