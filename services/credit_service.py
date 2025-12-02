"""Credit management service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

logger = logging.getLogger('mark4_bot')


class CreditService:
    """Service for managing user credits and transactions."""

    def __init__(self, config, database_service):
        """
        Initialize credit service.

        Args:
            config: Configuration object
            database_service: DatabaseService instance
        """
        self.config = config
        self.db = database_service

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
            user = self.db.get_user(user_id)
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
            logger.error(f"Error checking free trial availability for user {user_id}: {str(e)}")
            return False  # Fail safe - require credits on error

    async def get_next_free_trial_time(self, user_id: int) -> Optional[datetime]:
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

            user = self.db.get_user(user_id)
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
            logger.error(f"Error getting next free trial time for user {user_id}: {str(e)}")
            return None

    async def get_balance(self, user_id: int) -> float:
        """
        Get user's credit balance.

        Args:
            user_id: User ID

        Returns:
            Credit balance
        """
        try:
            user = self.db.get_user(user_id)
            return user['credit_balance'] if user else 0.0

        except Exception as e:
            logger.error(f"Error getting balance for user {user_id}: {str(e)}")
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
        """
        try:
            # Validate trial is available before using
            if not await self._is_free_trial_available(user_id):
                logger.warning(f"Attempted to use unavailable trial for user {user_id}")
                return False

            success = self.db.mark_free_trial_used(user_id)
            if success:
                logger.info(f"User {user_id} used free trial")
            return success

        except Exception as e:
            logger.error(f"Error using free trial for user {user_id}: {str(e)}")
            return False

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
            cost = self.db.get_feature_cost(feature_name)

            if cost is None:
                logger.error(f"Unknown feature: {feature_name}")
                return False, balance, 0.0

            has_sufficient = balance >= cost
            return has_sufficient, balance, cost

        except Exception as e:
            logger.error(
                f"Error checking credits for user {user_id}, feature {feature_name}: {str(e)}"
            )
            return False, 0.0, 0.0

    async def deduct_credits(
        self,
        user_id: int,
        feature_name: str,
        reference_id: str = None
    ) -> Tuple[bool, float]:
        """
        Deduct credits for using a feature.

        Args:
            user_id: User ID
            feature_name: Feature name
            reference_id: Optional reference (e.g., prompt_id)

        Returns:
            Tuple of (success, new_balance)
        """
        try:
            # Check if using free trial
            if feature_name == 'image_processing':
                has_trial = await self.has_free_trial(user_id)
                if has_trial:
                    success = await self.use_free_trial(user_id)
                    if success:
                        logger.info(f"User {user_id} used free trial for {feature_name}")
                        return True, 0.0  # Balance unchanged
                    else:
                        logger.error(f"Failed to mark free trial used for user {user_id}")
                        return False, 0.0

            # Get current balance and cost
            balance = await self.get_balance(user_id)
            cost = self.db.get_feature_cost(feature_name)

            if cost is None:
                logger.error(f"Unknown feature: {feature_name}")
                return False, balance

            if balance < cost:
                logger.warning(
                    f"Insufficient credits for user {user_id}: "
                    f"balance={balance}, required={cost}"
                )
                return False, balance

            # Deduct credits
            new_balance = balance - cost
            success = self.db.update_user_balance(user_id, new_balance)

            if success:
                # Record transaction
                self.db.create_transaction(
                    user_id=user_id,
                    transaction_type='deduction',
                    amount=-cost,
                    balance_before=balance,
                    balance_after=new_balance,
                    description=f"使用功能: {feature_name}",
                    reference_id=reference_id
                )
                logger.info(
                    f"Deducted {cost} credits from user {user_id}, "
                    f"new balance: {new_balance}"
                )
                return True, new_balance
            else:
                logger.error(f"Failed to update balance for user {user_id}")
                return False, balance

        except Exception as e:
            logger.error(f"Error deducting credits for user {user_id}: {str(e)}")
            return False, 0.0

    async def add_credits(
        self,
        user_id: int,
        amount: float,
        description: str = None,
        reference_id: str = None
    ) -> Tuple[bool, float]:
        """
        Add credits to user's account (top-up).

        Args:
            user_id: User ID
            amount: Amount to add
            description: Optional description
            reference_id: Optional reference (e.g., payment_id)

        Returns:
            Tuple of (success, new_balance)
        """
        try:
            balance = await self.get_balance(user_id)
            new_balance = balance + amount

            success = self.db.update_user_balance(user_id, new_balance)

            if success:
                # Record transaction
                self.db.create_transaction(
                    user_id=user_id,
                    transaction_type='topup',
                    amount=amount,
                    balance_before=balance,
                    balance_after=new_balance,
                    description=description or "充值",
                    reference_id=reference_id
                )
                logger.info(
                    f"Added {amount} credits to user {user_id}, "
                    f"new balance: {new_balance}"
                )
                return True, new_balance
            else:
                logger.error(f"Failed to add credits for user {user_id}")
                return False, balance

        except Exception as e:
            logger.error(f"Error adding credits for user {user_id}: {str(e)}")
            return False, 0.0

    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get user's transaction history.

        Args:
            user_id: User ID
            limit: Number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        try:
            transactions = self.db.get_user_transactions(user_id, limit)
            return transactions

        except Exception as e:
            logger.error(f"Error getting transaction history for user {user_id}: {str(e)}")
            return []

    async def get_user_stats(self, user_id: int) -> Dict:
        """
        Get user's credit statistics.

        Args:
            user_id: User ID

        Returns:
            Dictionary with balance, total_spent, has_free_trial
        """
        try:
            user = self.db.get_user(user_id)
            if not user:
                return {
                    'balance': 0.0,
                    'total_spent': 0.0,
                    'has_free_trial': True
                }

            return {
                'balance': user['credit_balance'],
                'total_spent': user['total_spent'],
                'has_free_trial': not user['free_image_processing_used']
            }

        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {str(e)}")
            return {
                'balance': 0.0,
                'total_spent': 0.0,
                'has_free_trial': False
            }

    async def refund_credits(
        self,
        user_id: int,
        amount: float,
        description: str = None,
        reference_id: str = None
    ) -> Tuple[bool, float]:
        """
        Refund credits to user (e.g., failed processing).

        Args:
            user_id: User ID
            amount: Amount to refund
            description: Optional description
            reference_id: Optional reference (e.g., prompt_id)

        Returns:
            Tuple of (success, new_balance)
        """
        try:
            balance = await self.get_balance(user_id)
            new_balance = balance + amount

            success = self.db.update_user_balance(user_id, new_balance)

            if success:
                # Record transaction
                self.db.create_transaction(
                    user_id=user_id,
                    transaction_type='refund',
                    amount=amount,
                    balance_before=balance,
                    balance_after=new_balance,
                    description=description or "退款",
                    reference_id=reference_id
                )
                logger.info(
                    f"Refunded {amount} credits to user {user_id}, "
                    f"new balance: {new_balance}"
                )
                return True, new_balance
            else:
                logger.error(f"Failed to refund credits for user {user_id}")
                return False, balance

        except Exception as e:
            logger.error(f"Error refunding credits for user {user_id}: {str(e)}")
            return False, 0.0
