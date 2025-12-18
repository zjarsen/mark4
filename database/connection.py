"""
Database connection management with pooling and context managers.

This module provides:
- Thread-safe connection management
- Automatic transaction management via context managers
- Proper error handling and rollback
- Connection pooling (thread-local connections)
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator
from pathlib import Path
import threading

from .exceptions import ConnectionError as DBConnectionError, TransactionError, IntegrityError

logger = logging.getLogger('mark4_bot')


class DatabaseConnection:
    """
    Thread-safe database connection pool manager.

    Uses thread-local storage to maintain one connection per thread,
    which is safe for use with async handlers in python-telegram-bot.
    """

    def __init__(self, db_path: str):
        """
        Initialize connection manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()  # Thread-local storage
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local connection (lazy initialization).

        Returns:
            sqlite3.Connection: Thread-local database connection

        Raises:
            DBConnectionError: If connection fails
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA busy_timeout = 5000")  # Avoid "database locked"
                self._local.connection = conn
                logger.debug(f"Created connection for thread {threading.current_thread().name}")
            except sqlite3.Error as e:
                raise DBConnectionError(f"Failed to connect to database: {e}") from e
        return self._local.connection

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """
        Context manager for database cursor with auto-commit/rollback.

        Usage:
            with conn_manager.get_cursor() as cursor:
                cursor.execute("INSERT ...")
                # Auto-commits on success, rolls back on exception

        Yields:
            sqlite3.Cursor: Database cursor

        Raises:
            IntegrityError: On constraint violation
            TransactionError: On other database errors
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except sqlite3.IntegrityError as e:
            conn.rollback()
            # Extract constraint name if available
            constraint = None
            error_str = str(e).lower()
            if 'unique' in error_str:
                constraint = 'UNIQUE'
            elif 'foreign key' in error_str:
                constraint = 'FOREIGN KEY'
            raise IntegrityError(str(e), constraint=constraint) from e
        except sqlite3.Error as e:
            conn.rollback()
            raise TransactionError(f"Transaction failed: {e}") from e
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error in transaction: {e}", exc_info=True)
            raise
        finally:
            cursor.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for explicit multi-step transactions.

        Use this when you need to perform multiple operations atomically
        (all succeed or all fail together).

        Usage:
            with conn_manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = ?", ...)
                cursor.execute("INSERT INTO transactions ...", ...)
                # Both succeed or both roll back

        Yields:
            sqlite3.Connection: Database connection

        Raises:
            TransactionError: On transaction failure
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully")
        except sqlite3.IntegrityError as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to integrity error: {e}")
            constraint = None
            error_str = str(e).lower()
            if 'unique' in error_str:
                constraint = 'UNIQUE'
            elif 'foreign key' in error_str:
                constraint = 'FOREIGN KEY'
            raise IntegrityError(str(e), constraint=constraint) from e
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}", exc_info=True)
            raise TransactionError(f"Transaction failed: {e}") from e

    def close(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.debug(f"Closed connection for thread {threading.current_thread().name}")

    def close_all(self):
        """
        Close all connections (call on application shutdown).

        Note: This only closes the connection for the current thread.
        In a multi-threaded environment, each thread should call close().
        """
        self.close()
