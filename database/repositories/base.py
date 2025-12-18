"""
Base repository with common database operations.

This eliminates the 18 repeated boilerplate patterns found in the old
database_service.py by providing reusable helper methods for all repositories.
"""

import sqlite3
import logging
from typing import Optional, List, Any, Tuple
from abc import ABC

from ..connection import DatabaseConnection
from ..exceptions import QueryError, IntegrityError

logger = logging.getLogger('mark4_bot')


class BaseRepository(ABC):
    """
    Abstract base repository with helper methods.

    Provides:
    - Consistent error handling (no more generic 'except Exception')
    - Automatic transaction management
    - Reusable query patterns
    - Type-safe returns

    Usage:
        class UserRepository(BaseRepository):
            def get_by_id(self, user_id: int) -> Optional[User]:
                row = self._fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
                return row_to_user(row) if row else None
    """

    def __init__(self, connection_manager: DatabaseConnection):
        """
        Initialize repository with connection manager.

        Args:
            connection_manager: DatabaseConnection instance
        """
        self.conn_manager = connection_manager

    def _execute_query(
        self,
        query: str,
        params: Tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Optional[Any]:
        """
        Execute query with error handling (eliminates boilerplate).

        This method replaces the repeated try-except-finally pattern
        found in 18 methods in the old codebase.

        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows

        Returns:
            Query results or None

        Raises:
            IntegrityError: On constraint violation
            QueryError: On other SQL errors
        """
        try:
            with self.conn_manager.get_cursor() as cursor:
                cursor.execute(query, params)

                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.lastrowid

        except IntegrityError:
            # Re-raise integrity errors (already specific)
            raise
        except sqlite3.Error as e:
            logger.error(f"Query error: {query[:100]}... Error: {e}")
            raise QueryError(f"Query failed: {e}") from e

    def _fetch_one(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """
        Fetch single row.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            Single row or None

        Example:
            row = self._fetch_one("SELECT * FROM users WHERE user_id = ?", (123,))
        """
        return self._execute_query(query, params, fetch_one=True)

    def _fetch_all(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """
        Fetch all rows.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            List of rows (empty list if no results)

        Example:
            rows = self._fetch_all("SELECT * FROM users WHERE vip_tier = ?", ('vip',))
        """
        result = self._execute_query(query, params, fetch_all=True)
        return result if result else []

    def _execute(self, query: str, params: Tuple = ()) -> int:
        """
        Execute query and return lastrowid.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            Last inserted row ID

        Example:
            user_id = self._execute("INSERT INTO users (user_id, ...) VALUES (?, ...)", (123, ...))
        """
        return self._execute_query(query, params)

    def _exists(self, query: str, params: Tuple = ()) -> bool:
        """
        Check if a record exists.

        Args:
            query: SQL query string (should be a SELECT query)
            params: Query parameters tuple

        Returns:
            True if record exists, False otherwise

        Example:
            exists = self._exists("SELECT 1 FROM users WHERE user_id = ?", (123,))
        """
        row = self._fetch_one(query, params)
        return row is not None

    def _count(self, query: str, params: Tuple = ()) -> int:
        """
        Execute COUNT query.

        Args:
            query: SQL COUNT query
            params: Query parameters tuple

        Returns:
            Count result

        Example:
            count = self._count("SELECT COUNT(*) as count FROM users WHERE vip_tier = ?", ('vip',))
        """
        row = self._fetch_one(query, params)
        return row[0] if row else 0
