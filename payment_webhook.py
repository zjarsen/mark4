"""
Payment webhook server for handling payment callbacks.

This server receives payment notifications from the payment provider
and processes them to credit user accounts.

Run with: python payment_webhook.py
"""

from flask import Flask, request, jsonify
import asyncio
import logging
import stripe
from telegram import Bot
from config import Config
from services.database_service import DatabaseService
from services.credit_service import CreditService
from services.payment_service import PaymentService
from payments.wechat_alipay_provider import WeChatAlipayProvider
from payments.stripe_provider import StripeProvider

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

# Initialize Telegram Bot for sending notifications
bot = Bot(token=config.BOT_TOKEN)

# Initialize payment timeout service
from services.payment_timeout_service import PaymentTimeoutService
timeout_service = PaymentTimeoutService(bot)

# Initialize Stripe provider
stripe_provider = StripeProvider(config)


async def send_payment_notification(user_id: int, payment_id: str, credits: float, new_balance: float, chat_id: int = None, message_id: int = None, language_code: str = 'zh_CN'):
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
        language_code: User's language preference for translation
    """
    try:
        # Import translation service
        from services.translation_service import TranslationService

        translation_service = TranslationService(
            database_service=database_service,
            locales_dir='locales',
            default_lang='zh_CN'
        )

        # Get translated message
        message = translation_service.get_lang(
            language_code,
            'payment.notification_success',
            credits=int(credits),
            new_balance=int(new_balance),
            payment_id=payment_id
        )

        if chat_id and message_id:
            # Edit the existing "等待支付中" message
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message
            )
            logger.info(f"Edited payment message for user {user_id} (msg: {message_id}, lang: {language_code})")
        else:
            # Send new message if no message_id provided
            await bot.send_message(
                chat_id=user_id,
                text=message
            )
            logger.info(f"Sent payment notification to user {user_id} (lang: {language_code})")
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
                payment = database_service.get_payment(payment_id)
                if payment:
                    user_id = payment['user_id']
                    credits = payment['credits_amount']
                    chat_id = payment.get('chat_id')
                    message_id = payment.get('message_id')
                    language_code = payment.get('language_code', 'zh_CN')

                    # Get user's new balance
                    user_stats = await credit_service.get_user_stats(user_id)
                    new_balance = user_stats['balance']

                    # Send notification (edit message if chat_id/message_id available) with language
                    await send_payment_notification(user_id, payment_id, credits, new_balance, chat_id, message_id, language_code)

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
    Handle user return from payment page with translated HTML.

    This is where users are redirected after completing/cancelling payment.
    Language parameter passed via query string: ?lang=zh_CN or ?lang=en_US
    """
    # Get language from query parameter
    language_code = request.args.get('lang', 'zh_CN')

    # Import translation service
    from services.translation_service import TranslationService

    translation_service = TranslationService(
        database_service=database_service,
        locales_dir='locales',
        default_lang='zh_CN'
    )

    # Get translated strings
    title = translation_service.get_lang(language_code, 'payment.webhook_html_title')
    heading = translation_service.get_lang(language_code, 'payment.webhook_html_heading')
    body = translation_service.get_lang(language_code, 'payment.webhook_html_body')
    return_text = translation_service.get_lang(language_code, 'payment.webhook_html_return')
    footer = translation_service.get_lang(language_code, 'payment.webhook_html_footer')

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; margin-bottom: 20px; }}
            p {{ color: #666; font-size: 16px; line-height: 1.6; }}
            .icon {{ font-size: 60px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">⏳</div>
            <h1>{heading}</h1>
            <p>{body}</p>
            <p>{return_text}</p>
            <p style="margin-top: 30px; color: #999; font-size: 14px;">
                {footer}
            </p>
        </div>
    </body>
    </html>
    """, 200


# ============================================================================
# STRIPE PAYMENT ROUTES
# ============================================================================

@app.route('/stripe/checkout', methods=['GET'])
def stripe_checkout_page():
    """
    Serve the Stripe Embedded Checkout page for Telegram Mini App.

    Query parameters:
    - session_id: Stripe checkout session ID
    """
    session_id = request.args.get('session_id')

    if not session_id:
        return "Missing session_id parameter", 400

    # Get publishable key for client-side Stripe
    publishable_key = config.STRIPE_PUBLISHABLE_KEY

    # Serve the checkout HTML page
    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Checkout</title>
    <script src="https://js.stripe.com/v3/"></script>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 16px;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            min-height: 100vh;
        }}
        #checkout {{
            max-width: 500px;
            margin: 0 auto;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
        }}
        .loading-spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid var(--tg-theme-hint-color, #ccc);
            border-top-color: var(--tg-theme-link-color, #2481cc);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .error {{
            text-align: center;
            padding: 40px;
            color: #dc3545;
        }}
        .success {{
            text-align: center;
            padding: 40px;
        }}
        .success-icon {{
            font-size: 48px;
            margin-bottom: 16px;
        }}
        .message {{
            font-size: 16px;
            margin-bottom: 24px;
        }}
        .close-button {{
            background: var(--tg-theme-button-color, #2481cc);
            color: var(--tg-theme-button-text-color, #ffffff);
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div id="checkout">
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading checkout...</p>
        </div>
    </div>

    <script>
        const sessionId = "{session_id}";
        const publishableKey = "{publishable_key}";

        // Initialize Telegram WebApp
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();

        // Initialize Stripe
        const stripe = Stripe(publishableKey);

        async function initCheckout() {{
            try {{
                // Fetch the client secret for this session
                const response = await fetch(`/stripe/session-secret?session_id=${{sessionId}}`);
                const data = await response.json();

                if (!data.client_secret) {{
                    throw new Error(data.error || 'Failed to get checkout session');
                }}

                // Initialize embedded checkout
                const checkout = await stripe.initEmbeddedCheckout({{
                    clientSecret: data.client_secret,
                }});

                // Clear loading and mount checkout
                document.getElementById('checkout').innerHTML = '';
                checkout.mount('#checkout');

            }} catch (error) {{
                console.error('Checkout error:', error);
                document.getElementById('checkout').innerHTML = `
                    <div class="error">
                        <p>Failed to load checkout: ${{error.message}}</p>
                        <button class="close-button" onclick="tg.close()">Close</button>
                    </div>
                `;
            }}
        }}

        initCheckout();
    </script>
</body>
</html>''', 200


@app.route('/stripe/session-secret', methods=['GET'])
def stripe_session_secret():
    """
    Return the client secret for a Stripe checkout session.

    Query parameters:
    - session_id: Stripe checkout session ID
    """
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400

    try:
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        return jsonify({
            'client_secret': session.client_secret,
            'status': session.status,
        })
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error retrieving session: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/stripe/return', methods=['GET'])
def stripe_return_page():
    """
    Handle return from Stripe Embedded Checkout.

    This page is shown after checkout completes or is cancelled.
    It checks the session status and closes the Mini App.
    """
    session_id = request.args.get('session_id')

    return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Payment Complete</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 40px 16px;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            text-align: center;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 16px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .message {{
            font-size: 16px;
            color: var(--tg-theme-hint-color, #666);
            margin-bottom: 24px;
        }}
        .close-button {{
            background: var(--tg-theme-button-color, #2481cc);
            color: var(--tg-theme-button-text-color, #ffffff);
            border: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div id="status">
        <div class="icon">⏳</div>
        <div class="title">Processing...</div>
        <div class="message">Please wait while we verify your payment.</div>
    </div>

    <script>
        const sessionId = "{session_id}";
        const tg = window.Telegram.WebApp;
        tg.ready();

        async function checkStatus() {{
            try {{
                const response = await fetch(`/stripe/session-status?session_id=${{sessionId}}`);
                const data = await response.json();

                const statusDiv = document.getElementById('status');

                if (data.status === 'complete') {{
                    statusDiv.innerHTML = `
                        <div class="icon">✅</div>
                        <div class="title">Payment Successful!</div>
                        <div class="message">Your credits have been added to your account.</div>
                        <button class="close-button" onclick="tg.close()">Close</button>
                    `;
                }} else if (data.status === 'expired') {{
                    statusDiv.innerHTML = `
                        <div class="icon">⏰</div>
                        <div class="title">Session Expired</div>
                        <div class="message">The checkout session has expired. Please try again.</div>
                        <button class="close-button" onclick="tg.close()">Close</button>
                    `;
                }} else {{
                    statusDiv.innerHTML = `
                        <div class="icon">❌</div>
                        <div class="title">Payment Incomplete</div>
                        <div class="message">The payment was not completed. Please try again.</div>
                        <button class="close-button" onclick="tg.close()">Close</button>
                    `;
                }}
            }} catch (error) {{
                console.error('Status check error:', error);
                document.getElementById('status').innerHTML = `
                    <div class="icon">❓</div>
                    <div class="title">Status Unknown</div>
                    <div class="message">Could not verify payment status. Please check your balance in the bot.</div>
                    <button class="close-button" onclick="tg.close()">Close</button>
                `;
            }}
        }}

        checkStatus();
    </script>
</body>
</html>''', 200


@app.route('/stripe/session-status', methods=['GET'])
def stripe_session_status():
    """
    Check the status of a Stripe checkout session.

    Query parameters:
    - session_id: Stripe checkout session ID
    """
    session_id = request.args.get('session_id')

    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return jsonify({
            'status': session.status,
            'payment_status': session.payment_status,
        })
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error checking session status: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/stripe/webhook', methods=['POST'])
async def stripe_webhook():
    """
    Handle Stripe webhook events.

    Processes checkout.session.completed events to credit user accounts.
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    # Verify webhook signature
    try:
        event = stripe_provider.verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        logger.error(f"Stripe webhook signature verification failed: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Process the event
    try:
        result = await stripe_provider.handle_webhook_event(event)

        if result.get('success') and result.get('user_id') and result.get('credits'):
            user_id = result['user_id']
            credits = result['credits']
            payment_id = result.get('internal_payment_id') or result.get('payment_id')

            # Check if we have a payment record (created when user initiated payment)
            payment = database_service.get_payment(payment_id)

            if payment:
                # Process payment completion through payment service
                success, new_balance, error = await payment_service.process_payment_completion(payment_id)

                if success:
                    # Get language code from payment record
                    language_code = payment.get('language_code', 'zh_CN')
                    chat_id = payment.get('chat_id')
                    message_id = payment.get('message_id')

                    # Send notification
                    await send_payment_notification(
                        user_id, payment_id, credits, new_balance,
                        chat_id, message_id, language_code
                    )
                    logger.info(f"Stripe payment completed: user={user_id}, credits={credits}")
                else:
                    logger.error(f"Failed to process Stripe payment completion: {error}")
            else:
                # No existing payment record - create one and credit directly
                # This handles cases where webhook arrives before/without local record
                logger.warning(f"No local payment record for Stripe session {payment_id}, creating one")

                # Add credits directly
                await credit_service.add_credits(user_id, credits, f"Stripe payment {payment_id}")

                # Get new balance and send notification
                user_stats = await credit_service.get_user_stats(user_id)
                new_balance = user_stats['balance']

                # Send notification directly to user
                await send_payment_notification(user_id, payment_id, credits, new_balance)
                logger.info(f"Stripe payment credited directly: user={user_id}, credits={credits}")

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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
