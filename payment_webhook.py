"""
Payment webhook server for handling payment callbacks.

This server receives payment notifications from the payment provider
and processes them to credit user accounts.

Run with: python payment_webhook.py
"""

from flask import Flask, request, jsonify
import asyncio
import logging
from config import Config
from services.database_service import DatabaseService
from services.credit_service import CreditService
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

# Initialize services
config = Config()
database_service = DatabaseService(config)
credit_service = CreditService(config, database_service)
payment_provider = WeChatAlipayProvider(config)
payment_service = PaymentService(
    config,
    database_service,
    credit_service,
    payment_provider
)


@app.route('/payment/callback', methods=['POST'])
async def payment_callback():
    """
    Handle payment callback from payment provider.

    The payment provider will send a POST request with form data containing:
    - memberid: Merchant ID
    - orderid: Order ID
    - amount: Payment amount
    - transaction_id: Platform transaction ID
    - datetime: Payment completion time
    - returncode: Status code ('00' = success)
    - sign: MD5 signature
    """
    try:
        # Get callback data from form
        callback_data = request.form.to_dict()

        logger.info(f"Received payment callback: {callback_data.get('orderid')}")

        # Process callback with payment service
        success, payment_id = await payment_service.process_payment_callback(callback_data)

        if success:
            logger.info(f"Successfully processed payment callback: {payment_id}")
            # CRITICAL: Must respond with exactly "OK" (uppercase)
            return "OK", 200
        else:
            logger.error(f"Failed to process payment callback: {payment_id}")
            return "FAIL", 400

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
