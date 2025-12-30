"""WeChat/Alipay payment provider implementation for 3rd party acquirer."""

from typing import Dict, Optional
import logging
import hashlib
import aiohttp
from datetime import datetime
from .base_payment import PaymentProvider
from core.constants import PaymentStatus

logger = logging.getLogger('mark4_bot')


class WeChatAlipayProvider(PaymentProvider):
    """
    Payment provider for WeChat/Alipay via 3rd party acquirer.

    This is a placeholder implementation. Replace with actual API calls
    when you receive the acquirer's documentation.
    """

    def __init__(self, config):
        """
        Initialize WeChat/Alipay payment provider.

        Args:
            config: Configuration object
        """
        super().__init__(config)

        # Payment gateway configuration
        self.gateway_url = getattr(config, 'PAYMENT_GATEWAY_URL', None)
        self.merchant_id = getattr(config, 'PAYMENT_MERCHANT_ID', None)
        self.secret_key = getattr(config, 'PAYMENT_SECRET_KEY', None)
        self.notify_url = getattr(config, 'PAYMENT_NOTIFY_URL', None)
        self.callback_url = getattr(config, 'PAYMENT_CALLBACK_URL', None)

        # Validate required config
        if not all([self.gateway_url, self.merchant_id, self.secret_key,
                    self.notify_url, self.callback_url]):
            logger.warning(
                "Payment provider initialized with incomplete configuration. "
                "Payment features will not work until credentials are configured."
            )
        else:
            logger.info("Initialized WeChatAlipayProvider with live credentials")

    async def create_payment(
        self,
        user_id: int,
        amount: float,
        currency: str,
        payment_method: str = 'alipay',
        language_code: str = 'zh_CN'
    ) -> Dict:
        """
        Create a payment order with the 3rd party acquirer.

        Args:
            user_id: Telegram user ID
            amount: Payment amount
            currency: Currency code (CNY)
            payment_method: 'wechat' or 'alipay' (default: 'alipay')
            language_code: User's language preference for return page

        Returns:
            Dictionary with:
                - payment_id: str
                - payment_url: str (URL for user to complete payment)
                - status: PaymentStatus
        """
        try:
            # Validate configuration
            if not all([self.gateway_url, self.merchant_id, self.secret_key]):
                raise ValueError("Payment provider not configured. Check .env file.")

            # Generate unique payment ID (max 20 chars as per API spec)
            payment_id = f"{int(datetime.now().timestamp())}{user_id}"[:20]

            # Select payment type based on payment method
            # 剑来支付 uses: 'alipay' or 'wxpay'
            payment_type = 'alipay' if payment_method == 'alipay' else 'wxpay'

            # Add language parameter to return URL for translated HTML page
            return_url_with_lang = f"{self.callback_url}?lang={language_code}"

            # Prepare SIGNATURE parameters (all signed for new vendor)
            signature_params = {
                'pid': self.merchant_id,
                'type': payment_type,
                'out_trade_no': payment_id,
                'notify_url': self.notify_url,
                'return_url': return_url_with_lang,
                'name': '积分充值',
                'money': f"{amount:.2f}",
                'clientip': '8.8.8.8',  # Required by vendor (TODO: use real user IP)
                'device': 'jump'  # Required for API payments - using 'jump' for WeChat Pay
            }

            # Generate signature
            signature = self._generate_signature(signature_params)

            # Prepare FULL request parameters
            params = {
                **signature_params,
                'sign': signature,
                'sign_type': 'MD5'
            }

            # Make API request
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/mapi.php"

                async with session.post(
                    url,
                    data=params,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(
                            f"Payment creation failed: HTTP {resp.status}, "
                            f"Response: {error_text}"
                        )

                    # Get response text and try to parse as JSON
                    # Note: API returns Content-Type: text/html but body is actually JSON
                    response_text = await resp.text()

                    try:
                        import json
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        # Only log error if it's not actually JSON
                        content_type = resp.headers.get('Content-Type', '')
                        logger.error(
                            f"API returned invalid JSON. Content-Type: {content_type}. "
                            f"Parse error: {str(e)}. Response preview: {response_text[:300]}"
                        )
                        raise Exception(
                            f"API returned invalid response. Preview: {response_text[:150]}"
                        )

                    # Check response status (new vendor returns code=1 for success)
                    code = result.get('code')
                    if code != 1:
                        raise Exception(
                            f"Payment creation failed: {result.get('msg', 'Unknown error')}"
                        )

                    logger.info(
                        f"Created payment {payment_id} for user {user_id}: "
                        f"¥{amount} via {payment_method}"
                    )

                    # New vendor returns 'payurl', 'qrcode', or 'urlscheme'
                    payment_url = result.get('payurl') or result.get('qrcode') or result.get('urlscheme')

                    return {
                        'payment_id': payment_id,
                        'payment_url': payment_url,
                        'platform_order_id': result.get('trade_no'),
                        'status': PaymentStatus.PENDING
                    }

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise

    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Check payment status via API query.

        Args:
            payment_id: Payment ID to check

        Returns:
            PaymentStatus enum value
        """
        try:
            # Validate configuration
            if not all([self.gateway_url, self.merchant_id, self.secret_key]):
                raise ValueError("Payment provider not configured")

            # Prepare query parameters
            params = {
                'act': 'order',
                'pid': self.merchant_id,
                'key': self.secret_key,
                'out_trade_no': payment_id
            }

            # Make API request (GET request to /api.php)
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/api.php"

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"Status check failed: HTTP {resp.status}")
                        return PaymentStatus.FAILED

                    result = await resp.json()

                    # Check response code
                    code = result.get('code')
                    if code != 1:
                        logger.warning(f"Query failed for {payment_id}: {result.get('msg')}")
                        return PaymentStatus.PENDING

                    # Map status to our PaymentStatus
                    # Note: API query uses 'status' field (1=paid, 0=unpaid)
                    # Callback uses 'trade_status' field ('TRADE_SUCCESS'=paid)
                    # API returns status as string "1" or "0", not integer
                    status = result.get('status')

                    if status == 1 or status == "1":
                        logger.info(f"Payment {payment_id} confirmed as completed")
                        return PaymentStatus.COMPLETED
                    elif status == 0 or status == "0":
                        logger.info(f"Payment {payment_id} still pending")
                        return PaymentStatus.PENDING
                    else:
                        # Unknown status
                        logger.warning(f"Payment {payment_id} has unknown status: {status}")
                        return PaymentStatus.FAILED

        except Exception as e:
            logger.error(f"Error checking payment status {payment_id}: {str(e)}")
            return PaymentStatus.FAILED

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> bool:
        """
        Refund a payment (full or partial).

        Note: Refunds are not implemented per requirements.

        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None for full refund)

        Returns:
            True if refund successful
        """
        # No refunds per requirements
        logger.warning(
            f"Refund requested for payment {payment_id}, amount {amount}. "
            "Refunds not implemented (per requirements)."
        )
        return False

    async def get_payment_details(self, payment_id: str) -> Dict:
        """
        Get detailed payment information via query API.

        Args:
            payment_id: Payment ID

        Returns:
            Dictionary with payment details including:
                - payment_id: Order ID
                - status: Payment status
                - amount: Payment amount
                - transaction_id: Platform transaction ID (if completed)
        """
        try:
            # Validate configuration
            if not all([self.gateway_url, self.merchant_id, self.secret_key]):
                raise ValueError("Payment provider not configured")

            # Prepare query parameters
            params = {
                'act': 'order',
                'pid': self.merchant_id,
                'key': self.secret_key,
                'out_trade_no': payment_id
            }

            # Make API request
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/api.php"

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"Query failed: HTTP {resp.status}")
                        return {}

                    result = await resp.json()

                    # Check response code
                    if result.get('code') != 1:
                        return {}

                    # Parse and return payment details
                    # Note: API query uses 'status' field (1=paid, 0=unpaid)
                    # API returns status as string "1" or "0", not integer
                    status = result.get('status')
                    return {
                        'payment_id': result.get('out_trade_no', payment_id),
                        'status': 'COMPLETED' if (status == 1 or status == "1") else 'PENDING',
                        'amount': result.get('money'),
                        'transaction_id': result.get('trade_no'),
                        'vendor_status': status
                    }

        except Exception as e:
            logger.error(f"Error getting payment details {payment_id}: {str(e)}")
            return {}

    def _generate_signature(self, params: Dict) -> str:
        """
        Generate MD5 signature for API requests.

        Algorithm per payment vendor documentation:
        1. Filter out empty values, 'sign', and 'sign_type'
        2. Sort parameters alphabetically by key (ASCII)
        3. Format as key1=value1&key2=value2&...
        4. Append SECRET_KEY directly (no &key=)
        5. Generate MD5 hash and convert to lowercase

        Args:
            params: Request parameters (dict)

        Returns:
            MD5 signature string (lowercase)
        """
        # Filter out empty values and the sign fields
        filtered_params = {
            k: v for k, v in params.items()
            if v is not None and v != '' and k not in ['sign', 'sign_type']
        }

        # Sort parameters alphabetically by key
        sorted_params = sorted(filtered_params.items())

        # Create signature string
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # Append secret key directly (no &key= prefix)
        sign_str += self.secret_key

        # Generate MD5 hash and convert to lowercase
        signature = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()

        logger.debug(f"Signature string: {sign_str}")
        logger.debug(f"Generated signature: {signature}")

        return signature

    async def handle_callback(self, callback_data: Dict) -> Dict:
        """
        Handle payment callback/webhook from payment vendor.

        Verifies signature and processes payment notification.

        Args:
            callback_data: Callback data from payment vendor containing:
                - pid: Merchant ID
                - trade_no: Platform transaction ID
                - out_trade_no: Our order ID
                - type: Payment method (alipay/wxpay)
                - name: Product name
                - money: Payment amount
                - trade_status: Status ('TRADE_SUCCESS' = success)
                - param: Custom parameter (echoed back)
                - sign: MD5 signature
                - sign_type: Signature type (MD5)

        Returns:
            Dictionary with:
                - status: 'success' or 'error'
                - payment_id: Order ID (if success)
                - payment_status: 'PAID', 'PENDING', or 'FAILED'
                - message: Error message (if error)
        """
        try:
            # 1. Verify signature
            received_signature = callback_data.get('sign', '')

            # Create params dict without sign and sign_type
            params_to_verify = {
                k: v for k, v in callback_data.items()
                if k not in ['sign', 'sign_type']
            }

            # Log callback data for debugging
            logger.info(f"Callback data received: {list(callback_data.keys())}")
            logger.debug(f"Full callback data: {callback_data}")
            logger.debug(f"Params to verify (sorted): {sorted(params_to_verify.items())}")

            calculated_signature = self._generate_signature(params_to_verify)

            if received_signature.lower() != calculated_signature.lower():
                logger.error(
                    f"Invalid callback signature! "
                    f"Received: {received_signature[:10]}..., "
                    f"Calculated: {calculated_signature[:10]}... "
                    f"Full received: {received_signature}, "
                    f"Full calculated: {calculated_signature}"
                )
                return {
                    'status': 'error',
                    'message': 'Invalid signature'
                }

            # 2. Extract payment information
            payment_id = callback_data.get('out_trade_no')
            amount = callback_data.get('money')
            transaction_id = callback_data.get('trade_no')
            trade_status = callback_data.get('trade_status')
            payment_type = callback_data.get('type')

            if not payment_id:
                logger.error("Missing out_trade_no in callback data")
                return {
                    'status': 'error',
                    'message': 'Missing order ID'
                }

            # 3. Determine payment status based on trade_status
            if trade_status == 'TRADE_SUCCESS':
                payment_status = 'PAID'
                logger.info(
                    f"Payment callback received: {payment_id} = ¥{amount}, "
                    f"transaction_id: {transaction_id}, type: {payment_type}"
                )
            else:
                payment_status = 'FAILED'
                logger.warning(
                    f"Payment callback with non-success status: {payment_id}, "
                    f"trade_status: {trade_status}"
                )

            # 4. Return result
            return {
                'status': 'success',
                'payment_id': payment_id,
                'payment_status': payment_status,
                'amount': amount,
                'transaction_id': transaction_id,
                'payment_time': None  # New vendor doesn't provide timestamp in callback
            }

        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
