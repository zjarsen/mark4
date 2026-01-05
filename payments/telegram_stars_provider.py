"""Telegram Stars payment provider implementation."""

from typing import Dict, Optional
import logging
from datetime import datetime
from telegram import LabeledPrice
from .base_payment import PaymentProvider
from core.constants import PaymentStatus

logger = logging.getLogger('mark4_bot')


class TelegramStarsProvider(PaymentProvider):
    """
    Payment provider for Telegram Stars.

    Uses Telegram's native payment API with currency='XTR'.
    No external gateway required - payments are processed directly by Telegram.
    """

    def __init__(self, config, bot, translation_service=None):
        """
        Initialize Telegram Stars payment provider.

        Args:
            config: Configuration object
            bot: Telegram Bot instance for sending invoices
            translation_service: Translation service for multi-language support
        """
        super().__init__(config)
        self.bot = bot
        self.translation_service = translation_service
        logger.info("Initialized TelegramStarsProvider")

    async def create_payment(
        self,
        user_id: int,
        amount: float,
        currency: str,
        **kwargs
    ) -> Dict:
        """
        Create Telegram Stars invoice and send it to user.

        Args:
            user_id: Telegram user ID
            amount: Amount in Stars (e.g., 46.0)
            currency: Should be 'XTR' for Telegram Stars
            **kwargs: Additional parameters:
                - credits_amount: int - Credits to award
                - chat_id: int - Chat ID to send invoice to
                - base_amount_cny: int - Base CNY amount for reference

        Returns:
            Dictionary with:
                - payment_id: str - Unique payment identifier
                - payment_url: None - No external URL for Stars
                - status: PaymentStatus.PENDING
                - stars_amount: int - Amount in Stars

        Raises:
            ValueError: If currency is not 'XTR'
        """
        if currency != 'XTR':
            raise ValueError(f"Telegram Stars must use currency='XTR', got '{currency}'")

        try:
            # Generate unique payment ID
            payment_id = f"stars_{int(datetime.now().timestamp())}{user_id}"[:20]

            # Get parameters
            credits = kwargs.get('credits_amount', 0)
            chat_id = kwargs.get('chat_id', user_id)
            base_amount_cny = kwargs.get('base_amount_cny', 0)

            # Telegram Stars API requires integer amount
            stars_amount = int(amount)

            # Create invoice details with translation
            if self.translation_service:
                title = self.translation_service.get(user_id, 'payment.invoice_title_stars', credits=credits)
                description = self.translation_service.get(user_id, 'payment.invoice_description_stars', credits=credits)
                price_label = self.translation_service.get(user_id, 'payment.price_label_stars', credits=credits)
            else:
                title = f"充值 {credits} 积分"
                description = f"获得 {credits} 积分，永久有效"
                price_label = f"{credits}积分"

            # Payload is used to identify this payment when we receive successful_payment
            payload = payment_id

            logger.info(
                f"Creating Stars invoice for user {user_id}: "
                f"{stars_amount} Stars = {credits} credits (base: ¥{base_amount_cny})"
            )

            # Send invoice to user
            await self.bot.send_invoice(
                chat_id=chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token="",  # Empty for Telegram Stars
                currency="XTR",  # Telegram Stars currency code
                prices=[LabeledPrice(label=price_label, amount=stars_amount)]
            )

            logger.info(f"Sent Stars invoice {payment_id} to user {user_id}")

            return {
                'payment_id': payment_id,
                'payment_url': None,  # No external URL for Stars
                'status': PaymentStatus.PENDING,
                'stars_amount': stars_amount
            }

        except Exception as e:
            logger.error(f"Error creating Stars payment: {str(e)}", exc_info=True)
            raise

    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Check payment status via database.

        For Telegram Stars, payment confirmation comes via successful_payment update,
        not via polling. This method queries the database for the current status.

        Args:
            payment_id: Payment ID to check

        Returns:
            PaymentStatus enum value
        """
        # Note: This method requires database access, which should be injected
        # For now, we'll return PENDING as Stars payments are confirmed via webhook
        logger.warning(
            f"check_payment_status called for Stars payment {payment_id}. "
            "Stars payments are confirmed via successful_payment update, not polling."
        )
        return PaymentStatus.PENDING

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Refund a Telegram Stars payment.

        Note: Telegram Stars refunds are not currently supported by the API.

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)

        Returns:
            False (refunds not supported)
        """
        logger.warning(
            f"Refund requested for Stars payment {payment_id}. "
            "Telegram Stars refunds are not supported by the API."
        )
        return False

    async def get_payment_details(self, payment_id: str) -> Dict:
        """
        Get detailed payment information.

        For Stars payments, this queries the database as Telegram doesn't
        provide a query API for Stars transactions.

        Args:
            payment_id: Payment ID

        Returns:
            Dictionary with payment details (from database)
        """
        logger.info(f"Getting Stars payment details for {payment_id} (from database)")

        # Return minimal info - actual details should come from database
        return {
            'payment_id': payment_id,
            'provider': 'telegram_stars',
            'currency': 'XTR'
        }

    async def handle_successful_payment(self, successful_payment) -> Dict:
        """
        Handle successful_payment update from Telegram.

        This is called when the bot receives a successful_payment update after
        the user completes payment in the Telegram Stars payment flow.

        Args:
            successful_payment: SuccessfulPayment object from Telegram update

        Returns:
            Dictionary with:
                - status: 'success' or 'error'
                - payment_id: str - Our payment ID (from invoice payload)
                - payment_status: 'PAID' if successful
                - transaction_id: str - Telegram's payment charge ID
                - amount: int - Amount paid in Stars
                - message: str - Error message (if error)
        """
        try:
            # Extract payment information from successful_payment
            payment_id = successful_payment.invoice_payload
            telegram_payment_id = successful_payment.telegram_payment_charge_id
            total_amount = successful_payment.total_amount
            currency = successful_payment.currency

            # Verify currency
            if currency != 'XTR':
                logger.error(
                    f"Received non-Stars successful_payment: currency={currency}"
                )
                return {
                    'status': 'error',
                    'message': f'Invalid currency: {currency}'
                }

            logger.info(
                f"Received Stars successful_payment: {payment_id}, "
                f"telegram_id={telegram_payment_id}, amount={total_amount} Stars"
            )

            return {
                'status': 'success',
                'payment_id': payment_id,
                'payment_status': 'PAID',
                'transaction_id': telegram_payment_id,
                'amount': total_amount,
                'currency': currency
            }

        except Exception as e:
            logger.error(
                f"Error handling successful Stars payment: {str(e)}",
                exc_info=True
            )
            return {
                'status': 'error',
                'message': str(e)
            }
