"""
Payment webhook server for handling payment callbacks.

This server receives payment notifications from the payment provider
and processes them to credit user accounts.

Run with: python payment_webhook.py
"""

from flask import Flask, request, jsonify
import asyncio
import logging
from telegram import Bot
from config import Config

# New architecture imports
from database.connection import DatabaseConnection
from database.repositories.user_repo import UserRepository
from database.repositories.payment_repo import PaymentRepository
from database.repositories.transaction_repo import TransactionRepository
from domain.credits.service import CreditService
from services.payment_service import PaymentService
from payments.wechat_alipay_provider import WeChatAlipayProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('payment_webhook')

# Initialize Flask app
app = Flask(__name__)

# Initialize services with new architecture
config = Config()

# Database layer
conn_manager = DatabaseConnection(config.DATABASE_PATH)
user_repo = UserRepository(conn_manager)
payment_repo = PaymentRepository(conn_manager)
transaction_repo = TransactionRepository(conn_manager)

# Domain layer
feature_pricing = {
    'i2i_1': 0.0,   # Pink Bra - Free
    'i2i_2': 10.0,  # Full Undress
    'i2v_1': 30.0,  # Breast Bounce
    'i2v_2': 30.0,  # Lower Body Fluid
    'i2v_3': 30.0   # Oral
}
credit_service = CreditService(
    connection_manager=conn_manager,
    feature_pricing=feature_pricing
)

# Compatibility wrapper for payment_service (expects old database_service interface)
class PaymentRepoWrapper:
    """Wrapper to make PaymentRepository compatible with old database_service interface."""
    def __init__(self, payment_repo):
        self._repo = payment_repo

    def create_payment_record(self, **kwargs):
        """Create payment record (old interface)."""
        return self._repo.create(**kwargs)

    def get_payment(self, payment_id: str):
        """Get payment by ID (old interface)."""
        return self._repo.get_by_id(payment_id)

    def update_payment_status(self, payment_id: str, status: str):
        """Update payment status (old interface)."""
        return self._repo.update_status(payment_id, status)

# Payment layer
payment_provider = WeChatAlipayProvider(config)
payment_service = PaymentService(
    config,
    PaymentRepoWrapper(payment_repo),  # Wrap new repo with compatibility layer
    credit_service,
    payment_provider
)

# Initialize Telegram Bot for sending notifications
bot = Bot(token=config.BOT_TOKEN)

# Initialize payment timeout service
from services.payment_timeout_service import PaymentTimeoutService
timeout_service = PaymentTimeoutService(bot)


async def send_payment_notification(user_id: int, payment_id: str, credits: float, new_balance: float, chat_id: int = None, message_id: int = None):
    """
    Send payment success notification to user via Telegram.
    If chat_id and message_id are provided, edit the existing message.
    Otherwise, send a new message.

    Args:
        user_id: Telegram user ID
        payment_id: Payment ID
        credits: Credits added
        new_balance: New balance after payment
        chat_id: Optional chat ID for editing existing message
        message_id: Optional message ID for editing existing message
    """
    try:
        message = f"""✅ 支付成功！

💰 充值积分：{credits}
📊 当前余额：{new_balance} 积分

订单号：{payment_id}

感谢您的支持！"""

        if chat_id and message_id:
            # Edit the existing "等待支付中" message
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message
            )
            logger.info(f"Edited payment message for user {user_id} (msg: {message_id})")
        else:
            # Send new message if no message_id provided
            await bot.send_message(
                chat_id=user_id,
                text=message
            )
            logger.info(f"Sent payment notification to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send payment notification to user {user_id}: {str(e)}")


@app.route('/payment/callback', methods=['GET', 'POST'])
async def payment_callback():
    """
    Handle payment callback from payment provider.

    Supports both GET and POST methods:
    - Payment gateway sends GET requests with query parameters
    - POST method also supported for compatibility

    Common parameters:
    - pid: Merchant ID
    - out_trade_no: Order ID
    - trade_no: Platform transaction ID
    - money: Payment amount
    - trade_status: Payment status
    - sign: MD5 signature
    """
    try:
        # Get callback data from either query params (GET) or form (POST)
        if request.method == 'GET':
            callback_data = request.args.to_dict()
        else:
            callback_data = request.form.to_dict()

        logger.info(f"Received payment callback via {request.method}: {callback_data.get('out_trade_no') or callback_data.get('orderid')}")

        # Process callback with payment service
        success, payment_id = await payment_service.process_payment_callback(callback_data)

        if success:
            logger.info(f"Successfully processed payment callback: {payment_id}")

            # Send notification to user
            try:
                payment = payment_repo.get_by_id(payment_id)
                if payment:
                    user_id = payment['user_id']
                    credits = payment['credits_amount']
                    chat_id = payment.get('chat_id')
                    message_id = payment.get('message_id')

                    # Get user's new balance
                    user_stats = await credit_service.get_user_stats(user_id)
                    new_balance = user_stats['balance']

                    # Send notification (edit message if chat_id/message_id available)
                    await send_payment_notification(user_id, payment_id, credits, new_balance, chat_id, message_id)

                    # Cancel timeout timer and cleanup timeout messages
                    timeout_service.cancel_payment_timeout(user_id)
                    if chat_id:
                        await timeout_service.cleanup_timeout_messages(user_id, chat_id)
                    logger.debug(f"Cancelled timeout and cleaned up messages for user {user_id}")

            except Exception as e:
                # Don't fail the callback if notification fails
                logger.error(f"Failed to send notification for payment {payment_id}: {str(e)}")

            # CRITICAL: Vendor requires exactly "success" (lowercase)
            return "success", 200
        else:
            logger.error(f"Failed to process payment callback: {payment_id}")
            return "fail", 400

    except Exception as e:
        logger.error(f"Error handling payment callback: {str(e)}", exc_info=True)
        return "ERROR", 500


@app.route('/payment/return', methods=['GET'])
def payment_return():
    """
    Handle user return from payment page.

    This is where users are redirected after completing/cancelling payment.
    """
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <title>支付处理中</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            }
            h1 { color: #333; margin-bottom: 20px; }
            p { color: #666; font-size: 16px; line-height: 1.6; }
            .icon { font-size: 60px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">⏳</div>
            <h1>支付处理中</h1>
            <p>您的支付正在处理中，积分将在确认后自动到账。</p>
            <p>请返回 Telegram bot 查看您的余额。</p>
            <p style="margin-top: 30px; color: #999; font-size: 14px;">
                此页面可以关闭
            </p>
        </div>
    </body>
    </html>
    """, 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'payment_webhook'
    }), 200


if __name__ == '__main__':
    # Run Flask app
    # For production, use a production server like gunicorn or uwsgi
    # Example: gunicorn -w 4 -b 0.0.0.0:8080 payment_webhook:app

    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    logger.info(f"Starting payment webhook server on port {port}")
    logger.info(f"Callback URL: http://localhost:{port}/payment/callback")
    logger.info(f"Return URL: http://localhost:{port}/payment/return")

    # Enable async support for Flask
    from asgiref.wsgi import WsgiToAsgi
    from hypercorn.asyncio import serve
    from hypercorn.config import Config as HyperConfig

    try:
        # Use hypercorn for async support
        asgi_app = WsgiToAsgi(app)
        hyper_config = HyperConfig()
        hyper_config.bind = [f"0.0.0.0:{port}"]

        asyncio.run(serve(asgi_app, hyper_config))
    except ImportError:
        # Fallback to regular Flask if hypercorn not available
        logger.warning(
            "hypercorn not installed. Using Flask development server. "
            "For production, install: pip install hypercorn asgiref"
        )
        app.run(host='0.0.0.0', port=port, debug=False)
