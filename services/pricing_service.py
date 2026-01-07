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
        },
        'stripe': {
            # Fixed USD pricing (no formula needed - use STRIPE_PACKAGES instead)
            'formula': lambda base: base,  # Pass-through (not used for Stripe)
            'currency': 'USD',
            'display_format': '${price:.2f}',
            'discount_eligible_packages': [500, 800, 1500, 2500, 4000],  # Exclude $2 (same logic as ¥10)
            'name': 'Card/Apple Pay/Google Pay'
        }
    }

    # Stripe-specific package definitions (fixed USD pricing)
    # Maps to CNY packages: ¥10→$2, ¥30→$5, ¥50→$8, ¥100→$15, ¥160→$25, ¥260→$40
    STRIPE_PACKAGES = {
        200: {'price_cents': 200, 'price_usd': 2.00, 'credits': 30, 'base_cny': 10},
        500: {'price_cents': 500, 'price_usd': 5.00, 'credits': 120, 'base_cny': 30},
        800: {'price_cents': 800, 'price_usd': 8.00, 'credits': 250, 'base_cny': 50},
        1500: {'price_cents': 1500, 'price_usd': 15.00, 'credits': 600, 'base_cny': 100},
        2500: {'price_cents': 2500, 'price_usd': 25.00, 'credits': 99999999, 'base_cny': 160, 'is_vip': True, 'vip_tier': 'vip'},
        4000: {'price_cents': 4000, 'price_usd': 40.00, 'credits': 99999999, 'base_cny': 260, 'is_vip': True, 'vip_tier': 'black_gold'},
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
        if payment_method == 'stripe':
            return config['display_format'].format(price=price)
        return config['display_format'].format(price=int(price))

    def get_stripe_packages(self) -> dict:
        """
        Get Stripe package definitions.

        Returns:
            Dictionary of Stripe packages with price and credit info
        """
        return self.STRIPE_PACKAGES

    def get_stripe_package(self, package_id: int) -> dict:
        """
        Get a specific Stripe package by ID.

        Args:
            package_id: Package ID (200 for $2, 500 for $5, etc.)

        Returns:
            Package dictionary with price_cents, price_usd, credits
        """
        return self.STRIPE_PACKAGES.get(package_id)

    def calculate_stripe_price(self, package_id: int, discount_rate: float = 1.0) -> dict:
        """
        Calculate Stripe price with optional discount.

        Args:
            package_id: Stripe package ID (price in cents: 200, 500, 800, 1500, 2500, 4000)
            discount_rate: Discount multiplier (1.0 = no discount, 0.5 = 50% off)

        Returns:
            Dictionary with price info including discounted values
        """
        package = self.STRIPE_PACKAGES.get(package_id)
        if not package:
            return None

        base_price_cents = package['price_cents']
        base_price_usd = package['price_usd']

        # Check if eligible for discount (exclude $2 package)
        is_eligible = package_id in self.PRICING_CONFIGS['stripe']['discount_eligible_packages']

        # Apply discount only if eligible
        actual_discount = discount_rate if is_eligible else 1.0

        # Calculate discounted price (round to nearest cent)
        final_price_cents = int(base_price_cents * actual_discount)
        final_price_usd = final_price_cents / 100

        return {
            'package_id': package_id,
            'base_price_cents': base_price_cents,
            'base_price_usd': base_price_usd,
            'final_price_cents': final_price_cents,
            'final_price_usd': final_price_usd,
            'discount_rate': actual_discount,
            'is_discount_eligible': is_eligible,
            'credits': package['credits'],
            'base_cny': package.get('base_cny'),
            'is_vip': package.get('is_vip', False),
            'vip_tier': package.get('vip_tier'),
            'savings_usd': base_price_usd - final_price_usd if is_eligible and actual_discount < 1.0 else 0,
        }
