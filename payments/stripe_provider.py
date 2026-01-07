"""Stripe payment provider for credit card, Apple Pay, and Google Pay."""

import stripe
import logging
from typing import Dict, Optional
from payments.base_payment import PaymentProvider
from core.constants import PaymentStatus

logger = logging.getLogger('mark4_bot')


class StripeProvider(PaymentProvider):
    """
    Stripe payment provider using Embedded Checkout.

    Supports credit cards, Apple Pay, and Google Pay through
    Stripe's Embedded Checkout flow in a Telegram Mini App.
    """

    def __init__(self, config):
        """
        Initialize Stripe provider.

        Args:
            config: Configuration object with Stripe keys
        """
        super().__init__(config)
        self.secret_key = config.STRIPE_SECRET_KEY
        self.publishable_key = config.STRIPE_PUBLISHABLE_KEY
        self.webhook_secret = config.STRIPE_WEBHOOK_SECRET

        # Initialize Stripe with secret key
        if self.secret_key:
            stripe.api_key = self.secret_key
            logger.info("Stripe provider initialized")
        else:
            logger.warning("Stripe secret key not configured")

    async def create_payment(
        self,
        user_id: int,
        amount: float,
        currency: str,
        **kwargs
    ) -> Dict:
        """
        Create a Stripe Checkout Session for embedded mode.

        Args:
            user_id: Telegram user ID
            amount: Amount in cents (100 = $1.00)
            currency: Currency code (should be 'USD')
            **kwargs: Additional parameters:
                - credits: Number of credits to award
                - return_url: Base URL for checkout page
                - payment_id: Pre-generated payment ID for tracking

        Returns:
            Dictionary with:
                - payment_id: Stripe session ID
                - client_secret: For mounting embedded checkout
                - checkout_url: URL to open in Mini App
                - status: PaymentStatus.PENDING
        """
        try:
            credits = kwargs.get('credits', 0)
            base_url = kwargs.get('return_url', 'https://telepay.swee.live')
            payment_id = kwargs.get('payment_id')
            vip_tier = kwargs.get('vip_tier')  # 'vip' or 'black_gold' or None

            # Determine product name and description based on VIP tier
            if vip_tier == 'vip':
                product_name = 'Lifetime VIP'
                product_description = 'Unlimited credits forever - no daily limits'
            elif vip_tier == 'black_gold':
                product_name = 'Black Gold VIP'
                product_description = 'Unlimited credits + Priority queue - the ultimate package'
            else:
                product_name = f'{credits} Credits'
                product_description = f'Top-up {credits} credits for your account'

            # Create Checkout Session with embedded mode
            session = stripe.checkout.Session.create(
                ui_mode='embedded',
                mode='payment',
                line_items=[{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': product_name,
                            'description': product_description,
                        },
                        'unit_amount': int(amount),  # Amount in cents
                    },
                    'quantity': 1,
                }],
                # Return URL with session ID template
                return_url=f'{base_url}/stripe/return?session_id={{CHECKOUT_SESSION_ID}}',
                # Store metadata for webhook processing
                metadata={
                    'user_id': str(user_id),
                    'credits': str(credits),
                    'internal_payment_id': payment_id or '',
                    'vip_tier': vip_tier or '',
                },
                # Enable automatic tax calculation (optional)
                # automatic_tax={'enabled': True},
            )

            logger.info(
                f"Created Stripe checkout session {session.id} for user {user_id}: "
                f"${amount/100:.2f} = {credits} credits"
            )

            return {
                'payment_id': session.id,
                'client_secret': session.client_secret,
                'checkout_url': f'{base_url}/stripe/checkout?session_id={session.id}',
                'status': PaymentStatus.PENDING,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating Stripe payment: {str(e)}")
            raise

    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Check the status of a Stripe Checkout Session.

        Args:
            payment_id: Stripe session ID

        Returns:
            PaymentStatus enum value
        """
        try:
            session = stripe.checkout.Session.retrieve(payment_id)

            status_map = {
                'complete': PaymentStatus.COMPLETED,
                'expired': PaymentStatus.CANCELLED,
                'open': PaymentStatus.PENDING,
            }

            return status_map.get(session.status, PaymentStatus.PENDING)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error checking session status: {str(e)}")
            return PaymentStatus.PENDING

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Refund a Stripe payment.

        Args:
            payment_id: Stripe session ID
            amount: Amount to refund in cents (None for full refund)

        Returns:
            True if refund successful
        """
        try:
            # Get the payment intent from the session
            session = stripe.checkout.Session.retrieve(payment_id)
            payment_intent_id = session.payment_intent

            if not payment_intent_id:
                logger.error(f"No payment intent found for session {payment_id}")
                return False

            # Create refund
            refund_params = {'payment_intent': payment_intent_id}
            if amount is not None:
                refund_params['amount'] = int(amount)

            refund = stripe.Refund.create(**refund_params)

            logger.info(
                f"Refunded Stripe payment {payment_id}: "
                f"refund_id={refund.id}, amount=${refund.amount/100:.2f}"
            )
            return True

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error refunding payment: {str(e)}")
            return False

    async def get_payment_details(self, payment_id: str) -> Dict:
        """
        Get detailed information about a Stripe Checkout Session.

        Args:
            payment_id: Stripe session ID

        Returns:
            Dictionary with session details
        """
        try:
            session = stripe.checkout.Session.retrieve(payment_id)

            return {
                'session_id': session.id,
                'status': session.status,
                'payment_status': session.payment_status,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'customer_email': session.customer_details.email if session.customer_details else None,
                'metadata': session.metadata,
                'created': session.created,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting session details: {str(e)}")
            return {}

    def verify_webhook_signature(self, payload: bytes, sig_header: str) -> Dict:
        """
        Verify Stripe webhook signature and parse event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Parsed Stripe event object

        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {str(e)}")
            raise ValueError("Invalid webhook signature")

    async def handle_webhook_event(self, event: Dict) -> Dict:
        """
        Process a Stripe webhook event.

        Args:
            event: Parsed Stripe event object

        Returns:
            Dictionary with:
                - success: bool
                - payment_id: Session ID (if applicable)
                - user_id: Telegram user ID (if applicable)
                - credits: Credits to award (if applicable)
                - message: Status message
        """
        event_type = event['type']
        logger.info(f"Processing Stripe webhook event: {event_type}")

        if event_type == 'checkout.session.completed':
            session = event['data']['object']

            # Extract metadata
            metadata = session.get('metadata', {})
            user_id = metadata.get('user_id')
            credits = metadata.get('credits')
            internal_payment_id = metadata.get('internal_payment_id')
            vip_tier = metadata.get('vip_tier') or None  # 'vip', 'black_gold', or None

            if session['payment_status'] == 'paid':
                logger.info(
                    f"Stripe payment completed: session={session['id']}, "
                    f"user={user_id}, credits={credits}, vip_tier={vip_tier}"
                )
                return {
                    'success': True,
                    'payment_id': session['id'],
                    'internal_payment_id': internal_payment_id,
                    'user_id': int(user_id) if user_id else None,
                    'credits': int(credits) if credits else 0,
                    'vip_tier': vip_tier,
                    'amount': session['amount_total'],
                    'currency': session['currency'],
                    'message': 'Payment completed successfully',
                }
            else:
                logger.warning(
                    f"Stripe session completed but not paid: {session['id']}, "
                    f"payment_status={session['payment_status']}"
                )
                return {
                    'success': False,
                    'payment_id': session['id'],
                    'message': f"Payment not completed: {session['payment_status']}",
                }

        elif event_type == 'checkout.session.expired':
            session = event['data']['object']
            logger.info(f"Stripe checkout session expired: {session['id']}")
            return {
                'success': False,
                'payment_id': session['id'],
                'message': 'Checkout session expired',
            }

        else:
            # Unhandled event type
            logger.debug(f"Ignoring Stripe event type: {event_type}")
            return {
                'success': True,
                'message': f'Event type {event_type} ignored',
            }

    def get_publishable_key(self) -> str:
        """
        Get the Stripe publishable key for client-side use.

        Returns:
            Stripe publishable key
        """
        return self.publishable_key
