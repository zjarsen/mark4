"""Common decorators for handlers."""

import functools
import logging
from typing import Callable

logger = logging.getLogger('mark4_bot')


def log_handler(func: Callable):
    """
    Decorator to log handler entry and exit.

    Args:
        func: Handler function to wrap

    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = "Unknown"
        if update.effective_user:
            user_id = update.effective_user.id

        logger.info(f"Handler {func.__name__} called by user {user_id}")

        try:
            result = await func(update, context, *args, **kwargs)
            logger.debug(f"Handler {func.__name__} completed successfully")
            return result

        except Exception as e:
            logger.error(
                f"Handler {func.__name__} failed: {str(e)}",
                exc_info=True
            )
            raise

    return wrapper


def handle_errors(error_message: str = None):
    """
    Decorator to catch and handle errors in handlers.

    Args:
        error_message: Optional custom error message to send to user

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            try:
                return await func(update, context, *args, **kwargs)

            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    exc_info=True
                )

                # Try to send error message to user
                if update.message:
                    try:
                        from core.constants import ERROR_MESSAGE
                        msg = error_message if error_message else ERROR_MESSAGE
                        await update.message.reply_text(msg)
                    except:
                        pass

        return wrapper
    return decorator


def require_state(required_state: str):
    """
    Decorator to check user state before handler execution.

    Args:
        required_state: Required state value

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            # Note: state_manager must be accessible from context
            # This is a simplified version
            # In production, you'd need to access state_manager from context
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def rate_limit(max_calls: int, period_seconds: int):
    """
    Decorator to rate limit handler calls (future implementation).

    Args:
        max_calls: Maximum calls allowed
        period_seconds: Time period in seconds

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        # TODO: Implement rate limiting logic
        # Could use Redis or in-memory dict with timestamps
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator
