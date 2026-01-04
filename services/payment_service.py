"""Payment service for handling top-ups and payment processing."""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from core.constants import PaymentStatus, TOPUP_PACKAGES

logger = logging.getLogger('mark4_bot')


class PaymentService:
    """Service for managing payments and connecting with credit system."""

    def __init__(self, config, database_service, credit_service, payment_provider, stars_provider=None):
        """
        Initialize payment service.

        Args:
            config: Configuration object
            database_service: DatabaseService instance
            credit_service: CreditService instance
            payment_provider: Payment provider instance (WeChatAlipayProvider)
            stars_provider: Telegram Stars payment provider (optional)
        """
        self.config = config
        self.db = database_service
        self.credit_service = credit_service
        self.payment_provider = payment_provider
        self.stars_provider = stars_provider

    def get_topup_packages(self) -> Dict[int, int]:
        """
        Get available top-up packages.

        Returns:
            Dictionary of {amount_cny: credits}
        """
        return TOPUP_PACKAGES

    def calculate_credits_for_amount(self, amount_cny: int) -> Optional[int]:
        """
        Calculate credits for a given CNY amount.

        Supports discounted amounts by finding the closest matching package.

        Args:
            amount_cny: Amount in CNY (may be discounted)

        Returns:
            Credits amount or None if invalid package
        """
        # Try exact match first
        if amount_cny in TOPUP_PACKAGES:
            return TOPUP_PACKAGES[amount_cny]

        # If not exact match, try to find base package (for discounted amounts)
        # Discounts range from 50% to 95% (SSR to C tier)
        # So discounted amount should be 50-95% of a base package
        for base_amount, credits in TOPUP_PACKAGES.items():
            # Check if amount_cny could be a discounted version of base_amount
            # Allow 45-100% range to account for rounding
            if 0.45 * base_amount <= amount_cny <= base_amount:
                return credits

        return None

    async def create_topup_payment(
        self,
        user_id: int,
        amount_cny: int,
        payment_method: str = 'alipay',
        chat_id: int = None,
        message_id: int = None,
        language_code: str = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Create a top-up payment order.

        Args:
            user_id: User ID
            amount_cny: Amount in CNY (must be a valid package: 1, 10, 30, 50, or 100)
            payment_method: Payment method ('alipay' or 'wechat', default: 'alipay')
            chat_id: Optional Telegram chat ID for message editing
            message_id: Optional Telegram message ID for editing after payment
            language_code: User's language preference for webhook translation

        Returns:
            Tuple of (success, payment_info, error_message)
            payment_info contains: payment_id, payment_url, credits_amount
        """
        try:
            # Get user's language if not provided
            if language_code is None:
                language_code = self.db.get_user_language(user_id)

            # Validate payment method
            if payment_method not in ['alipay', 'wechat']:
                return False, None, f"Invalid payment method: {payment_method}. Must be 'alipay' or 'wechat'."

            # Validate package (supports discounted amounts)
            credits_amount = self.calculate_credits_for_amount(amount_cny)
            if credits_amount is None:
                return False, None, f"Invalid top-up amount: {amount_cny}. Please select a valid package."

            # Create payment with provider (pass language for return URL)
            payment_result = await self.payment_provider.create_payment(
                user_id=user_id,
                amount=float(amount_cny),
                currency='CNY',
                payment_method=payment_method,
                language_code=language_code
            )

            payment_id = payment_result['payment_id']
            payment_url = payment_result['payment_url']
            status = payment_result['status']

            # Record payment in database with language
            success = self.db.create_payment_record(
                payment_id=payment_id,
                user_id=user_id,
                provider='wechat_alipay',
                amount=float(amount_cny),
                currency='CNY',
                credits_amount=float(credits_amount),
                status=status.value,
                payment_url=payment_url,
                chat_id=chat_id,
                message_id=message_id,
                language_code=language_code,
                payment_method=payment_method
            )

            if not success:
                logger.error(f"Failed to record payment {payment_id} in database")
                return False, None, "Failed to create payment record"

            logger.info(
                f"Created payment {payment_id} for user {user_id}: "
                f"¥{amount_cny} = {credits_amount} credits"
            )

            return True, {
                'payment_id': payment_id,
                'payment_url': payment_url,
                'credits_amount': credits_amount,
                'amount_cny': amount_cny
            }, None

        except Exception as e:
            logger.error(f"Error creating top-up payment for user {user_id}: {str(e)}")
            return False, None, str(e)

    async def create_topup_payment_stars(
        self,
        user_id: int,
        amount_stars: int,
        base_amount_cny: int,
        credits_amount: int,
        chat_id: int = None,
        language_code: str = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Create a Telegram Stars top-up payment order.

        Args:
            user_id: User ID
            amount_stars: Amount in Telegram Stars (XTR)
            base_amount_cny: Base CNY amount for reference (10, 30, 50, 100, 160, 260)
            credits_amount: Credits to award
            chat_id: Optional Telegram chat ID for invoice
            language_code: User's language preference

        Returns:
            Tuple of (success, payment_info, error_message)
            payment_info contains: payment_id, stars_amount
        """
        try:
            # Validate stars provider
            if not self.stars_provider:
                return False, None, "Telegram Stars provider not available"

            # Get user's language if not provided
            if language_code is None:
                language_code = self.db.get_user_language(user_id)

            # Create payment with Stars provider
            payment_result = await self.stars_provider.create_payment(
                user_id=user_id,
                amount=float(amount_stars),
                currency='XTR',
                credits_amount=credits_amount,
                chat_id=chat_id or user_id,
                base_amount_cny=base_amount_cny
            )

            payment_id = payment_result['payment_id']
            stars_amount = payment_result['stars_amount']
            status = payment_result['status']

            # Record payment in database
            success = self.db.create_payment_record(
                payment_id=payment_id,
                user_id=user_id,
                provider='telegram_stars',
                amount=float(stars_amount),
                currency='XTR',
                credits_amount=float(credits_amount),
                status=status.value,
                payment_url=None,  # No external URL for Stars
                chat_id=chat_id,
                message_id=None,  # Stars don't need message tracking
                language_code=language_code,
                payment_method='stars'
            )

            if not success:
                logger.error(f"Failed to record Stars payment {payment_id} in database")
                return False, None, "Failed to create payment record"

            logger.info(
                f"Created Stars payment {payment_id} for user {user_id}: "
                f"{stars_amount} Stars (¥{base_amount_cny}) = {credits_amount} credits"
            )

            return True, {
                'payment_id': payment_id,
                'stars_amount': stars_amount,
                'credits_amount': credits_amount,
                'base_amount_cny': base_amount_cny
            }, None

        except Exception as e:
            logger.error(f"Error creating Stars payment for user {user_id}: {str(e)}", exc_info=True)
            return False, None, str(e)

    async def check_payment_status(self, payment_id: str) -> Optional[PaymentStatus]:
        """
        Check payment status.

        Args:
            payment_id: Payment ID

        Returns:
            PaymentStatus or None
        """
        try:
            status = await self.payment_provider.check_payment_status(payment_id)
            return status

        except Exception as e:
            logger.error(f"Error checking payment status {payment_id}: {str(e)}")
            return None

    async def process_payment_completion(
        self,
        payment_id: str
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Process a completed payment and credit the user's account (VIP-aware).

        Args:
            payment_id: Payment ID

        Returns:
            Tuple of (success, new_balance, error_message)
        """
        try:
            # Get payment record
            payment = self.db.get_payment(payment_id)
            if not payment:
                return False, None, "Payment not found"

            # Check if already processed
            if payment['status'] == PaymentStatus.COMPLETED.value:
                logger.warning(f"Payment {payment_id} already completed")
                return False, None, "Payment already processed"

            # Verify payment with provider
            status = await self.check_payment_status(payment_id)
            if status != PaymentStatus.COMPLETED:
                logger.warning(
                    f"Payment {payment_id} not completed yet, status: {status}"
                )
                return False, None, f"Payment status: {status.value}"

            user_id = payment['user_id']
            credits_amount = payment['credits_amount']

            # Check if this is a VIP purchase
            # Handle None metadata (database NULL) by converting to empty string
            metadata = payment.get('metadata') or ''
            is_vip_purchase = metadata.startswith('vip_tier:')

            if is_vip_purchase:
                # VIP purchase - grant VIP status (includes credits)
                tier = metadata.split(':')[1] if ':' in metadata else 'vip'

                success, message = await self.credit_service.grant_vip_status(user_id, tier)

                if not success:
                    logger.error(
                        f"Failed to grant VIP status to user {user_id} for payment {payment_id}: {message}"
                    )
                    return False, None, f"VIP授予失败: {message}"

                # Get new balance
                new_balance = await self.credit_service.get_balance(user_id)

                # Update payment status
                self.db.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.COMPLETED.value,
                    completed_at=datetime.now()
                )

                logger.info(
                    f"Completed VIP payment {payment_id} for user {user_id}: "
                    f"granted {tier} status, new balance: {new_balance}"
                )

                return True, new_balance, None

            else:
                # Regular credit purchase
                success, new_balance = await self.credit_service.add_credits(
                    user_id=user_id,
                    amount=credits_amount,
                    description=f"充值 ¥{payment['amount']}",
                    reference_id=payment_id
                )

                if not success:
                    logger.error(f"Failed to credit user {user_id} for payment {payment_id}")
                    return False, None, "Failed to add credits"

                # Update payment status
                self.db.update_payment_status(
                    payment_id=payment_id,
                    status=PaymentStatus.COMPLETED.value,
                    completed_at=datetime.now()
                )

                logger.info(
                    f"Completed payment {payment_id} for user {user_id}: "
                    f"credited {credits_amount} credits, new balance: {new_balance}"
                )

                return True, new_balance, None

        except Exception as e:
            logger.error(f"Error processing payment completion {payment_id}: {str(e)}")
            return False, None, str(e)

    async def process_payment_callback(
        self,
        callback_data: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Process payment callback from provider.

        Args:
            callback_data: Callback data from payment provider

        Returns:
            Tuple of (success, payment_id)
        """
        try:
            # Handle callback with provider
            result = await self.payment_provider.handle_callback(callback_data)

            if result['status'] != 'success':
                logger.error(f"Callback processing failed: {result.get('message')}")
                return False, None

            payment_id = result['payment_id']
            payment_status = result['payment_status']

            # If payment is completed, process it
            if payment_status == 'PAID':
                success, new_balance, error = await self.process_payment_completion(payment_id)
                if success:
                    logger.info(f"Successfully processed callback for payment {payment_id}")
                    return True, payment_id
                else:
                    logger.error(f"Failed to process completed payment {payment_id}: {error}")
                    return False, payment_id
            else:
                # Update status in database
                self.db.update_payment_status(
                    payment_id=payment_id,
                    status=payment_status
                )
                logger.info(f"Updated payment {payment_id} status to {payment_status}")
                return True, payment_id

        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}")
            return False, None

    async def get_payment_info(self, payment_id: str) -> Optional[Dict]:
        """
        Get payment information.

        Args:
            payment_id: Payment ID

        Returns:
            Payment dictionary or None
        """
        try:
            payment = self.db.get_payment(payment_id)
            return payment

        except Exception as e:
            logger.error(f"Error getting payment info {payment_id}: {str(e)}")
            return None

    async def cancel_payment(self, payment_id: str) -> bool:
        """
        Cancel a pending payment.

        Args:
            payment_id: Payment ID

        Returns:
            True if successful
        """
        try:
            payment = self.db.get_payment(payment_id)
            if not payment:
                return False

            if payment['status'] != PaymentStatus.PENDING.value:
                logger.warning(
                    f"Cannot cancel payment {payment_id} with status {payment['status']}"
                )
                return False

            # Update status to cancelled
            success = self.db.update_payment_status(
                payment_id=payment_id,
                status=PaymentStatus.CANCELLED.value
            )

            if success:
                logger.info(f"Cancelled payment {payment_id}")

            return success

        except Exception as e:
            logger.error(f"Error cancelling payment {payment_id}: {str(e)}")
            return False
