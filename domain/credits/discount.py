"""
Simplified discount service with random daily draw.

This replaces the overly complex day-based discount logic (interaction_days % 5 == 1)
with a simple random draw system that's easier to understand and maintain.

User decision: Option A - Random daily discount (simplified from complex day-based)
"""

import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from database.repositories import UserRepository
from core.constants import DISCOUNT_TIERS

logger = logging.getLogger('mark4_bot')


class DiscountService:
    """
    Service for managing daily lucky discounts.

    NEW DESIGN: Random daily draw instead of complex modulo logic
    - User clicks "幸运折扣" button
    - Random tier drawn from weighted pool
    - Simple, transparent, easy to explain
    """

    # Discount tier weights for random draw
    # SSR: 5% chance (best - 50% off)
    # SR: 15% chance (great - 30% off)
    # R: 30% chance (good - 15% off)
    # C: 50% chance (basic - 5% off)
    TIER_WEIGHTS = {
        'SSR': 5,
        'SR': 15,
        'R': 30,
        'C': 50
    }

    def __init__(self, user_repository: UserRepository):
        """
        Initialize discount service.

        Args:
            user_repository: UserRepository instance
        """
        self.users = user_repository

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

    def _draw_random_tier(self) -> tuple[str, float]:
        """
        Draw a random discount tier based on weights.

        Returns:
            Tuple of (tier_name, discount_rate)
            e.g., ('SR', 0.7) means 30% off, pay 70%
        """
        # Create weighted list
        tier_pool = []
        for tier, weight in self.TIER_WEIGHTS.items():
            tier_pool.extend([tier] * weight)

        # Random draw
        selected_tier = random.choice(tier_pool)

        # Get tier info from constants
        tier_info = DISCOUNT_TIERS[selected_tier]
        rate = tier_info['rate']

        logger.debug(f"Drew discount tier: {selected_tier} ({tier_info['off']} off)")
        return selected_tier, rate

    async def track_user_interaction(self, user_id: int):
        """
        Track user interaction and update interaction days.

        Note: This is kept for potential future use, but no longer
        affects discount calculation.

        Args:
            user_id: User ID
        """
        try:
            current_date = self.get_current_date_gmt8()
            self.users.update_interaction(user_id, current_date)
        except Exception as e:
            logger.error(f"Error tracking interaction for user {user_id}: {e}")

    async def peek_discount_tier(self, user_id: int) -> Optional[str]:
        """
        Peek at what discount tier the user has (if already revealed today).

        This does NOT draw a new discount - only returns existing one.

        Args:
            user_id: User ID

        Returns:
            Discount tier ('SSR', 'SR', 'R', 'C') or None if not revealed today
        """
        try:
            discount_info = self.users.get_discount_info(user_id)

            if not discount_info:
                return None

            # Check if already revealed today
            current_date = self.get_current_date_gmt8()
            if discount_info['daily_discount_date'] == current_date:
                return discount_info['daily_discount_tier']

            # Not revealed today
            return None

        except Exception as e:
            logger.error(f"Error peeking discount tier for user {user_id}: {e}")
            return None

    async def get_or_reveal_daily_discount(self, user_id: int) -> Dict:
        """
        Get today's discount for user. If not revealed yet, draw random tier.

        NEW BEHAVIOR: Random draw instead of calculation based on interaction days.

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
            discount_info = self.users.get_discount_info(user_id)

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
                    'display': tier_info['display'],
                    'emoji': tier_info['emoji'],
                    'off': tier_info['off'],
                    'is_new': False
                }

            # Draw new random discount for today
            tier, rate = self._draw_random_tier()

            # Save discount
            self.users.save_daily_discount(user_id, tier, rate, current_date)

            tier_info = DISCOUNT_TIERS[tier]
            logger.info(f"User {user_id} revealed discount: {tier} ({tier_info['off']} off)")

            return {
                'tier': tier,
                'rate': rate,
                'display': tier_info['display'],
                'emoji': tier_info['emoji'],
                'off': tier_info['off'],
                'is_new': True
            }

        except Exception as e:
            logger.error(f"Error getting daily discount for user {user_id}: {e}")
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
            discount_info = self.users.get_discount_info(user_id)

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
                        'display': tier_info['display'],
                        'emoji': tier_info['emoji'],
                        'off': tier_info['off']
                    }

            return None

        except Exception as e:
            logger.error(f"Error getting current discount for user {user_id}: {e}")
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
