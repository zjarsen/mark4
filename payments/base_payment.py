"""Base payment provider interface for future implementation."""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from core.constants import PaymentStatus


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.

    Implement this interface to add new payment providers (Stripe, Alipay, etc.)
    """

    def __init__(self, config):
        """
        Initialize payment provider.

        Args:
            config: Configuration object
        """
        self.config = config

    @abstractmethod
    async def create_payment(
        self,
        user_id: int,
        amount: float,
        currency: str
    ) -> Dict:
        """
        Create a payment and return payment info.

        Args:
            user_id: Telegram user ID
            amount: Payment amount
            currency: Currency code (USD, CNY, etc.)

        Returns:
            Dictionary with:
                - payment_id: str
                - payment_url: str (URL for user to complete payment)
                - status: PaymentStatus
        """
        pass

    @abstractmethod
    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Check if payment is completed.

        Args:
            payment_id: Payment ID to check

        Returns:
            PaymentStatus enum value
        """
        pass

    @abstractmethod
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Refund a payment (full or partial).

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)

        Returns:
            True if refund successful
        """
        pass

    @abstractmethod
    async def get_payment_details(self, payment_id: str) -> Dict:
        """
        Get detailed payment information.

        Args:
            payment_id: Payment ID

        Returns:
            Dictionary with payment details
        """
        pass


class PaymentManager:
    """
    Manager for multiple payment providers.

    Use this class to route payments to different providers based on user preference.
    """

    def __init__(self, config):
        """
        Initialize payment manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self.providers: Dict[str, PaymentProvider] = {}

        # TODO: Initialize payment providers here
        # Example:
        # self.providers['stripe'] = StripeProvider(config)
        # self.providers['alipay'] = AlipayProvider(config)

    def register_provider(self, name: str, provider: PaymentProvider):
        """
        Register a payment provider.

        Args:
            name: Provider name (e.g., 'stripe', 'alipay')
            provider: Provider instance
        """
        self.providers[name] = provider

    def get_provider(self, name: str) -> Optional[PaymentProvider]:
        """
        Get payment provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self.providers.get(name)

    async def create_payment(
        self,
        user_id: int,
        amount: float,
        currency: str,
        provider_name: str
    ) -> Dict:
        """
        Create payment with specified provider.

        Args:
            user_id: User ID
            amount: Payment amount
            currency: Currency code
            provider_name: Provider to use

        Returns:
            Payment info dictionary

        Raises:
            ValueError: If provider not found
        """
        provider = self.get_provider(provider_name)

        if not provider:
            raise ValueError(f"Payment provider '{provider_name}' not found")

        return await provider.create_payment(user_id, amount, currency)

# TODO: Implement specific payment providers
# Example structure:
#
# class StripeProvider(PaymentProvider):
#     async def create_payment(self, user_id, amount, currency):
#         # Stripe implementation
#         pass
#
# class AlipayProvider(PaymentProvider):
#     async def create_payment(self, user_id, amount, currency):
#         # Alipay implementation
#         pass
