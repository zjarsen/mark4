"""Pricing service for multi-payment-method support."""

import logging
from typing import Dict, List

logger = logging.getLogger('mark4_bot')


class PricingService:
    """
    Manages pricing calculations for different payment methods.

    Each payment method has its own pricing formula, transaction fees,
    and discount eligibility rules.
    """

    # Payment method configurations
    PRICING_CONFIGS = {
        'stars': {
            'commission': 0.35,  # Telegram takes 35% commission (30% Apple/Google + 5% Telegram)
            'stars_rate_cny': 0.14,  # User pays ¥0.14 per Star ($0.02 × 7.0 CNY/USD)
            'merchant_rate_cny': 0.091,  # Merchant receives ¥0.091 per Star (0.14 × 0.65)
            'formula': lambda base: int(base / 0.091),  # Stars needed for merchant to receive 'base' CNY
            'currency': 'XTR',
            'display_format': '{price} ⭐',
            'discount_eligible_packages': [10, 30, 50, 100, 160, 260],  # All packages eligible
            'name': 'Telegram Stars'
        },
        'alipay': {
            'transaction_fee': 0.08,  # 8% transaction fee
            'formula': lambda base: int(base * 1.08),  # Add 8% fee
            'currency': 'CNY',
            'display_format': '¥{price}',
            'discount_eligible_packages': [30, 50, 100, 160, 260],  # Exclude ¥10
            'name': '支付宝'
        },
        'wechat': {
            'transaction_fee': 0.08,  # 8% transaction fee
            'formula': lambda base: int(base * 1.08),  # Add 8% fee
            'currency': 'CNY',
            'display_format': '¥{price}',
            'discount_eligible_packages': [30, 50, 100, 160, 260],  # Exclude ¥10
            'name': '微信支付'
        }
    }

    def __init__(self):
        """Initialize pricing service."""
        pass

    def calculate_price(
        self,
        base_amount: int,
        payment_method: str,
        discount_rate: float = 1.0
    ) -> Dict:
        """
        Calculate final price with discount for a given payment method.

        Args:
            base_amount: Base CNY amount (10, 30, 50, 100, 160, 260)
            payment_method: Payment method ('stars', 'alipay', 'wechat')
            discount_rate: Discount multiplier (1.0 = no discount, 0.5 = 50% off)

        Returns:
            Dictionary with:
                - base_amount: Original base amount in CNY
                - base_price: Price before discount (in method's currency)
                - discount_rate: Applied discount rate
                - final_price: Final price after discount (in method's currency)
                - currency: Currency code ('XTR' or 'CNY')
                - display: Formatted price string for display
                - savings: Amount saved from discount
                - is_discount_eligible: Whether this package is eligible for discount

        Example:
            >>> pricing.calculate_price(30, 'stars', 0.5)
            {
                'base_amount': 30,
                'base_price': 330,
                'discount_rate': 0.5,
                'final_price': 165,
                'currency': 'XTR',
                'display': '165 ⭐',
                'savings': 165,
                'is_discount_eligible': True
            }
        """
        if payment_method not in self.PRICING_CONFIGS:
            raise ValueError(f"Unknown payment method: {payment_method}")

        config = self.PRICING_CONFIGS[payment_method]

        # Calculate base price using method's formula
        base_price = config['formula'](base_amount)

        # Check if this package is eligible for discount
        is_eligible = base_amount in config['discount_eligible_packages']

        # Apply discount only if eligible
        actual_discount = discount_rate if is_eligible else 1.0

        # Calculate final price
        final_price = int(base_price * actual_discount)

        # Calculate savings
        savings = base_price - final_price if is_eligible and actual_discount < 1.0 else 0

        # Format display string
        display = config['display_format'].format(price=final_price)

        return {
            'base_amount': base_amount,
            'base_price': base_price,
            'discount_rate': actual_discount,
            'final_price': final_price,
            'currency': config['currency'],
            'display': display,
            'savings': savings,
            'is_discount_eligible': is_eligible,
            'payment_method': payment_method
        }

    def get_pricing_config(self, payment_method: str) -> Dict:
        """
        Get pricing configuration for a payment method.

        Args:
            payment_method: Payment method ('stars', 'alipay', 'wechat')

        Returns:
            Configuration dictionary
        """
        if payment_method not in self.PRICING_CONFIGS:
            raise ValueError(f"Unknown payment method: {payment_method}")

        return self.PRICING_CONFIGS[payment_method]

    def get_available_methods(self) -> List[str]:
        """
        Get list of available payment methods.

        Returns:
            List of payment method names
        """
        return list(self.PRICING_CONFIGS.keys())

    def is_discount_eligible(self, base_amount: int, payment_method: str) -> bool:
        """
        Check if a package is eligible for discount with a given payment method.

        Args:
            base_amount: Base CNY amount
            payment_method: Payment method

        Returns:
            True if eligible for discount
        """
        config = self.get_pricing_config(payment_method)
        return base_amount in config['discount_eligible_packages']

    def format_price_display(self, price: float, payment_method: str) -> str:
        """
        Format price for display according to payment method.

        Args:
            price: Price amount
            payment_method: Payment method

        Returns:
            Formatted price string (e.g., "46 ⭐" or "¥32")
        """
        config = self.get_pricing_config(payment_method)
        return config['display_format'].format(price=int(price))
