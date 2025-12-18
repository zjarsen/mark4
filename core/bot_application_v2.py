"""
Bot application with ServiceContainer integration.

This is the refactored version using centralized dependency injection.
Maintains backward compatibility with existing handlers.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    TypeHandler,
    filters
)
import logging

from core.service_container import ServiceContainer
from core.constants import (
    MENU_OPTION_IMAGE,
    MENU_OPTION_VIDEO,
    MENU_OPTION_CHECK_QUEUE,
    MENU_OPTION_BALANCE_HISTORY,
    MENU_OPTION_TOPUP
)

# Import all handler modules
from handlers import command_handlers, menu_handlers, media_handlers, callback_handlers

logger = logging.getLogger('mark4_bot')


class BotApplication:
    """
    Main bot application with ServiceContainer integration.

    Key improvements over original:
    - Centralized dependency injection via ServiceContainer
    - Cleaner initialization order
    - Better resource management (automatic cleanup)
    - Easier testing (swap implementations via container)
    """

    def __init__(self, config, use_redis: bool = True):
        """
        Initialize bot application.

        Args:
            config: Configuration object
            use_redis: Whether to use Redis for state (default: True)
                      Set to False for testing with in-memory state
        """
        self.config = config

        # Initialize service container (handles all dependency injection)
        logger.info("Initializing ServiceContainer...")
        self.container = ServiceContainer(config, use_redis=use_redis)
        logger.info("ServiceContainer initialized successfully")

        # Create Telegram application with post_init callback
        self.app = Application.builder().token(config.BOT_TOKEN).post_init(self._post_init).build()

        # Inject dependencies into handlers
        self._inject_dependencies()

        # Register all handlers
        self._register_handlers()

        logger.info("Bot application initialized successfully")

    def _inject_dependencies(self):
        """
        Inject service instances into handler modules.

        Note: Handlers still expect old service interfaces for now.
        We provide backward-compatible wrappers where needed.
        """
        # For backward compatibility, we need to provide services with the old interface
        # Most handlers expect: state_manager, credit_service, file_service, etc.

        # Inject into command_handlers
        command_handlers.state_manager = self.container.state
        command_handlers.config = self.config
        command_handlers.credit_service = self.container.credits

        # Inject into menu_handlers
        menu_handlers.state_manager = self.container.state
        menu_handlers.notification_service = self.container.notifications
        # menu_handlers expects queue_service, but we have separate managers
        # For now, keep the old queue_service (it's in legacy)
        from services.queue_service import QueueService
        from services.comfyui_service import ComfyUIService
        legacy_comfyui = ComfyUIService(self.config, 'image_undress')
        menu_handlers.queue_service = QueueService(
            self.config,
            legacy_comfyui,
            self.container.notifications
        )
        menu_handlers.config = self.config
        menu_handlers.credit_service = self.container.credits

        # Inject into media_handlers
        media_handlers.state_manager = self.container.state
        media_handlers.file_service = self.container.files
        # media_handlers expects workflow_service
        # For now, we'll need to create a compatibility wrapper
        # But let's use the old WorkflowService temporarily
        from services.workflow_service import WorkflowService
        from services.comfyui_service import ComfyUIService
        legacy_comfyui = ComfyUIService(self.config, 'image_undress')
        legacy_queue = QueueService(
            self.config,
            legacy_comfyui,
            self.container.notifications
        )
        media_handlers.workflow_service = WorkflowService(
            self.config,
            legacy_comfyui,
            self.container.files,
            self.container.notifications,
            legacy_queue,
            self.container.state,
            credit_service=self.container.credits
        )
        media_handlers.config = self.config

        # Inject into callback_handlers
        callback_handlers.state_manager = self.container.state
        callback_handlers.queue_service = legacy_queue

        # Inject into credit_handlers
        from handlers import credit_handlers
        credit_handlers.credit_service = self.container.credits
        credit_handlers.payment_service = self.container.payment_service
        credit_handlers.timeout_service = self.container.payment_timeout
        credit_handlers.discount_service = self.container.discounts

        # Store services in bot_data for access from handlers
        self.app.bot_data['workflow_service'] = media_handlers.workflow_service
        self.app.bot_data['state_manager'] = self.container.state
        self.app.bot_data['container'] = self.container

        logger.debug("Dependencies injected into handlers")

    async def _cleanup_timeout_messages_middleware(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Middleware to cleanup timeout messages and handle abandoned confirmations.

        This runs before every handler to:
        1. Track user interaction for daily discount system
        2. Delete any pending timeout messages when user interacts
        3. Cancel credit confirmations if user sends other input
        """
        if not update.effective_user:
            return

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id if update.effective_chat else None

        # Track user interaction for daily discount system
        try:
            await self.container.discounts.track_user_interaction(user_id)
        except Exception as e:
            logger.debug(f"Error tracking interaction for user {user_id}: {e}")

        # Check if user has pending timeout messages
        if chat_id and self.container.payment_timeout.has_timeout_messages(user_id):
            try:
                await self.container.payment_timeout.cleanup_timeout_messages(user_id, chat_id)
            except Exception as e:
                logger.warning(f"Error cleaning up timeout messages for user {user_id}: {e}")

        # Check for abandoned credit confirmations
        if not update.callback_query:
            if await self.container.state.is_state(user_id, 'waiting_for_credit_confirmation'):
                try:
                    # Delete confirmation message if exists
                    if await self.container.state.has_confirmation_message(user_id):
                        conf_msg = await self.container.state.get_confirmation_message(user_id)
                        if conf_msg:
                            try:
                                # Reconstruct message for deletion
                                chat_id = conf_msg['chat_id']
                                message_id = conf_msg['message_id']
                                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                            except Exception as e:
                                logger.debug(f"Could not delete confirmation message: {e}")
                        await self.container.state.remove_confirmation_message(user_id)

                    # Delete uploaded file
                    state = await self.container.state.get_state(user_id)
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
                    await self.container.state.reset_state(user_id)

                    logger.info(f"Auto-cancelled abandoned confirmation for user {user_id}")

                except Exception as e:
                    logger.error(f"Error handling abandoned confirmation: {e}")

    def _register_handlers(self):
        """Register all handlers in correct priority order."""
        # Cleanup middleware (runs before all handlers)
        self.app.add_handler(
            TypeHandler(Update, self._cleanup_timeout_messages_middleware),
            group=-1
        )

        # Command handlers (highest priority)
        self.app.add_handler(CommandHandler("start", command_handlers.start))
        self.app.add_handler(CommandHandler("help", command_handlers.help_command))
        self.app.add_handler(CommandHandler("cancel", command_handlers.cancel_command))
        self.app.add_handler(CommandHandler("status", command_handlers.status_command))

        # Admin top-up handler
        class AdminPasswordFilter(filters.MessageFilter):
            def __init__(self, config):
                self.config = config
                super().__init__()

            def filter(self, message):
                if not message.text:
                    return False
                if not self.config.ADMIN_TOPUP_PASSWORD:
                    return False
                is_match = message.text.strip() == self.config.ADMIN_TOPUP_PASSWORD
                if is_match:
                    logger.info(f"[ADMIN_FILTER] Admin password matched for user {message.from_user.id}")
                return is_match

        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & AdminPasswordFilter(self.config),
                command_handlers.admin_topup_handler
            ),
            group=0
        )

        # Media upload handlers
        self.app.add_handler(MessageHandler(filters.PHOTO, media_handlers.handle_photo))
        self.app.add_handler(MessageHandler(filters.Document.ALL, media_handlers.handle_document))

        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(callback_handlers.cancel_callback, pattern="^cancel_"))
        self.app.add_handler(CallbackQueryHandler(callback_handlers.payment_callback, pattern="^payment_"))
        self.app.add_handler(CallbackQueryHandler(callback_handlers.video_style_callback, pattern="^video_style_|^back_to_menu"))
        self.app.add_handler(CallbackQueryHandler(callback_handlers.image_style_callback, pattern="^image_style_|^back_to_menu"))
        self.app.add_handler(CallbackQueryHandler(callback_handlers.credit_confirmation_callback, pattern="^confirm_credits_|^cancel_credits"))

        # Credit system callback handlers
        from handlers.credit_handlers import handle_topup_callback, handle_lucky_discount_callback
        self.app.add_handler(CallbackQueryHandler(handle_topup_callback, pattern="^topup_"))
        self.app.add_handler(CallbackQueryHandler(handle_lucky_discount_callback, pattern="^lucky_discount$"))

        # Open topup menu callback handler
        from handlers.callback_handlers import open_topup_menu_callback
        self.app.add_handler(CallbackQueryHandler(open_topup_menu_callback, pattern="^open_topup_menu$"))

        # Queue refresh callback handler
        async def refresh_queue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle refresh_queue callback to update position in same message."""
            query = update.callback_query
            user_id = update.effective_user.id if update.effective_user else None

            if not user_id:
                return

            job_id = query.data.replace("refresh_queue_", "")
            logger.info(f"[CALLBACK] refresh_queue button clicked by user {user_id} for job {job_id}")

            try:
                await query.answer()

                workflow_service = context.bot_data.get('workflow_service')
                if not workflow_service:
                    await query.edit_message_text("❌ 无法获取队列状态")
                    return

                # Check queue managers for job position
                position = None
                found_in_queue = False

                # Check image queue
                image_position = workflow_service.image_queue_manager._get_job_position(job_id)
                if image_position is not None:
                    position = image_position
                    found_in_queue = True

                # Check video queue if not found
                if not found_in_queue:
                    video_position = workflow_service.video_queue_manager._get_job_position(job_id)
                    if video_position is not None:
                        position = video_position
                        found_in_queue = True

                # Update message
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                from telegram.error import BadRequest

                try:
                    if found_in_queue and position is not None:
                        message_text = f"📋 您的任务已加入队列\n位置: #{position}"
                        keyboard = [[InlineKeyboardButton("🔄 刷新", callback_data=f"refresh_queue_{job_id}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(message_text, reply_markup=reply_markup)
                    else:
                        message_text = "🚀 您的任务现在正在服务器上处理！\n⏱️ 这可能需要几分钟..."
                        await query.edit_message_text(message_text)

                    logger.info(f"Refreshed queue position for user {user_id}, job {job_id}: position={position}")

                except BadRequest as e:
                    if "message is not modified" in str(e).lower():
                        logger.debug(f"Queue position unchanged for user {user_id}, job {job_id}")
                    else:
                        raise

            except Exception as e:
                logger.error(f"Error refreshing queue: {e}", exc_info=True)
                try:
                    await query.answer("刷新失败", show_alert=True)
                except:
                    pass

        self.app.add_handler(CallbackQueryHandler(refresh_queue_callback, pattern="^refresh_queue_"))

        # Text message handler
        async def logged_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Wrapper to log when text handler is called."""
            user_id = update.effective_user.id if update.effective_user else "unknown"
            text = update.message.text if update.message else "no text"
            logger.info(f"[TEXT_HANDLER] Called for user {user_id}, text: '{text}'")
            await menu_handlers.handle_menu_selection(update, context)

        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, logged_menu_handler))

        logger.info("All handlers registered")

    async def _post_init(self, application):
        """Called after application initialization to start background tasks."""
        workflow_service = application.bot_data.get('workflow_service')
        if workflow_service:
            if hasattr(workflow_service, 'start_queue_managers'):
                await workflow_service.start_queue_managers()
                logger.info("Queue managers started via post_init")
            else:
                logger.warning("workflow_service does not have start_queue_managers method")

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
        print(f"🔧 State: {'Redis' if isinstance(self.container.state, type(self.container.state)) else 'InMemory'}")
        print("=" * 60)
        print("✅ Bot is running... Press Ctrl+C to stop")
        print("=" * 60)

        try:
            # Run bot with polling
            self.app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            print("\n👋 Bot stopped gracefully")

        except Exception as e:
            logger.error(f"Error running bot: {e}", exc_info=True)
            print(f"\n❌ Bot stopped due to error: {e}")
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")

        # Close service container (closes all resources)
        await self.container.close()

        logger.info("Bot stopped successfully")
