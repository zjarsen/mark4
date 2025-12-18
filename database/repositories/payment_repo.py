"""
Payment repository for database operations.

This handles all payment-related database operations,
including payment order creation, status tracking, and completion.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models import Payment, row_to_payment
from ..exceptions import NotFoundError

logger = logging.getLogger('mark4_bot')


class PaymentRepository(BaseRepository):
    """Repository for payment-related database operations."""

    def create(
        self,
        payment_id: str,
        user_id: int,
        provider: str,
        amount: float,
        currency: str,
        credits_amount: float,
        status: str = 'pending',
        payment_url: str = None,
        chat_id: int = None,
        message_id: int = None,
        metadata: str = None,
        expires_at: datetime = None
    ) -> Payment:
        """
        Create a new payment record.

        Args:
            payment_id: Unique payment ID
            user_id: User ID
            provider: Payment provider ('taitaitai')
            amount: Payment amount in CNY
            currency: Currency code ('CNY')
            credits_amount: Credits to grant on completion
            status: Payment status (default: 'pending')
            payment_url: URL for user to complete payment
            chat_id: Telegram chat ID (for editing messages)
            message_id: Telegram message ID (for editing messages)
            metadata: Additional metadata (e.g., 'vip_tier:vip')
            expires_at: Payment expiration timestamp

        Returns:
            Newly created Payment model

        Raises:
            IntegrityError: If payment_id already exists
            QueryError: On database error
        """
        query = """
            INSERT INTO payments (
                payment_id, user_id, provider, amount, currency,
                credits_amount, status, payment_url, chat_id,
                message_id, metadata, expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(query, (
            payment_id, user_id, provider, amount, currency,
            credits_amount, status, payment_url, chat_id,
            message_id, metadata, expires_at
        ))
        logger.info(f"Created payment {payment_id} for user {user_id}: {amount} CNY")
        return self.get_by_id(payment_id)

    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """
        Get payment by ID.

        Args:
            payment_id: Payment ID

        Returns:
            Payment model or None
        """
        query = "SELECT * FROM payments WHERE payment_id = ?"
        row = self._fetch_one(query, (payment_id,))
        return row_to_payment(row) if row else None

    def get_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Payment]:
        """
        Get payments for a user, sorted by most recent first.

        Args:
            user_id: User ID
            limit: Maximum number of payments to return
            offset: Number of payments to skip

        Returns:
            List of Payment models
        """
        query = """
            SELECT * FROM payments
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = self._fetch_all(query, (user_id, limit, offset))
        return [row_to_payment(row) for row in rows]

    def get_by_status(
        self,
        status: str,
        limit: int = 100
    ) -> List[Payment]:
        """
        Get payments by status.

        Args:
            status: Payment status ('pending', 'completed', 'failed', etc.)
            limit: Maximum number of payments

        Returns:
            List of Payment models
        """
        query = """
            SELECT * FROM payments
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self._fetch_all(query, (status, limit))
        return [row_to_payment(row) for row in rows]

    def update_status(
        self,
        payment_id: str,
        status: str,
        completed_at: datetime = None
    ) -> bool:
        """
        Update payment status.

        Args:
            payment_id: Payment ID
            status: New status
            completed_at: Completion timestamp (optional)

        Returns:
            True if successful

        Raises:
            QueryError: On database error
        """
        if completed_at:
            query = """
                UPDATE payments
                SET status = ?, completed_at = ?
                WHERE payment_id = ?
            """
            self._execute(query, (status, completed_at, payment_id))
        else:
            query = """
                UPDATE payments
                SET status = ?
                WHERE payment_id = ?
            """
            self._execute(query, (status, payment_id))

        logger.info(f"Updated payment {payment_id} status to {status}")
        return True

    def update_message_refs(
        self,
        payment_id: str,
        chat_id: int,
        message_id: int
    ) -> bool:
        """
        Update Telegram message references for a payment.

        Args:
            payment_id: Payment ID
            chat_id: Telegram chat ID
            message_id: Telegram message ID

        Returns:
            True if successful
        """
        query = """
            UPDATE payments
            SET chat_id = ?, message_id = ?
            WHERE payment_id = ?
        """
        self._execute(query, (chat_id, message_id, payment_id))
        return True

    def update_metadata(self, payment_id: str, metadata: str) -> bool:
        """
        Update payment metadata.

        Args:
            payment_id: Payment ID
            metadata: Metadata string (e.g., 'vip_tier:vip')

        Returns:
            True if successful
        """
        query = """
            UPDATE payments
            SET metadata = ?
            WHERE payment_id = ?
        """
        self._execute(query, (metadata, payment_id))
        return True

    def get_pending_payments(
        self,
        user_id: int = None,
        older_than_minutes: int = None
    ) -> List[Payment]:
        """
        Get pending payments, optionally filtered by user and age.

        Args:
            user_id: Filter by user ID (optional)
            older_than_minutes: Only return payments older than N minutes

        Returns:
            List of Payment models
        """
        if user_id and older_than_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=older_than_minutes)
            query = """
                SELECT * FROM payments
                WHERE user_id = ? AND status = 'pending' AND created_at < ?
                ORDER BY created_at DESC
            """
            rows = self._fetch_all(query, (user_id, cutoff_time))
        elif user_id:
            query = """
                SELECT * FROM payments
                WHERE user_id = ? AND status = 'pending'
                ORDER BY created_at DESC
            """
            rows = self._fetch_all(query, (user_id,))
        elif older_than_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=older_than_minutes)
            query = """
                SELECT * FROM payments
                WHERE status = 'pending' AND created_at < ?
                ORDER BY created_at DESC
            """
            rows = self._fetch_all(query, (cutoff_time,))
        else:
            query = """
                SELECT * FROM payments
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """
            rows = self._fetch_all(query)

        return [row_to_payment(row) for row in rows]

    def get_expired_payments(self) -> List[Payment]:
        """
        Get all expired pending payments.

        Returns:
            List of Payment models that are pending and past expiration
        """
        query = """
            SELECT * FROM payments
            WHERE status = 'pending'
              AND expires_at IS NOT NULL
              AND expires_at < ?
            ORDER BY expires_at DESC
        """
        rows = self._fetch_all(query, (datetime.now(),))
        return [row_to_payment(row) for row in rows]

    def get_completed_payments_by_user(self, user_id: int) -> List[Payment]:
        """
        Get all completed payments for a user.

        Args:
            user_id: User ID

        Returns:
            List of completed Payment models
        """
        query = """
            SELECT * FROM payments
            WHERE user_id = ? AND status = 'completed'
            ORDER BY completed_at DESC
        """
        rows = self._fetch_all(query, (user_id,))
        return [row_to_payment(row) for row in rows]

    def sum_completed_payments_by_user(self, user_id: int) -> float:
        """
        Calculate total completed payment amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total payment amount (CNY)
        """
        query = """
            SELECT COALESCE(SUM(amount), 0.0) as total
            FROM payments
            WHERE user_id = ? AND status = 'completed'
        """
        row = self._fetch_one(query, (user_id,))
        return float(row['total']) if row else 0.0

    def count_by_status(self, status: str) -> int:
        """
        Count payments by status.

        Args:
            status: Payment status

        Returns:
            Payment count
        """
        return self._count(
            "SELECT COUNT(*) FROM payments WHERE status = ?",
            (status,)
        )

    def get_all_payments(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Payment]:
        """
        Get all payments across all users (for admin analytics).

        Args:
            limit: Maximum number of payments
            offset: Number of payments to skip

        Returns:
            List of Payment models
        """
        query = """
            SELECT * FROM payments
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = self._fetch_all(query, (limit, offset))
        return [row_to_payment(row) for row in rows]

    def count_total_payments(self) -> int:
        """
        Get total number of payments across all users.

        Returns:
            Total payment count
        """
        return self._count("SELECT COUNT(*) FROM payments")
