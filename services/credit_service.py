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
        reference_id: str = None,
        feature_type: str = None
    ) -> Tuple[bool, float]:
        """
        Deduct credits for using a feature.

        Args:
            user_id: User ID
            feature_name: Feature name (e.g., 'image_processing', 'video_processing')
            reference_id: Optional reference (e.g., prompt_id)
            feature_type: Optional specific feature type (e.g., 'image_undress', 'video_style_a')

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
                        # Get current balance (unchanged for free usage)
                        balance = await self.get_balance(user_id)

                        # Create transaction record for free trial usage
                        self.db.create_transaction(
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
                    reference_id=reference_id,
                    feature_type=feature_type
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

    async def get_total_spent(self, user_id: int) -> float:
        """
        Get user's total spent credits.

        Args:
            user_id: User ID

        Returns:
            Total spent amount
        """
        try:
            user = self.db.get_user(user_id)
            return user['total_spent'] if user else 0.0

        except Exception as e:
            logger.error(f"Error getting total spent for user {user_id}: {str(e)}")
            return 0.0

    # VIP operations
    async def is_vip_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Check if user is VIP and return tier.

        Args:
            user_id: User ID

        Returns:
            Tuple of (is_vip, tier) where tier is 'none', 'vip', or 'black_gold'
        """
        try:
            tier = self.db.get_vip_tier(user_id)
            is_vip = tier in ['vip', 'black_gold']
            return is_vip, tier

        except Exception as e:
            logger.error(f"Error checking VIP status for user {user_id}: {str(e)}")
            return False, 'none'

    async def check_vip_daily_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Check if VIP user has reached their daily usage limit.

        Args:
            user_id: User ID

        Returns:
            Tuple of (limit_reached, current_usage, limit)
            - limit_reached: True if limit is reached
            - current_usage: Current daily usage count
            - limit: Daily limit (50 for VIP, 100 for Black Gold)
        """
        try:
            # Check if user is VIP
            is_vip, tier = await self.is_vip_user(user_id)

            # Non-VIP users have no daily limits
            if not is_vip:
                return False, 0, 0

            # Get daily limit based on tier
            if tier == 'vip':
                daily_limit = 50
            elif tier == 'black_gold':
                daily_limit = 100
            else:
                return False, 0, 0

            # Get current date in GMT+8
            from datetime import datetime, timezone, timedelta
            gmt8 = timezone(timedelta(hours=8))
            current_date = datetime.now(gmt8).strftime('%Y-%m-%d')

            # Get current usage count
            current_usage = self.db.get_daily_usage_count(user_id, current_date)

            # Check if limit is reached
            limit_reached = current_usage >= daily_limit

            logger.info(
                f"VIP daily limit check for user {user_id} (tier: {tier}): "
                f"{current_usage}/{daily_limit} (limit_reached: {limit_reached})"
            )

            return limit_reached, current_usage, daily_limit

        except Exception as e:
            logger.error(f"Error checking VIP daily limit for user {user_id}: {str(e)}")
            return False, 0, 0

    async def check_bra_daily_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Check if regular (non-VIP) user has reached their daily bra usage limit.

        Args:
            user_id: User ID

        Returns:
            Tuple of (limit_reached, current_usage, limit)
            - limit_reached: True if limit is reached
            - current_usage: Current daily bra usage count
            - limit: Daily limit (5 for regular users)
        """
        try:
            # Daily limit for regular users on bra feature
            daily_limit = 5

            # Get current date in GMT+8
            from datetime import datetime, timezone, timedelta
            gmt8 = timezone(timedelta(hours=8))
            current_date = datetime.now(gmt8).strftime('%Y-%m-%d')

            # Get current bra usage count from transactions table
            current_usage = self.db.get_bra_usage_count(user_id, current_date)

            # Check if limit is reached
            limit_reached = current_usage >= daily_limit

            logger.info(
                f"Bra daily limit check for user {user_id}: "
                f"{current_usage}/{daily_limit} (limit_reached: {limit_reached})"
            )

            return limit_reached, current_usage, daily_limit

        except Exception as e:
            logger.error(f"Error checking bra daily limit for user {user_id}: {str(e)}")
            return False, 0, 5

    async def increment_vip_daily_usage(self, user_id: int) -> bool:
        """
        Increment VIP user's daily usage count.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            # Get current date in GMT+8
            from datetime import datetime, timezone, timedelta
            gmt8 = timezone(timedelta(hours=8))
            current_date = datetime.now(gmt8).strftime('%Y-%m-%d')

            # Increment usage
            success = self.db.increment_daily_usage(user_id, current_date)

            if success:
                logger.info(f"Incremented daily usage for VIP user {user_id}")
            else:
                logger.error(f"Failed to increment daily usage for VIP user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error incrementing VIP daily usage for user {user_id}: {str(e)}")
            return False

    async def check_sufficient_credits_with_vip(
        self,
        user_id: int,
        feature_name: str
    ) -> Tuple[bool, bool, float, float]:
        """
        Check credits with VIP bypass.

        Args:
            user_id: User ID
            feature_name: Feature name (e.g., 'image_processing')

        Returns:
            Tuple of (is_vip, has_sufficient, balance, cost)
        """
        try:
            # Check VIP status first
            is_vip, tier = await self.is_vip_user(user_id)

            balance = await self.get_balance(user_id)
            cost = self.db.get_feature_cost(feature_name) or 0.0

            if is_vip:
                # VIP users always have sufficient credits (but still subject to daily limits)
                logger.info(f"VIP user {user_id} (tier: {tier}) - bypassing credit check")
                return True, True, balance, cost

            # Regular credit check for non-VIP (includes free trial logic)
            has_sufficient, balance, cost = await self.check_sufficient_credits(
                user_id, feature_name
            )
            return False, has_sufficient, balance, cost

        except Exception as e:
            logger.error(
                f"Error checking credits with VIP for user {user_id}: {str(e)}"
            )
            return False, False, 0.0, 0.0

    async def grant_vip_status(self, user_id: int, tier: str) -> Tuple[bool, str]:
        """
        Grant VIP status to user and add unlimited credits.

        Args:
            user_id: User ID
            tier: 'vip' or 'black_gold'

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate tier
            if tier not in ['vip', 'black_gold']:
                return False, "无效的VIP类型"

            # Check current tier
            current_tier = self.db.get_vip_tier(user_id)

            # Check if redundant purchase
            if current_tier == tier:
                tier_name = self._tier_display_name(tier)
                return False, f"您已经是{tier_name}了"

            # Check if downgrade (shouldn't happen, but validate)
            if current_tier == 'black_gold' and tier == 'vip':
                return False, "不能从黑金VIP降级到普通VIP"

            # Set VIP tier
            success = self.db.set_vip_tier(user_id, tier)

            if not success:
                return False, "设置VIP状态失败"

            # Add 99999999 credits
            credit_amount = 99999999
            tier_name = self._tier_display_name(tier)

            success, new_balance = await self.add_credits(
                user_id,
                credit_amount,
                description=f"{tier_name}购买",
                reference_id=f"vip_{tier}_{user_id}"
            )

            if not success:
                # Rollback VIP tier
                self.db.set_vip_tier(user_id, current_tier)
                return False, "添加积分失败"

            logger.info(
                f"Granted {tier} VIP to user {user_id}, "
                f"added {credit_amount} credits, new balance: {new_balance}"
            )

            return True, f"恭喜成为{tier_name}！"

        except Exception as e:
            logger.error(f"Error granting VIP to user {user_id}: {str(e)}")
            return False, "系统错误"

    def _tier_display_name(self, tier: str) -> str:
        """
        Get display name for tier.

        Args:
            tier: Tier code ('none', 'vip', 'black_gold')

        Returns:
            Display name in Chinese
        """
        names = {
            'vip': '永久VIP',
            'black_gold': '永久黑金VIP',
            'none': '普通用户'
        }
        return names.get(tier, tier)
