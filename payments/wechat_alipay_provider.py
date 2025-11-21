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
        self.bankcode_wechat = getattr(config, 'PAYMENT_BANKCODE_WECHAT', '998')
        self.bankcode_alipay = getattr(config, 'PAYMENT_BANKCODE_ALIPAY', '999')

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
        payment_method: str = 'alipay'
    ) -> Dict:
        """
        Create a payment order with the 3rd party acquirer.

        Args:
            user_id: Telegram user ID
            amount: Payment amount
            currency: Currency code (CNY)
            payment_method: 'wechat' or 'alipay' (default: 'alipay')

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

            # Select bank code based on payment method
            bankcode = self.bankcode_alipay if payment_method == 'alipay' else self.bankcode_wechat

            # Prepare request parameters
            params = {
                'pay_memberid': self.merchant_id,
                'pay_orderid': payment_id,
                'pay_amount': f"{amount:.2f}",
                'pay_bankcode': bankcode,
                'pay_notifyurl': self.notify_url,
                'pay_callbackurl': self.callback_url
            }

            # Generate signature
            signature = self._generate_signature(params)
            params['pay_md5sign'] = signature

            # Make API request
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/Pay_Index.html"

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

                    result = await resp.json()

                    # Check response status
                    if result.get('status') != 1:
                        raise Exception(
                            f"Payment creation failed: {result.get('msg', 'Unknown error')}"
                        )

                    logger.info(
                        f"Created payment {payment_id} for user {user_id}: "
                        f"¥{amount} via {payment_method}"
                    )

                    return {
                        'payment_id': payment_id,
                        'payment_url': result.get('h5_url'),
                        'platform_order_id': result.get('mch_order_id'),
                        'status': PaymentStatus.PENDING
                    }

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise

    async def check_payment_status(self, payment_id: str) -> PaymentStatus:
        """
        Check payment status with the acquirer.

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
                'pay_memberid': self.merchant_id,
                'pay_orderid': payment_id
            }

            # Generate signature
            signature = self._generate_signature(params)
            params['pay_md5sign'] = signature

            # Make API request
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/Pay_Trade_query.html"

                async with session.post(
                    url,
                    data=params,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Status check failed: HTTP {resp.status}")
                        return PaymentStatus.FAILED

                    result = await resp.json()

                    # Map API status to our PaymentStatus
                    # returncode: '00' = success, others = pending/failed
                    returncode = result.get('returncode', '')

                    if returncode == '00':
                        logger.info(f"Payment {payment_id} confirmed as completed")
                        return PaymentStatus.COMPLETED
                    elif returncode == '':
                        # No status yet - still pending
                        return PaymentStatus.PENDING
                    else:
                        # Any other code means failed or cancelled
                        logger.warning(f"Payment {payment_id} has status code: {returncode}")
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
                - datetime: Payment completion time (if completed)
        """
        try:
            # Validate configuration
            if not all([self.gateway_url, self.merchant_id, self.secret_key]):
                raise ValueError("Payment provider not configured")

            # Prepare query parameters
            params = {
                'pay_memberid': self.merchant_id,
                'pay_orderid': payment_id
            }

            # Generate signature
            signature = self._generate_signature(params)
            params['pay_md5sign'] = signature

            # Make API request
            async with aiohttp.ClientSession() as session:
                url = f"{self.gateway_url}/Pay_Trade_query.html"

                async with session.post(
                    url,
                    data=params,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Query failed: HTTP {resp.status}")
                        return {}

                    result = await resp.json()

                    # Parse and return payment details
                    return {
                        'payment_id': result.get('orderid', payment_id),
                        'status': 'COMPLETED' if result.get('returncode') == '00' else 'PENDING',
                        'amount': result.get('amount'),
                        'transaction_id': result.get('transaction_id'),
                        'datetime': result.get('datetime'),
                        'returncode': result.get('returncode')
                    }

        except Exception as e:
            logger.error(f"Error getting payment details {payment_id}: {str(e)}")
            return {}

    def _generate_signature(self, params: Dict) -> str:
        """
        Generate MD5 signature for API requests.

        Algorithm per API documentation:
        1. Filter out empty values and 'pay_md5sign' if present
        2. Sort parameters alphabetically by key (ASCII)
        3. Format as key1=value1&key2=value2&...
        4. Append &key=SECRET_KEY
        5. Generate MD5 hash and convert to uppercase

        Args:
            params: Request parameters (dict)

        Returns:
            MD5 signature string (uppercase)
        """
        # Filter out empty values and the sign field itself
        filtered_params = {
            k: v for k, v in params.items()
            if v is not None and v != '' and k != 'pay_md5sign'
        }

        # Sort parameters alphabetically by key
        sorted_params = sorted(filtered_params.items())

        # Create signature string
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # Append secret key
        sign_str += f"&key={self.secret_key}"

        # Generate MD5 hash and convert to uppercase
        signature = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

        logger.debug(f"Generated signature for params: {list(filtered_params.keys())}")

        return signature

    async def handle_callback(self, callback_data: Dict) -> Dict:
        """
        Handle payment callback/webhook from acquirer.

        Verifies signature and processes payment notification.

        Args:
            callback_data: Callback data from acquirer containing:
                - memberid: Merchant ID
                - orderid: Order ID
                - amount: Payment amount
                - transaction_id: Platform transaction ID
                - datetime: Payment completion time
                - returncode: Status code ('00' = success)
                - sign: MD5 signature

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

            # Create params dict without the signature field
            params_to_verify = {
                k: v for k, v in callback_data.items()
                if k != 'sign' and k != 'attach'  # attach is not signed
            }

            calculated_signature = self._generate_signature(params_to_verify)

            if received_signature.upper() != calculated_signature.upper():
                logger.error(
                    f"Invalid callback signature! "
                    f"Received: {received_signature[:10]}..., "
                    f"Calculated: {calculated_signature[:10]}..."
                )
                return {
                    'status': 'error',
                    'message': 'Invalid signature'
                }

            # 2. Extract payment information
            payment_id = callback_data.get('orderid')
            amount = callback_data.get('amount')
            transaction_id = callback_data.get('transaction_id')
            returncode = callback_data.get('returncode')
            payment_time = callback_data.get('datetime')

            if not payment_id:
                logger.error("Missing orderid in callback data")
                return {
                    'status': 'error',
                    'message': 'Missing order ID'
                }

            # 3. Determine payment status based on returncode
            if returncode == '00':
                payment_status = 'PAID'
                logger.info(
                    f"Payment callback received: {payment_id} = ¥{amount}, "
                    f"transaction_id: {transaction_id}, time: {payment_time}"
                )
            else:
                payment_status = 'FAILED'
                logger.warning(
                    f"Payment callback with non-success code: {payment_id}, "
                    f"returncode: {returncode}"
                )

            # 4. Return result
            return {
                'status': 'success',
                'payment_id': payment_id,
                'payment_status': payment_status,
                'amount': amount,
                'transaction_id': transaction_id,
                'payment_time': payment_time
            }

        except Exception as e:
            logger.error(f"Error handling callback: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }
