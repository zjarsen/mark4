"""Discount service for daily lucky discount system."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from core.constants import DISCOUNT_TIERS

logger = logging.getLogger('mark4_bot')


class DiscountService:
    """Service for managing daily lucky discounts."""

    def __init__(self, database_service):
        """
        Initialize discount service.

        Args:
            database_service: DatabaseService instance
        """
        self.db = database_service

    @staticmethod
    def get_current_date_gmt8() -> str:
        """
        Get current date in GMT+8 timezone.

        Returns:
            Date string in YYYY-MM-DD format
        """
        gmt8 = timezone(timedelta(hours=8))
        now = datetime.now(gmt8)
        return now.strftime('%Y-%m-%d')

    def calculate_discount_tier(self, interaction_days: int) -> Tuple[str, float]:
        """
        Calculate discount tier based on interaction days.

        Rules:
        - Day 1: Always SR (30% off) - first day bonus
        - Every 5th day (6, 11, 16...): SSR (50% off)
        - Every 3rd day (4, 7, 10...): SR (30% off)
        - Every 2nd day (3, 5, 7...): R (15% off)
        - Other days: C (5% off)

        If multiple rules apply, choose heavier discount.

        Args:
            interaction_days: Number of days user has interacted (1-indexed)

        Returns:
            Tuple of (tier_name, discount_rate)
            discount_rate: multiplier for final price (0.5 = 50% off, pay 50%)
        """
        # First day always gets SR
        if interaction_days == 1:
            return ('SR', 0.7)

        # Check each tier (order matters - heavier discount first)
        if interaction_days % 5 == 1:  # Every 5th day (day 6, 11, 16...)
            return ('SSR', 0.5)  # 50% off
        elif interaction_days % 3 == 1:  # Every 3rd day (day 4, 7, 10...)
            return ('SR', 0.7)  # 30% off (pay 70%)
        elif interaction_days % 2 == 1:  # Every 2nd day (day 3, 5, 7...)
            return ('R', 0.85)  # 15% off (pay 85%)
        else:
            return ('C', 0.95)  # 5% off (pay 95%)

    async def track_user_interaction(self, user_id: int):
        """
        Track user interaction and update interaction days.
        Should be called whenever user sends any message.

        Args:
            user_id: User ID
        """
        try:
            current_date = self.get_current_date_gmt8()
            self.db.update_user_interaction(user_id, current_date)
        except Exception as e:
            logger.error(f"Error tracking interaction for user {user_id}: {str(e)}")

    async def peek_discount_tier(self, user_id: int) -> Optional[str]:
        """
        Peek at what discount tier the user would get WITHOUT revealing it.
        Used to determine which message variant to show in top-up menu.

        Args:
            user_id: User ID

        Returns:
            Discount tier ('SSR', 'SR', 'R', 'C') or None if not available
        """
        try:
            discount_info = self.db.get_user_discount_info(user_id)

            if not discount_info:
                return None

            # If already revealed today, return the revealed tier
            current_date = self.get_current_date_gmt8()
            if discount_info['daily_discount_date'] == current_date:
                return discount_info['daily_discount_tier']

            # Otherwise, calculate what tier they would get (without revealing)
            interaction_days = discount_info['interaction_days'] or 1
            tier, _ = self.calculate_discount_tier(interaction_days)
            return tier

        except Exception as e:
            logger.error(f"Error peeking discount tier for user {user_id}: {str(e)}")
            return None

    async def get_or_reveal_daily_discount(self, user_id: int) -> Dict:
        """
        Get today's discount for user. If not revealed yet, calculate and save it.

        Args:
            user_id: User ID

        Returns:
            Dictionary with:
            - tier: Discount tier (SSR, SR, R, C)
            - rate: Discount rate (0.5, 0.7, 0.85, 0.95)
            - display: Display name (e.g., "SSR神级运气")
            - emoji: Emoji for tier
            - off: Discount percentage (e.g., "50%")
            - is_new: True if just revealed, False if already revealed today
        """
        try:
            current_date = self.get_current_date_gmt8()
            discount_info = self.db.get_user_discount_info(user_id)

            if not discount_info:
                logger.error(f"User {user_id} not found")
                return None

            # Check if discount already revealed today
            if discount_info['daily_discount_date'] == current_date:
                tier = discount_info['daily_discount_tier']
                rate = discount_info['daily_discount_rate']
                tier_info = DISCOUNT_TIERS[tier]
                return {
                    'tier': tier,
                    'rate': rate,
                    'emoji': tier_info['emoji'],
                    'off': tier_info['off'],
                    'is_new': False
                }

            # Calculate new discount for today
            interaction_days = discount_info['interaction_days'] or 1
            tier, rate = self.calculate_discount_tier(interaction_days)

            # Save discount
            self.db.save_daily_discount(user_id, tier, rate, current_date)

            tier_info = DISCOUNT_TIERS[tier]
            return {
                'tier': tier,
                'rate': rate,
                'emoji': tier_info['emoji'],
                'off': tier_info['off'],
                'is_new': True
            }

        except Exception as e:
            logger.error(f"Error getting daily discount for user {user_id}: {str(e)}")
            return None

    async def get_current_discount(self, user_id: int) -> Optional[Dict]:
        """
        Get user's current discount if revealed today.

        Args:
            user_id: User ID

        Returns:
            Dictionary with discount info or None if not revealed today
        """
        try:
            current_date = self.get_current_date_gmt8()
            discount_info = self.db.get_user_discount_info(user_id)

            if not discount_info:
                return None

            # Check if discount revealed today
            if discount_info['daily_discount_date'] == current_date:
                tier = discount_info['daily_discount_tier']
                rate = discount_info['daily_discount_rate']

                if tier and rate:
                    tier_info = DISCOUNT_TIERS[tier]
                    return {
                        'tier': tier,
                        'rate': rate,
                        'emoji': tier_info['emoji'],
                        'off': tier_info['off']
                    }

            return None

        except Exception as e:
            logger.error(f"Error getting current discount for user {user_id}: {str(e)}")
            return None

    def apply_discount_to_price(self, base_price: int, discount_rate: float) -> int:
        """
        Apply discount to base price.

        Args:
            base_price: Base price in CNY (before 8% transaction fee)
            discount_rate: Discount rate (0.5, 0.7, 0.85, 0.95)

        Returns:
            Discounted price with 8% transaction fee, rounded
        """
        # Apply discount first, then add 8% transaction fee
        discounted_price = base_price * discount_rate * 1.08
        return int(discounted_price)
