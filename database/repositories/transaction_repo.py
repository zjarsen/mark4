"""
Transaction repository for database operations.

This handles all transaction-related database operations,
providing a clean interface for transaction history and analytics.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .base import BaseRepository
from ..models import Transaction, row_to_transaction

logger = logging.getLogger('mark4_bot')


class TransactionRepository(BaseRepository):
    """Repository for transaction-related database operations."""

    def create(
        self,
        user_id: int,
        transaction_type: str,
        amount: float,
        balance_before: float,
        balance_after: float,
        description: str = None,
        reference_id: str = None,
        feature_type: str = None
    ) -> int:
        """
        Create a new transaction record.

        Args:
            user_id: User ID
            transaction_type: Type ('topup', 'deduction', 'refund')
            amount: Transaction amount
            balance_before: Balance before transaction
            balance_after: Balance after transaction
            description: Human-readable description
            reference_id: External reference ID (e.g., payment_id)
            feature_type: Feature that caused transaction

        Returns:
            Transaction ID

        Raises:
            QueryError: On database error
        """
        query = """
            INSERT INTO transactions (
                user_id, transaction_type, amount,
                balance_before, balance_after, description,
                reference_id, feature_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        transaction_id = self._execute(query, (
            user_id, transaction_type, amount,
            balance_before, balance_after, description,
            reference_id, feature_type
        ))
        logger.debug(
            f"Created transaction {transaction_id} for user {user_id}: "
            f"{transaction_type} {amount}"
        )
        return transaction_id

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Get transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction model or None
        """
        query = "SELECT * FROM transactions WHERE id = ?"
        row = self._fetch_one(query, (transaction_id,))
        return row_to_transaction(row) if row else None

    def get_by_user(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Transaction]:
        """
        Get transactions for a user, sorted by most recent first.

        Args:
            user_id: User ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            List of Transaction models
        """
        query = """
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = self._fetch_all(query, (user_id, limit, offset))
        return [row_to_transaction(row) for row in rows]

    def get_by_type(
        self,
        user_id: int,
        transaction_type: str,
        limit: int = 50
    ) -> List[Transaction]:
        """
        Get transactions of a specific type for a user.

        Args:
            user_id: User ID
            transaction_type: Type ('topup', 'deduction', 'refund')
            limit: Maximum number of transactions

        Returns:
            List of Transaction models
        """
        query = """
            SELECT * FROM transactions
            WHERE user_id = ? AND transaction_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self._fetch_all(query, (user_id, transaction_type, limit))
        return [row_to_transaction(row) for row in rows]

    def get_by_feature_type(
        self,
        user_id: int,
        feature_type: str,
        limit: int = 50
    ) -> List[Transaction]:
        """
        Get transactions for a specific feature.

        Args:
            user_id: User ID
            feature_type: Feature type (e.g., 'image_undress')
            limit: Maximum number of transactions

        Returns:
            List of Transaction models
        """
        query = """
            SELECT * FROM transactions
            WHERE user_id = ? AND feature_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = self._fetch_all(query, (user_id, feature_type, limit))
        return [row_to_transaction(row) for row in rows]

    def get_recent_by_reference(
        self,
        reference_id: str,
        days: int = 7
    ) -> List[Transaction]:
        """
        Get recent transactions by reference ID.

        Useful for finding transactions related to a payment or refund.

        Args:
            reference_id: Reference ID to search for
            days: How many days back to search

        Returns:
            List of Transaction models
        """
        since_date = datetime.now() - timedelta(days=days)
        query = """
            SELECT * FROM transactions
            WHERE reference_id = ? AND created_at >= ?
            ORDER BY created_at DESC
        """
        rows = self._fetch_all(query, (reference_id, since_date))
        return [row_to_transaction(row) for row in rows]

    def count_by_user(self, user_id: int) -> int:
        """
        Count total transactions for a user.

        Args:
            user_id: User ID

        Returns:
            Transaction count
        """
        return self._count(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,)
        )

    def sum_topups_by_user(self, user_id: int) -> float:
        """
        Calculate total top-up amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total top-up amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0.0) as total
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'topup'
        """
        row = self._fetch_one(query, (user_id,))
        return float(row['total']) if row else 0.0

    def sum_deductions_by_user(self, user_id: int) -> float:
        """
        Calculate total deduction amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total deduction amount (positive number)
        """
        query = """
            SELECT COALESCE(SUM(ABS(amount)), 0.0) as total
            FROM transactions
            WHERE user_id = ? AND transaction_type = 'deduction'
        """
        row = self._fetch_one(query, (user_id,))
        return float(row['total']) if row else 0.0

    def get_all_transactions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Transaction]:
        """
        Get all transactions across all users (for admin analytics).

        Args:
            limit: Maximum number of transactions
            offset: Number of transactions to skip

        Returns:
            List of Transaction models
        """
        query = """
            SELECT * FROM transactions
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = self._fetch_all(query, (limit, offset))
        return [row_to_transaction(row) for row in rows]

    def count_total_transactions(self) -> int:
        """
        Get total number of transactions across all users.

        Returns:
            Total transaction count
        """
        return self._count("SELECT COUNT(*) FROM transactions")
