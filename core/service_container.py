"""
Service container for dependency injection.

This centralizes all service initialization and wiring, making it easier to:
- Manage dependencies
- Swap implementations (e.g., Redis vs In-Memory state)
- Test with mock services
- Understand service relationships
"""

import logging
from pathlib import Path
from telegram import Bot

# Database layer
from database import DatabaseConnection
from database.repositories import UserRepository, TransactionRepository, PaymentRepository
from database.migrations import MigrationManager

# Domain services
from domain.credits import CreditService, DiscountService
from domain.workflows.image import ImageWorkflowService
from domain.workflows.video import VideoWorkflowService

# Infrastructure
from infrastructure.state import StateManager, RedisStateManager, InMemoryStateManager
from infrastructure.comfyui import ComfyUIClient
from infrastructure.notifications import NotificationService
from infrastructure.files import FileService

# Legacy services (to be phased out)
from services.payment_service import PaymentService
from services.payment_timeout_service import PaymentTimeoutService
from payments.wechat_alipay_provider import WeChatAlipayProvider

logger = logging.getLogger('mark4_bot')


class ServiceContainer:
    """
    Container for all services with dependency injection.

    This manages the initialization order and wiring of:
    - Database layer (connection, repositories, migrations)
    - Domain services (credits, workflows)
    - Infrastructure (state, ComfyUI, notifications, files)
    - Legacy services (payment, timeouts)

    Usage:
        config = Config()
        container = ServiceContainer(config)

        # Access services
        credit_service = container.credits
        image_workflow = container.image_workflow
        state_manager = container.state
    """

    def __init__(self, config, use_redis: bool = True):
        """
        Initialize service container.

        Args:
            config: Configuration object
            use_redis: Whether to use Redis for state (default: True)
                      Set to False for testing with in-memory state
        """
        self.config = config
        self.use_redis = use_redis

        logger.info("=" * 60)
        logger.info("ServiceContainer Initialization Starting")
        logger.info("=" * 60)

        # Initialize in dependency order
        self._init_database()
        self._init_infrastructure(use_redis)
        self._init_domain()
        self._init_legacy()

        logger.info("=" * 60)
        logger.info("ServiceContainer Initialization Complete")
        logger.info("=" * 60)

    # Database Layer

    def _init_database(self):
        """Initialize database connection, repositories, and migrations."""
        logger.info("Initializing database layer...")

        # Connection pool
        self.db_connection = DatabaseConnection(self.config.DATABASE_PATH)
        logger.info(f"✓ Database connection: {self.config.DATABASE_PATH}")

        # Repositories
        self.user_repo = UserRepository(self.db_connection)
        self.transaction_repo = TransactionRepository(self.db_connection)
        self.payment_repo = PaymentRepository(self.db_connection)
        logger.info("✓ Repositories: User, Transaction, Payment")

        # Initialize migration tracking (migrations applied manually if needed)
        self.migration_manager = MigrationManager(self.config.DATABASE_PATH)
        current_version = self.migration_manager.get_current_version()
        logger.info(f"✓ Migration manager ready (current version: {current_version})")

    # Infrastructure Layer

    def _init_infrastructure(self, use_redis: bool):
        """Initialize infrastructure services."""
        logger.info("Initializing infrastructure layer...")

        # State management
        if use_redis:
            redis_url = getattr(self.config, 'REDIS_URL', 'redis://localhost:6379')
            self.state = RedisStateManager(redis_url=redis_url)
            logger.info(f"✓ State: RedisStateManager ({redis_url})")
        else:
            self.state = InMemoryStateManager()
            logger.info("✓ State: InMemoryStateManager")

        # ComfyUI clients (one per server)
        self.comfyui_clients = {
            'image_undress': ComfyUIClient(
                self.config.COMFYUI_IMAGE_UNDRESS_SERVER,
                disable_ssl_verify=True
            ),
            'video_douxiong': ComfyUIClient(
                self.config.COMFYUI_VIDEO_DOUXIONG_SERVER,
                disable_ssl_verify=True
            ),
            'video_liujing': ComfyUIClient(
                self.config.COMFYUI_VIDEO_LIUJING_SERVER,
                disable_ssl_verify=True
            ),
            'video_shejing': ComfyUIClient(
                self.config.COMFYUI_VIDEO_SHEJING_SERVER,
                disable_ssl_verify=True
            )
        }
        logger.info(f"✓ ComfyUI clients: {len(self.comfyui_clients)} servers")

        # Notification service
        self.notifications = NotificationService()
        logger.info("✓ Notifications: Telegram message service")

        # File service
        self.files = FileService(
            uploads_dir=self.config.USER_UPLOADS_DIR,
            retrieve_dir=self.config.COMFYUI_RETRIEVE_DIR,
            allowed_formats=self.config.ALLOWED_IMAGE_FORMATS
        )
        logger.info("✓ Files: Upload/download service")

    # Domain Layer

    def _init_domain(self):
        """Initialize domain services."""
        logger.info("Initializing domain layer...")

        # Credit service (with feature pricing)
        feature_pricing = {
            'image_undress': 10.0,
            'pink_bra': 0.0,  # Free
            'video_style_a': 30.0,
            'video_style_b': 30.0,
            'video_style_c': 30.0
        }
        self.credits = CreditService(
            connection_manager=self.db_connection,
            feature_pricing=feature_pricing
        )
        logger.info("✓ Credits: CreditService with transaction safety")

        # Discount service
        self.discounts = DiscountService(
            user_repository=self.user_repo
        )
        logger.info("✓ Discounts: Random daily draw system")

        # Workflow services
        # Note: We need to wire queue managers here, but they're in legacy services
        # For now, we'll defer workflow service initialization until legacy is ready
        logger.info("✓ Workflows: Deferred until queue managers ready")

    # Legacy Services (to be refactored later)

    def _init_legacy(self):
        """Initialize legacy services that haven't been refactored yet."""
        logger.info("Initializing legacy services...")

        # Bot instance (needed for various services)
        self.bot = Bot(token=self.config.BOT_TOKEN)
        logger.info("✓ Bot: Telegram Bot instance")

        # Payment provider
        self.payment_provider = WeChatAlipayProvider(self.config)
        logger.info("✓ Payment provider: WeChatAlipay")

        # Payment service with compatibility wrapper
        class PaymentRepoWrapper:
            """Wrapper to make PaymentRepository compatible with old payment_service interface."""
            def __init__(self, payment_repo):
                self._repo = payment_repo

            def create_payment_record(self, **kwargs):
                return self._repo.create(**kwargs)

            def get_payment(self, payment_id: str):
                return self._repo.get_by_id(payment_id)

            def update_payment_status(self, payment_id: str, status: str):
                return self._repo.update_status(payment_id, status)

        self.payment_service = PaymentService(
            self.config,
            PaymentRepoWrapper(self.payment_repo),  # Use new payment repo with wrapper
            self.credits,  # Use new CreditService
            self.payment_provider
        )
        logger.info("✓ Payment service: Payment orchestration")

        # Payment timeout service
        self.payment_timeout = PaymentTimeoutService(self.bot)
        logger.info("✓ Payment timeout: Timeout tracking")

        # Queue managers (still using old ComfyUIService)
        from services.comfyui_service import ComfyUIService
        from services.image_queue_manager import ImageQueueManager
        from services.video_queue_manager import VideoQueueManager

        # Create legacy ComfyUI services for queue managers
        legacy_comfyui_image = ComfyUIService(self.config, 'image_undress')
        legacy_comfyui_douxiong = ComfyUIService(self.config, 'video_douxiong')
        legacy_comfyui_liujing = ComfyUIService(self.config, 'video_liujing')
        legacy_comfyui_shejing = ComfyUIService(self.config, 'video_shejing')

        self.image_queue = ImageQueueManager(legacy_comfyui_image)
        self.video_queues = {
            'style_a': VideoQueueManager(legacy_comfyui_douxiong),
            'style_b': VideoQueueManager(legacy_comfyui_liujing),
            'style_c': VideoQueueManager(legacy_comfyui_shejing)
        }
        logger.info("✓ Queue managers: Image + 3 video styles")

        # Now we can create workflow services
        # Image workflow service
        # Note: ImageWorkflowService needs processor, which we'll create inline
        from domain.workflows.image.processors import ImageUndressProcessor, PinkBraProcessor

        image_processors = {
            'undress': ImageUndressProcessor(
                comfyui_client=self.comfyui_clients['image_undress'],
                workflow_path=self.config.WORKFLOWS_DIR / 'i2i_undress_final_v5.json',
                cost=10
            ),
            'pink_bra': PinkBraProcessor(
                comfyui_client=self.comfyui_clients['image_undress'],
                workflow_path=self.config.WORKFLOWS_DIR / 'i2i_bra_v5.json',
                cost=0
            )
        }

        self.image_workflow = ImageWorkflowService(
            credit_service=self.credits,
            state_manager=self.state,
            notification_service=self.notifications,
            file_service=self.files,
            queue_manager=self.image_queue,
            processors=image_processors
        )
        logger.info("✓ Image workflow: Undress + Pink Bra")

        # Video workflow service
        # Note: VideoWorkflowService needs processors for each style
        from domain.workflows.video.processors import (
            VideoStyleAProcessor,
            VideoStyleBProcessor,
            VideoStyleCProcessor
        )

        video_processors = {
            'style_a': VideoStyleAProcessor(
                comfyui_client=self.comfyui_clients['video_douxiong'],
                workflow_path=self.config.WORKFLOWS_DIR / 'i2v_undress_douxiong.json',
                cost=30
            ),
            'style_b': VideoStyleBProcessor(
                comfyui_client=self.comfyui_clients['video_liujing'],
                workflow_path=self.config.WORKFLOWS_DIR / 'i2v_undress_liujing.json',
                cost=30
            ),
            'style_c': VideoStyleCProcessor(
                comfyui_client=self.comfyui_clients['video_shejing'],
                workflow_path=self.config.WORKFLOWS_DIR / 'i2v_undress_shejing.json',
                cost=30
            )
        }

        self.video_workflow = VideoWorkflowService(
            credit_service=self.credits,
            state_manager=self.state,
            notification_service=self.notifications,
            file_service=self.files,
            queue_manager=self.video_queues,  # Dict of queue managers
            video_processors=video_processors
        )
        logger.info("✓ Video workflow: 3 styles (A, B, C)")

    # Cleanup

    async def close(self):
        """Close all resources (connections, sessions, etc.)."""
        logger.info("Closing ServiceContainer resources...")

        # Close ComfyUI clients
        for name, client in self.comfyui_clients.items():
            try:
                await client.close()
                logger.debug(f"Closed ComfyUI client: {name}")
            except Exception as e:
                logger.error(f"Error closing ComfyUI client {name}: {e}")

        # Close state manager (if Redis)
        if isinstance(self.state, RedisStateManager):
            try:
                await self.state.close()
                logger.debug("Closed Redis state manager")
            except Exception as e:
                logger.error(f"Error closing state manager: {e}")

        # Close database connection
        try:
            self.db_connection.close()
            logger.debug("Closed database connection")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        logger.info("ServiceContainer resources closed")

    def __repr__(self) -> str:
        """String representation."""
        state_type = "Redis" if isinstance(self.state, RedisStateManager) else "InMemory"
        return f"ServiceContainer(state={state_type}, comfyui_clients={len(self.comfyui_clients)})"
