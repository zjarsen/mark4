"""Workflow orchestration service."""

import asyncio
from pathlib import Path
import logging
from workflows_processing.image_processing import (
    ImageProcessingWorkflow,
    ImageProcessingStyleBra,
    ImageProcessingStyleUndress
)

logger = logging.getLogger('mark4_bot')


class WorkflowService:
    """Service for orchestrating workflow processing."""

    def __init__(
        self,
        config,
        comfyui_service,
        file_service,
        notification_service,
        queue_service,
        state_manager,
        credit_service=None
    ):
        """
        Initialize workflow service.

        Args:
            config: Configuration object
            comfyui_service: Legacy ComfyUI service instance (deprecated, will be removed)
            file_service: File service instance
            notification_service: Notification service instance
            queue_service: Queue service instance
            state_manager: State manager instance
            credit_service: CreditService instance (optional for backwards compatibility)
        """
        self.config = config
        self.file_service = file_service
        self.notification_service = notification_service
        self.queue_service = queue_service
        self.state_manager = state_manager
        self.credit_service = credit_service

        # Create workflow-specific ComfyUI service instances
        from services.comfyui_service import ComfyUIService

        image_comfyui = ComfyUIService(config, 'image_undress')
        image_bra_comfyui = ComfyUIService(config, 'image_bra')
        video_douxiong_comfyui = ComfyUIService(config, 'video_douxiong')
        video_liujing_comfyui = ComfyUIService(config, 'video_liujing')
        video_shejing_comfyui = ComfyUIService(config, 'video_shejing')

        # Initialize workflow implementations with their specific ComfyUI services
        self.image_workflow = ImageProcessingWorkflow(
            config,
            image_comfyui,
            file_service
        )

        # Initialize image workflow implementations (styled)
        self.image_workflows = {
            'bra': ImageProcessingStyleBra(config, image_bra_comfyui, file_service),
            'undress': ImageProcessingStyleUndress(config, image_comfyui, file_service)
        }

        # Initialize video workflow implementations
        from workflows_processing.video_processing import (
            VideoProcessingStyleA,
            VideoProcessingStyleB,
            VideoProcessingStyleC
        )

        self.video_workflows = {
            'style_a': VideoProcessingStyleA(config, video_douxiong_comfyui, file_service),
            'style_b': VideoProcessingStyleB(config, video_liujing_comfyui, file_service),
            'style_c': VideoProcessingStyleC(config, video_shejing_comfyui, file_service)
        }

        # Store ComfyUI services for queue service (uses image_undress by default)
        self.comfyui_service = image_comfyui

    async def start_image_workflow(
        self,
        update,
        context,
        local_path: str,
        user_id: int
    ):
        """
        Upload image and show credit confirmation (NEW FLOW).
        Actual processing starts after user confirms via proceed_with_image_workflow().

        Args:
            update: Telegram Update object
            context: Telegram Context object
            local_path: Path to uploaded image
            user_id: User ID
        """
        try:
            filename = Path(local_path).name

            # Check credits if credit service is available
            if self.credit_service:
                has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                    user_id,
                    'image_processing'
                )

                if not has_sufficient:
                    # Check if user is on cooldown for free trial
                    has_trial = await self.credit_service.has_free_trial(user_id)

                    if not has_trial:
                        # User is on cooldown - show next available time
                        next_available = await self.credit_service.get_next_free_trial_time(user_id)

                        if next_available:
                            from core.constants import FREE_TRIAL_COOLDOWN_MESSAGE
                            next_time_str = next_available.strftime('%Y-%m-%d %H:%M GMT+8')
                            await update.message.reply_text(
                                FREE_TRIAL_COOLDOWN_MESSAGE.format(
                                    next_available=next_time_str,
                                    balance=balance
                                )
                            )
                            logger.info(
                                f"User {user_id} on free trial cooldown until {next_time_str}"
                            )
                            self.state_manager.reset_state(user_id)
                            return

                    # Insufficient credits (no trial available or other reason)
                    from core.constants import (
                        INSUFFICIENT_CREDITS_MESSAGE,
                        TOPUP_PACKAGES_MESSAGE,
                        TOPUP_10_BUTTON,
                        TOPUP_30_BUTTON,
                        TOPUP_50_BUTTON,
                        TOPUP_100_BUTTON
                    )
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                    # Send insufficient credits message
                    await update.message.reply_text(
                        INSUFFICIENT_CREDITS_MESSAGE.format(
                            balance=balance,
                            required=cost
                        )
                    )

                    # Show topup packages inline keyboard
                    keyboard = [
                        [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                        [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                        [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                        [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=TOPUP_PACKAGES_MESSAGE,
                        reply_markup=reply_markup
                    )

                    logger.warning(
                        f"User {user_id} has insufficient credits: "
                        f"balance={balance}, required={cost}"
                    )
                    self.state_manager.reset_state(user_id)
                    return

                # Check if using free trial
                has_free_trial = await self.credit_service.has_free_trial(user_id)

                # Get real balance for display (check_sufficient_credits returns 0.0 for free trial)
                if has_free_trial:
                    balance = await self.credit_service.get_balance(user_id)

                # Calculate cooldown info for free trial users
                cooldown_info = None
                if has_free_trial:
                    next_available = await self.credit_service.get_next_free_trial_time(user_id)
                    if next_available:
                        # Calculate time difference
                        from datetime import datetime
                        import pytz
                        now = datetime.now(pytz.timezone('Asia/Shanghai'))
                        if next_available.tzinfo is None:
                            next_available = pytz.utc.localize(next_available).astimezone(pytz.timezone('Asia/Shanghai'))

                        delta = next_available - now
                        days = delta.days
                        hours = delta.seconds // 3600
                        cooldown_info = f"使用后 {days}天{hours}小时 后可再次免费使用"

            # Upload image to ComfyUI
            await self.image_workflow.upload_image(local_path, filename)

            # Store workflow details in state and show confirmation
            self.state_manager.update_state(
                user_id,
                state='waiting_for_credit_confirmation',
                uploaded_file_path=local_path,
                filename=filename,
                workflow_type='image'
            )

            # Show credit confirmation
            from core.constants import WORKFLOW_NAME_IMAGE
            message = await self.notification_service.send_credit_confirmation(
                context.bot,
                user_id,
                workflow_name=WORKFLOW_NAME_IMAGE,
                workflow_type='image',
                balance=balance,
                cost=cost,
                is_free_trial=has_free_trial,
                cooldown_info=cooldown_info
            )

            # Store confirmation message for cleanup
            self.state_manager.set_confirmation_message(user_id, message)

            logger.info(
                f"Uploaded image and showed confirmation for user {user_id}, "
                f"free_trial={has_free_trial}"
            )

        except Exception as e:
            logger.error(f"Error starting image workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                context.bot,
                user_id,
                "上传失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)

    async def start_image_workflow_with_style(
        self,
        update,
        context,
        local_path: str,
        user_id: int,
        style: str
    ):
        """
        Upload image and show credit confirmation for styled image processing.
        Actual processing starts after user confirms via proceed_with_image_workflow_with_style().

        Args:
            update: Telegram Update object
            context: Telegram Context object
            local_path: Path to uploaded image
            user_id: User ID
            style: Image style ('bra' or 'undress')
        """
        try:
            filename = Path(local_path).name

            # Validate style
            if style not in self.image_workflows:
                await update.message.reply_text("选择的风格无效")
                self.state_manager.reset_state(user_id)
                return

            image_workflow = self.image_workflows[style]

            # Check credits based on style
            # 'undress' supports free trial, 'bra' is paid only
            has_free_trial = False
            cooldown_info = None

            if self.credit_service:
                if style == 'undress':
                    # Check with free trial support
                    has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                        user_id,
                        'image_processing'
                    )

                    if not has_sufficient:
                        # Check if user is on cooldown for free trial
                        has_trial = await self.credit_service.has_free_trial(user_id)

                        if not has_trial:
                            # User is on cooldown - show next available time
                            next_available = await self.credit_service.get_next_free_trial_time(user_id)

                            if next_available:
                                from core.constants import FREE_TRIAL_COOLDOWN_MESSAGE
                                next_time_str = next_available.strftime('%Y-%m-%d %H:%M GMT+8')
                                await update.message.reply_text(
                                    FREE_TRIAL_COOLDOWN_MESSAGE.format(
                                        next_available=next_time_str,
                                        balance=balance
                                    )
                                )
                                logger.info(
                                    f"User {user_id} on free trial cooldown until {next_time_str}"
                                )
                                self.state_manager.reset_state(user_id)
                                return

                        # Insufficient credits (no trial available or other reason)
                        from core.constants import (
                            INSUFFICIENT_CREDITS_MESSAGE,
                            TOPUP_PACKAGES_MESSAGE,
                            TOPUP_10_BUTTON,
                            TOPUP_30_BUTTON,
                            TOPUP_50_BUTTON,
                            TOPUP_100_BUTTON
                        )
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                        # Send insufficient credits message
                        await update.message.reply_text(
                            INSUFFICIENT_CREDITS_MESSAGE.format(
                                balance=balance,
                                required=cost
                            )
                        )

                        # Show topup packages inline keyboard
                        keyboard = [
                            [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                            [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                            [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                            [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await context.bot.send_message(
                            chat_id=user_id,
                            text=TOPUP_PACKAGES_MESSAGE,
                            reply_markup=reply_markup
                        )

                        logger.warning(
                            f"User {user_id} has insufficient credits: "
                            f"balance={balance}, required={cost}"
                        )
                        self.state_manager.reset_state(user_id)
                        return

                    # Check if using free trial
                    has_free_trial = await self.credit_service.has_free_trial(user_id)

                    # Get real balance for display
                    if has_free_trial:
                        balance = await self.credit_service.get_balance(user_id)

                    # Calculate cooldown info for free trial users
                    if has_free_trial:
                        next_available = await self.credit_service.get_next_free_trial_time(user_id)
                        if next_available:
                            from datetime import datetime
                            import pytz
                            now = datetime.now(pytz.timezone('Asia/Shanghai'))
                            if next_available.tzinfo is None:
                                next_available = pytz.utc.localize(next_available).astimezone(pytz.timezone('Asia/Shanghai'))

                            delta = next_available - now
                            days = delta.days
                            hours = delta.seconds // 3600
                            cooldown_info = f"使用后 {days}天{hours}小时 后可再次免费使用"

                else:  # style == 'bra' - permanently free (0 credits, no payment ever)
                    # Get user's balance for display only (not used for checking)
                    balance = await self.credit_service.get_balance(user_id)

                    # Bra style is permanently free - set cost to 0
                    cost = 0

                    # Mark as free trial to skip credit deduction later
                    has_free_trial = True

                    logger.info(
                        f"User {user_id} using bra style (permanently free)"
                    )

            # Upload image to ComfyUI
            await image_workflow.upload_image(local_path, filename)

            # Determine workflow name based on style
            from core.constants import (
                WORKFLOW_NAME_IMAGE_BRA,
                WORKFLOW_NAME_IMAGE_UNDRESS
            )

            workflow_name_map = {
                'bra': WORKFLOW_NAME_IMAGE_BRA,
                'undress': WORKFLOW_NAME_IMAGE_UNDRESS
            }
            workflow_name = workflow_name_map.get(style, "图片脱衣")

            # Store workflow details in state and show confirmation
            self.state_manager.update_state(
                user_id,
                state='waiting_for_credit_confirmation',
                uploaded_file_path=local_path,
                filename=filename,
                workflow_type=f'image_{style}',  # e.g., 'image_bra' or 'image_undress'
                image_style=style
            )

            # Show credit confirmation
            message = await self.notification_service.send_credit_confirmation(
                context.bot,
                user_id,
                workflow_name=workflow_name,
                workflow_type=f'image_{style}',
                balance=balance,
                cost=cost,
                is_free_trial=has_free_trial,
                cooldown_info=cooldown_info
            )

            # Store confirmation message for cleanup
            self.state_manager.set_confirmation_message(user_id, message)

            logger.info(
                f"Uploaded image and showed confirmation for user {user_id}, "
                f"image style: {style}, free_trial={has_free_trial}"
            )

        except Exception as e:
            logger.error(f"Error starting image workflow with style for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                context.bot,
                user_id,
                "上传失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)

    async def _show_queue_position(self, update, user_id: int, prompt_id: str):
        """
        Display initial queue position to user.

        Args:
            update: Telegram Update object
            user_id: User ID
            prompt_id: Prompt ID
        """
        try:
            position, total = await self.queue_service.get_queue_position(prompt_id)

            message = await self.notification_service.send_queue_position(
                update.message.get_bot(),
                user_id,
                position,
                total,
                prompt_id
            )

            # Store message for later updates/deletion
            self.state_manager.set_queue_message(user_id, message)

        except Exception as e:
            logger.error(f"Error showing queue position for user {user_id}: {str(e)}")

    async def _monitor_and_complete(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str
    ):
        """
        Monitor processing and handle completion.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            prompt_id: Prompt ID to monitor
            filename: Original filename
        """
        async def completion_callback(outputs):
            """Called when processing completes."""
            await self.image_workflow.handle_completion(
                bot,
                user_id,
                filename,
                outputs,
                self.state_manager,
                self.notification_service
            )

        # Start monitoring (pass image workflow's ComfyUI service)
        await self.queue_service.monitor_processing(
            bot,
            user_id,
            prompt_id,
            completion_callback,
            comfyui_service=self.image_workflow.comfyui_service
        )

    async def proceed_with_image_workflow(self, bot, user_id: int):
        """
        Proceed with image workflow after user confirms credit deduction.
        Called from credit_confirmation_callback handler.

        Args:
            bot: Telegram Bot instance
            user_id: User ID

        Returns:
            True if successful, False if failed
        """
        try:
            state = self.state_manager.get_state(user_id)
            filename = state.get('filename')
            local_path = state.get('uploaded_file_path')

            if not filename or not local_path:
                logger.error(f"Missing filename or path in state for user {user_id}")
                return False

            # Re-check credits (in case balance changed)
            if self.credit_service:
                has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                    user_id,
                    'image_processing'
                )

                if not has_sufficient:
                    # Check if user has free trial
                    has_trial = await self.credit_service.has_free_trial(user_id)

                    if not has_trial:
                        # Insufficient credits - show error and topup menu
                        from core.constants import (
                            CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE,
                            TOPUP_PACKAGES_MESSAGE,
                            TOPUP_10_BUTTON,
                            TOPUP_30_BUTTON,
                            TOPUP_50_BUTTON,
                            TOPUP_100_BUTTON
                        )
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                        # Send insufficient credits message
                        await bot.send_message(
                            chat_id=user_id,
                            text=CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE.format(
                                balance=int(balance),
                                cost=int(cost)
                            )
                        )

                        # Show topup packages inline keyboard
                        keyboard = [
                            [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                            [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                            [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                            [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await bot.send_message(
                            chat_id=user_id,
                            text=TOPUP_PACKAGES_MESSAGE,
                            reply_markup=reply_markup
                        )

                        self.state_manager.reset_state(user_id)
                        return False

            # Queue workflow
            prompt_id = await self.image_workflow.queue_workflow(filename=filename)

            # Deduct credits after successful queue
            if self.credit_service:
                success, new_balance = await self.credit_service.deduct_credits(
                    user_id,
                    'image_processing',
                    reference_id=prompt_id
                )
                if success:
                    logger.info(
                        f"Deducted credits for user {user_id}, "
                        f"new balance: {new_balance}"
                    )
                else:
                    logger.error(f"Failed to deduct credits for user {user_id}")

            # Update user state
            self.state_manager.update_state(
                user_id,
                state='processing',
                prompt_id=prompt_id,
                filename=filename
            )

            # Show initial queue position
            position, total = await self.queue_service.get_queue_position(prompt_id)
            message = await self.notification_service.send_queue_position(
                bot,
                user_id,
                position,
                total,
                prompt_id
            )

            # Store message for later updates/deletion
            self.state_manager.set_queue_message(user_id, message)

            # Start monitoring in background
            asyncio.create_task(
                self._monitor_and_complete(
                    bot,
                    user_id,
                    prompt_id,
                    filename
                )
            )

            logger.info(
                f"Proceeded with image workflow for user {user_id}, "
                f"prompt_id: {prompt_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error proceeding with image workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                bot,
                user_id,
                "处理失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)
            return False

    async def _monitor_and_complete_image_styled(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str,
        style: str
    ):
        """
        Monitor styled image processing and handle completion.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            prompt_id: Prompt ID to monitor
            filename: Original filename
            style: Image style
        """
        async def completion_callback(outputs):
            """Called when styled image processing completes."""
            image_workflow = self.image_workflows[style]
            await image_workflow.handle_completion(
                bot,
                user_id,
                filename,
                outputs,
                self.state_manager,
                self.notification_service
            )

        # Start monitoring (pass styled workflow's ComfyUI service)
        image_workflow = self.image_workflows[style]
        await self.queue_service.monitor_processing(
            bot,
            user_id,
            prompt_id,
            completion_callback,
            comfyui_service=image_workflow.comfyui_service
        )

    async def proceed_with_image_workflow_with_style(self, bot, user_id: int):
        """
        Proceed with styled image workflow after user confirms credit deduction.
        Called from credit_confirmation_callback handler.

        Args:
            bot: Telegram Bot instance
            user_id: User ID

        Returns:
            True if successful, False if failed
        """
        try:
            state = self.state_manager.get_state(user_id)
            filename = state.get('filename')
            local_path = state.get('uploaded_file_path')
            style = state.get('image_style')

            if not filename or not local_path or not style:
                logger.error(f"Missing required data in state for user {user_id}")
                return False

            image_workflow = self.image_workflows[style]

            # Re-check credits based on style
            if self.credit_service:
                if style == 'undress':
                    # Check with free trial support
                    has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                        user_id,
                        'image_processing'
                    )

                    if not has_sufficient:
                        # Check if user has free trial
                        has_trial = await self.credit_service.has_free_trial(user_id)

                        if not has_trial:
                            # Insufficient credits - show error and topup menu
                            from core.constants import (
                                CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE,
                                TOPUP_PACKAGES_MESSAGE,
                                TOPUP_10_BUTTON,
                                TOPUP_30_BUTTON,
                                TOPUP_50_BUTTON,
                                TOPUP_100_BUTTON
                            )
                            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                            # Send insufficient credits message
                            await bot.send_message(
                                chat_id=user_id,
                                text=CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE.format(
                                    balance=int(balance),
                                    cost=int(cost)
                                )
                            )

                            # Show topup packages inline keyboard
                            keyboard = [
                                [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                                [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                                [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                                [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await bot.send_message(
                                chat_id=user_id,
                                text=TOPUP_PACKAGES_MESSAGE,
                                reply_markup=reply_markup
                            )

                            self.state_manager.reset_state(user_id)
                            return False

                else:  # style == 'bra' - permanently free (no credit checks)
                    # Bra style is permanently free - skip all credit checks
                    logger.info(
                        f"User {user_id} proceeding with bra style (permanently free)"
                    )

            # Queue workflow
            prompt_id = await image_workflow.queue_workflow(filename=filename)

            # Deduct credits after successful queue (skip if bra style - permanently free)
            if self.credit_service and style != 'bra':
                success, new_balance = await self.credit_service.deduct_credits(
                    user_id,
                    'image_processing',
                    reference_id=prompt_id
                )
                if success:
                    logger.info(
                        f"Deducted credits for user {user_id} (style: {style}), "
                        f"new balance: {new_balance}"
                    )
                else:
                    logger.error(f"Failed to deduct credits for user {user_id}")
            elif style == 'bra':
                logger.info(
                    f"Skipping credit deduction for user {user_id} (bra style - permanently free)"
                )

            # Update user state
            self.state_manager.update_state(
                user_id,
                state='processing',
                prompt_id=prompt_id,
                filename=filename,
                image_style=style
            )

            # Show initial queue position
            position, total = await self.queue_service.get_queue_position(prompt_id)
            message = await self.notification_service.send_queue_position(
                bot,
                user_id,
                position,
                total,
                prompt_id
            )

            # Store message for later updates/deletion
            self.state_manager.set_queue_message(user_id, message)

            # Start monitoring in background
            asyncio.create_task(
                self._monitor_and_complete_image_styled(
                    bot,
                    user_id,
                    prompt_id,
                    filename,
                    style
                )
            )

            logger.info(
                f"Proceeded with styled image workflow for user {user_id}, "
                f"style: {style}, prompt_id: {prompt_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error proceeding with styled image workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                bot,
                user_id,
                "处理失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)
            return False

    async def start_video_workflow(
        self,
        update,
        context,
        local_path: str,
        user_id: int,
        style: str
    ):
        """
        Upload image and show credit confirmation for video processing (NEW FLOW).
        Actual processing starts after user confirms via proceed_with_video_workflow().

        Args:
            update: Telegram Update object
            context: Telegram Context object
            local_path: Path to uploaded file
            user_id: User ID
            style: Video style ('style_a', 'style_b', or 'style_c')
        """
        try:
            filename = Path(local_path).name

            # Validate style
            if style not in self.video_workflows:
                await update.message.reply_text("选择的风格无效")
                self.state_manager.reset_state(user_id)
                return

            video_workflow = self.video_workflows[style]

            # Check credits (NO free trial for video)
            if self.credit_service:
                has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                    user_id,
                    'video_processing'
                )

                if not has_sufficient:
                    from core.constants import (
                        INSUFFICIENT_CREDITS_MESSAGE,
                        TOPUP_PACKAGES_MESSAGE,
                        TOPUP_10_BUTTON,
                        TOPUP_30_BUTTON,
                        TOPUP_50_BUTTON,
                        TOPUP_100_BUTTON
                    )
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                    # Send insufficient credits message
                    await update.message.reply_text(
                        INSUFFICIENT_CREDITS_MESSAGE.format(
                            balance=balance,
                            required=cost
                        )
                    )

                    # Show topup packages inline keyboard
                    keyboard = [
                        [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                        [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                        [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                        [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await context.bot.send_message(
                        chat_id=user_id,
                        text=TOPUP_PACKAGES_MESSAGE,
                        reply_markup=reply_markup
                    )

                    logger.warning(
                        f"User {user_id} has insufficient credits for video: "
                        f"balance={balance}, required={cost}"
                    )
                    self.state_manager.reset_state(user_id)
                    return

            # Upload image to ComfyUI
            await video_workflow.upload_image(local_path, filename)

            # Determine workflow name based on style
            from core.constants import (
                WORKFLOW_NAME_VIDEO_A,
                WORKFLOW_NAME_VIDEO_B,
                WORKFLOW_NAME_VIDEO_C
            )

            workflow_name_map = {
                'style_a': WORKFLOW_NAME_VIDEO_A,
                'style_b': WORKFLOW_NAME_VIDEO_B,
                'style_c': WORKFLOW_NAME_VIDEO_C
            }
            workflow_name = workflow_name_map.get(style, "图片转视频")

            # Store workflow details in state and show confirmation
            self.state_manager.update_state(
                user_id,
                state='waiting_for_credit_confirmation',
                uploaded_file_path=local_path,
                filename=filename,
                workflow_type=f'video_{style}',  # e.g., 'video_style_a'
                video_style=style
            )

            # Show credit confirmation (NO free trial for video)
            message = await self.notification_service.send_credit_confirmation(
                context.bot,
                user_id,
                workflow_name=workflow_name,
                workflow_type=f'video_{style}',
                balance=balance,
                cost=cost,
                is_free_trial=False,
                cooldown_info=None
            )

            # Store confirmation message for cleanup
            self.state_manager.set_confirmation_message(user_id, message)

            logger.info(
                f"Uploaded image and showed confirmation for user {user_id}, "
                f"video style: {style}"
            )

        except Exception as e:
            logger.error(f"Error starting video workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                context.bot,
                user_id,
                "上传失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)

    async def _monitor_and_complete_video(
        self,
        bot,
        user_id: int,
        prompt_id: str,
        filename: str,
        style: str
    ):
        """
        Monitor video processing and handle completion.

        Args:
            bot: Telegram Bot instance
            user_id: User ID
            prompt_id: Prompt ID to monitor
            filename: Original filename
            style: Video style
        """
        async def completion_callback(outputs):
            """Called when video processing completes."""
            video_workflow = self.video_workflows[style]
            await video_workflow.handle_completion(
                bot,
                user_id,
                filename,
                outputs,
                self.state_manager,
                self.notification_service
            )

        # Start monitoring (pass video workflow's ComfyUI service)
        video_workflow = self.video_workflows[style]
        await self.queue_service.monitor_processing(
            bot,
            user_id,
            prompt_id,
            completion_callback,
            comfyui_service=video_workflow.comfyui_service
        )

    async def proceed_with_video_workflow(self, bot, user_id: int):
        """
        Proceed with video workflow after user confirms credit deduction.
        Called from credit_confirmation_callback handler.
        NO REFUND POLICY: Credits deducted before queueing.

        Args:
            bot: Telegram Bot instance
            user_id: User ID

        Returns:
            True if successful, False if failed
        """
        try:
            state = self.state_manager.get_state(user_id)
            filename = state.get('filename')
            local_path = state.get('uploaded_file_path')
            style = state.get('video_style')

            if not filename or not local_path or not style:
                logger.error(f"Missing required data in state for user {user_id}")
                return False

            video_workflow = self.video_workflows[style]

            # Re-check credits (in case balance changed)
            if self.credit_service:
                has_sufficient, balance, cost = await self.credit_service.check_sufficient_credits(
                    user_id,
                    'video_processing'
                )

                if not has_sufficient:
                    # Insufficient credits - show error and topup menu
                    from core.constants import (
                        CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE,
                        TOPUP_PACKAGES_MESSAGE,
                        TOPUP_10_BUTTON,
                        TOPUP_30_BUTTON,
                        TOPUP_50_BUTTON,
                        TOPUP_100_BUTTON
                    )
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

                    # Send insufficient credits message
                    await bot.send_message(
                        chat_id=user_id,
                        text=CREDIT_INSUFFICIENT_ON_CONFIRM_MESSAGE.format(
                            balance=int(balance),
                            cost=int(cost)
                        )
                    )

                    # Show topup packages inline keyboard
                    keyboard = [
                        [InlineKeyboardButton(TOPUP_10_BUTTON, callback_data="topup_10")],
                        [InlineKeyboardButton(TOPUP_30_BUTTON, callback_data="topup_30")],
                        [InlineKeyboardButton(TOPUP_50_BUTTON, callback_data="topup_50")],
                        [InlineKeyboardButton(TOPUP_100_BUTTON, callback_data="topup_100")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await bot.send_message(
                        chat_id=user_id,
                        text=TOPUP_PACKAGES_MESSAGE,
                        reply_markup=reply_markup
                    )

                    self.state_manager.reset_state(user_id)
                    return False

                # DEDUCT CREDITS BEFORE QUEUEING (no refund policy)
                success, new_balance = await self.credit_service.deduct_credits(
                    user_id,
                    'video_processing',
                    reference_id=None
                )

                if not success:
                    await bot.send_message(
                        chat_id=user_id,
                        text="扣除积分失败，请重试"
                    )
                    self.state_manager.reset_state(user_id)
                    return False

                logger.info(
                    f"Deducted {cost} credits from user {user_id} for video, "
                    f"new balance: {new_balance}"
                )

            # Queue workflow
            prompt_id = await video_workflow.queue_workflow(filename=filename)

            # Update user state
            self.state_manager.update_state(
                user_id,
                state='processing',
                prompt_id=prompt_id,
                filename=filename,
                workflow_type='video',
                video_style=style
            )

            # Show initial queue position
            position, total = await self.queue_service.get_queue_position(prompt_id)
            message = await self.notification_service.send_queue_position(
                bot,
                user_id,
                position,
                total,
                prompt_id
            )

            # Store message for later updates/deletion
            self.state_manager.set_queue_message(user_id, message)

            # Start monitoring in background
            asyncio.create_task(
                self._monitor_and_complete_video(
                    bot,
                    user_id,
                    prompt_id,
                    filename,
                    style
                )
            )

            logger.info(
                f"Proceeded with video workflow for user {user_id}, "
                f"style: {style}, prompt_id: {prompt_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error proceeding with video workflow for user {user_id}: {str(e)}")
            await self.notification_service.send_error_message(
                bot,
                user_id,
                "处理失败，请稍后重试"
            )
            self.state_manager.reset_state(user_id)
            return False

    async def cancel_user_workflow(self, user_id: int) -> bool:
        """
        Cancel user's current workflow if any.

        Args:
            user_id: User ID

        Returns:
            True if cancelled, False if no active workflow
        """
        state = self.state_manager.get_state(user_id)

        if state.get('state') == 'processing':
            prompt_id = state.get('prompt_id')

            if prompt_id:
                # Try to cancel on ComfyUI (may not be supported)
                await self.comfyui_service.cancel_prompt(prompt_id)

                # Cancel cleanup task if exists
                self.state_manager.cancel_cleanup_task(user_id)

                # Delete queue message if exists
                if self.state_manager.has_queue_message(user_id):
                    queue_msg = self.state_manager.get_queue_message(user_id)
                    await self.notification_service.delete_message_safe(queue_msg)
                    self.state_manager.remove_queue_message(user_id)

                # Reset state
                self.state_manager.reset_state(user_id)

                logger.info(f"Cancelled workflow for user {user_id}")
                return True

        return False
