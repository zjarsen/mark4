"""Bot application initialization and handler registration."""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import logging

# Import all handler modules
from handlers import command_handlers, menu_handlers, media_handlers, callback_handlers

# Import services
from services.comfyui_service import ComfyUIService
from services.file_service import FileService
from services.notification_service import NotificationService
from services.queue_service import QueueService
from services.workflow_service import WorkflowService
from services.database_service import DatabaseService
from services.credit_service import CreditService
from services.payment_service import PaymentService

# Import payment provider
from payments.wechat_alipay_provider import WeChatAlipayProvider

# Import core
from core.state_manager import StateManager
from core.constants import (
    MENU_OPTION_IMAGE,
    MENU_OPTION_VIDEO,
    MENU_OPTION_CHECK_QUEUE,
    MENU_OPTION_BALANCE_HISTORY,
    MENU_OPTION_TOPUP
)

logger = logging.getLogger('mark4_bot')


class BotApplication:
    """Main bot application with dependency injection and handler registration."""

    def __init__(self, config):
        """
        Initialize bot application.

        Args:
            config: Configuration object
        """
        self.config = config

        # Initialize state manager
        self.state_manager = StateManager()

        # Initialize services
        self._initialize_services()

        # Create Telegram application
        self.app = Application.builder().token(config.BOT_TOKEN).build()

        # Inject dependencies into handlers
        self._inject_dependencies()

        # Register all handlers
        self._register_handlers()

        logger.info("Bot application initialized successfully")

    def _initialize_services(self):
        """Initialize all service instances."""
        # Core services
        # Note: ComfyUIService now requires workflow_type parameter
        # This default instance is used by QueueService for backwards compatibility
        self.comfyui_service = ComfyUIService(self.config, 'image_undress')
        self.file_service = FileService(self.config)
        self.notification_service = NotificationService(self.config)

        # Database and credit services
        self.database_service = DatabaseService(self.config)
        self.credit_service = CreditService(self.config, self.database_service)

        # Payment services
        self.payment_provider = WeChatAlipayProvider(self.config)
        self.payment_service = PaymentService(
            self.config,
            self.database_service,
            self.credit_service,
            self.payment_provider
        )

        # Initialize bot instance (needed for timeout service)
        from telegram import Bot
        self.bot = Bot(token=self.config.BOT_TOKEN)

        # Payment timeout service
        from services.payment_timeout_service import PaymentTimeoutService
        self.timeout_service = PaymentTimeoutService(self.bot)

        # Queue service (depends on comfyui and notification services)
        self.queue_service = QueueService(
            self.config,
            self.comfyui_service,
            self.notification_service
        )

        # Workflow service (depends on multiple services, including credit_service)
        self.workflow_service = WorkflowService(
            self.config,
            self.comfyui_service,
            self.file_service,
            self.notification_service,
            self.queue_service,
            self.state_manager,
            credit_service=self.credit_service
        )

        logger.debug("All services initialized")

    def _inject_dependencies(self):
        """Inject service instances into handler modules."""
        # Inject into command_handlers
        command_handlers.state_manager = self.state_manager
        command_handlers.config = self.config
        command_handlers.credit_service = self.credit_service

        # Inject into menu_handlers
        menu_handlers.state_manager = self.state_manager
        menu_handlers.notification_service = self.notification_service
        menu_handlers.queue_service = self.queue_service
        menu_handlers.config = self.config

        # Inject into media_handlers
        media_handlers.state_manager = self.state_manager
        media_handlers.file_service = self.file_service
        media_handlers.workflow_service = self.workflow_service
        media_handlers.config = self.config

        # Inject into callback_handlers
        callback_handlers.state_manager = self.state_manager
        callback_handlers.queue_service = self.queue_service

        # Inject into credit_handlers
        from handlers import credit_handlers
        credit_handlers.credit_service = self.credit_service
        credit_handlers.payment_service = self.payment_service
        credit_handlers.timeout_service = self.timeout_service

        # Store workflow_service in bot_data for access from handlers
        self.app.bot_data['workflow_service'] = self.workflow_service
        self.app.bot_data['state_manager'] = self.state_manager

        logger.debug("Dependencies injected into handlers")

    async def _cleanup_timeout_messages_middleware(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Middleware to cleanup timeout messages and handle abandoned confirmations.

        This runs before every handler to:
        1. Delete any pending timeout messages when user interacts
        2. Cancel credit confirmations if user sends other input

        Abandoned confirmation detection:
        - If user is in 'waiting_for_credit_confirmation' state
        - AND user sends ANY input (text, command, photo, etc.)
        - EXCEPT callback queries (button clicks)
        - Then auto-cancel the confirmation
        """
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id if update.effective_chat else None

        # Check if user has pending timeout messages
        if chat_id and self.timeout_service.has_timeout_messages(user_id):
            try:
                await self.timeout_service.cleanup_timeout_messages(user_id, chat_id)
            except Exception as e:
                logger.warning(f"Error cleaning up timeout messages for user {user_id}: {str(e)}")

        # Check for abandoned credit confirmations
        # Don't trigger on callback queries (button clicks)
        if not update.callback_query:
            if self.state_manager.is_state(user_id, 'waiting_for_credit_confirmation'):
                try:
                    # Delete confirmation message if exists
                    if self.state_manager.has_confirmation_message(user_id):
                        conf_msg = self.state_manager.get_confirmation_message(user_id)
                        try:
                            await conf_msg.delete()
                        except Exception as e:
                            logger.debug(f"Could not delete confirmation message: {e}")
                        self.state_manager.remove_confirmation_message(user_id)

                    # Delete uploaded file
                    state = self.state_manager.get_state(user_id)
                    uploaded_file = state.get('uploaded_file_path')
                    if uploaded_file:
                        try:
                            import os
                            if os.path.exists(uploaded_file):
                                os.remove(uploaded_file)
                                logger.debug(f"Deleted abandoned upload: {uploaded_file}")
                        except Exception as e:
                            logger.error(f"Error deleting uploaded file: {e}")

                    # Reset state
                    self.state_manager.reset_state(user_id)

                    logger.info(f"Auto-cancelled abandoned confirmation for user {user_id}")

                except Exception as e:
                    logger.error(f"Error handling abandoned confirmation: {str(e)}")

    def _register_handlers(self):
        """Register all handlers in correct priority order."""
        # Cleanup middleware (runs before all handlers)
        from telegram.ext import TypeHandler
        self.app.add_handler(
            TypeHandler(Update, self._cleanup_timeout_messages_middleware),
            group=-1
        )

        # Command handlers (highest priority)
        self.app.add_handler(CommandHandler("start", command_handlers.start))
        self.app.add_handler(CommandHandler("help", command_handlers.help_command))
        self.app.add_handler(CommandHandler("cancel", command_handlers.cancel_command))
        self.app.add_handler(CommandHandler("status", command_handlers.status_command))

        # Admin top-up handler (high priority, only matches exact password)
        # Custom filter that only matches the admin password
        class AdminPasswordFilter(filters.MessageFilter):
            def __init__(self, config):
                self.config = config
                super().__init__()

            def filter(self, message):
                if not message.text:
                    return False
                if not self.config.ADMIN_TOPUP_PASSWORD:
                    return False
                return message.text.strip() == self.config.ADMIN_TOPUP_PASSWORD

        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & AdminPasswordFilter(self.config),
                command_handlers.admin_topup_handler
            ),
            group=0
        )

        # Menu selection handlers
        # Use regex to match menu options (including variations)
        menu_pattern = r"^(1\. 图片脱衣|2\. 图片转视频脱衣|3\. 查看队列|4\. 📊 积分余额 & 充值记录|5\. 💳 充值积分|.*图片转视频.*)"
        self.app.add_handler(
            MessageHandler(
                filters.Regex(menu_pattern),
                menu_handlers.handle_menu_selection
            )
        )

        # Media upload handlers
        self.app.add_handler(
            MessageHandler(filters.PHOTO, media_handlers.handle_photo)
        )
        self.app.add_handler(
            MessageHandler(filters.Document.ALL, media_handlers.handle_document)
        )

        # Callback query handlers (inline buttons)
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.refresh_queue_callback,
                pattern="^refresh_"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.cancel_callback,
                pattern="^cancel_"
            )
        )
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.payment_callback,
                pattern="^payment_"
            )
        )

        # Video style selection callback handler
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.video_style_callback,
                pattern="^video_style_|^back_to_menu"
            )
        )

        # Image style selection callback handler
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.image_style_callback,
                pattern="^image_style_|^back_to_menu"
            )
        )

        # Credit confirmation callback handler
        self.app.add_handler(
            CallbackQueryHandler(
                callback_handlers.credit_confirmation_callback,
                pattern="^confirm_credits_|^cancel_credits"
            )
        )

        # Credit system callback handlers
        from handlers.credit_handlers import handle_topup_callback
        self.app.add_handler(
            CallbackQueryHandler(
                handle_topup_callback,
                pattern="^topup_"
            )
        )

        # Text message fallback (lowest priority)
        # This catches any text that wasn't handled by other handlers
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                menu_handlers.handle_unexpected_text
            )
        )

        logger.info("All handlers registered")

    def run(self):
        """Start the bot with polling."""
        logger.info(f"Starting bot: {self.config.BOT_USERNAME}")
        logger.info(f"ComfyUI servers: Image={self.config.COMFYUI_IMAGE_UNDRESS_SERVER}, Video={self.config.COMFYUI_VIDEO_DOUXIONG_SERVER}")

        print("=" * 60)
        print(f"🤖 Bot starting: @{self.config.BOT_USERNAME}")
        print(f"🎨 ComfyUI Image: {self.config.COMFYUI_IMAGE_UNDRESS_SERVER}")
        print(f"🎨 ComfyUI Video: {self.config.COMFYUI_VIDEO_DOUXIONG_SERVER}")
        print(f"📁 Uploads directory: {self.config.USER_UPLOADS_DIR}")
        print(f"📁 Retrieve directory: {self.config.COMFYUI_RETRIEVE_DIR}")
        print(f"⏱️  Cleanup timeout: {self.config.CLEANUP_TIMEOUT}s")
        print("=" * 60)
        print("✅ Bot is running... Press Ctrl+C to stop")
        print("=" * 60)

        try:
            # Run bot with polling
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Ignore updates received while bot was offline
            )

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print("\n👋 Bot stopped gracefully")

        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            print(f"\n❌ Bot stopped due to error: {str(e)}")
            raise

    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")

        # Cancel all cleanup tasks
        for user_id in self.state_manager.get_all_processing_users():
            self.state_manager.cancel_cleanup_task(user_id)

        logger.info("Bot stopped successfully")
