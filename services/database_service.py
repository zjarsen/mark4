"""Database service for persistent storage using SQLite."""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger('mark4_bot')


class DatabaseService:
    """Service for database operations using SQLite."""

    def __init__(self, config):
        """
        Initialize database service.

        Args:
            config: Configuration object
        """
        self.config = config
        self.db_path = config.DATABASE_PATH
        self.connection = None
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection.

        Returns:
            SQLite connection object
        """
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
        return self.connection

    def _initialize_database(self):
        """Create database tables if they don't exist."""
        try:
            # Ensure database directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            conn = self._get_connection()
            cursor = conn.cursor()

            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    telegram_username TEXT,
                    credit_balance REAL DEFAULT 0.0,
                    total_spent REAL DEFAULT 0.0,
                    free_image_processing_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    description TEXT,
                    reference_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    credits_amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    payment_url TEXT,
                    chat_id INTEGER,
                    message_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Migration: Add chat_id and message_id columns if they don't exist
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN chat_id INTEGER")
                logger.info("Added chat_id column to payments table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN message_id INTEGER")
                logger.info("Added message_id column to payments table")
            except Exception:
                pass  # Column already exists

            # Feature pricing table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feature_pricing (
                    feature_name TEXT PRIMARY KEY,
                    credit_cost REAL NOT NULL,
                    description TEXT,
                    enabled BOOLEAN DEFAULT 1
                )
            """)

            # Insert default feature pricing (图片脱衣 = 10 积分)
            cursor.execute("""
                INSERT OR IGNORE INTO feature_pricing (feature_name, credit_cost, description)
                VALUES ('image_processing', 10.0, '图片脱衣')
            """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    # User operations
    def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID, create if doesn't exist.

        Args:
            user_id: Telegram user ID

        Returns:
            User dictionary or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                return dict(user)
            else:
                # Create new user with 0 credits and free trial available
                cursor.execute("""
                    INSERT INTO users (user_id, credit_balance, free_image_processing_used)
                    VALUES (?, 0.0, 0)
                """, (user_id,))
                conn.commit()
                logger.info(f"Created new user: {user_id}")
                return self.get_user(user_id)

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None

    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """
        Update user's credit balance.

        Args:
            user_id: User ID
            new_balance: New balance amount

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET credit_balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (new_balance, user_id))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {str(e)}")
            return False

    def mark_free_trial_used(self, user_id: int) -> bool:
        """
        Mark that user has used their free trial.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET free_image_processing_used = 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))

            conn.commit()
            logger.info(f"Marked free trial used for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error marking free trial for user {user_id}: {str(e)}")
            return False

    # Transaction operations
    def create_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount: float,
        balance_before: float,
        balance_after: float,
        description: str = None,
        reference_id: str = None
    ) -> Optional[int]:
        """
        Create a transaction record.

        Args:
            user_id: User ID
            transaction_type: 'topup', 'deduction', 'refund'
            amount: Transaction amount
            balance_before: Balance before transaction
            balance_after: Balance after transaction
            description: Optional description
            reference_id: Optional reference (payment_id or prompt_id)

        Returns:
            Transaction ID if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO transactions
                (user_id, transaction_type, amount, balance_before, balance_after, description, reference_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, transaction_type, amount, balance_before, balance_after, description, reference_id))

            conn.commit()
            transaction_id = cursor.lastrowid
            logger.info(f"Created transaction {transaction_id} for user {user_id}: {transaction_type} {amount}")
            return transaction_id

        except Exception as e:
            logger.error(f"Error creating transaction for user {user_id}: {str(e)}")
            return None

    def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get user's transaction history.

        Args:
            user_id: User ID
            limit: Number of transactions to return

        Returns:
            List of transaction dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))

            transactions = cursor.fetchall()
            return [dict(t) for t in transactions]

        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {str(e)}")
            return []

    # Payment operations
    def create_payment_record(
        self,
        payment_id: str,
        user_id: int,
        provider: str,
        amount: float,
        currency: str,
        credits_amount: float,
        status: str,
        payment_url: str = None,
        chat_id: int = None,
        message_id: int = None
    ) -> bool:
        """
        Create payment record.

        Args:
            payment_id: Unique payment ID
            user_id: User ID
            provider: Payment provider name
            amount: Payment amount
            currency: Currency code
            credits_amount: Credits to be awarded
            status: Payment status
            payment_url: Optional payment URL
            chat_id: Optional Telegram chat ID
            message_id: Optional Telegram message ID

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO payments
                (payment_id, user_id, provider, amount, currency, credits_amount, status, payment_url, chat_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (payment_id, user_id, provider, amount, currency, credits_amount, status, payment_url, chat_id, message_id))

            conn.commit()
            logger.info(f"Created payment record {payment_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating payment record {payment_id}: {str(e)}")
            return False

    def update_payment_status(
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
            completed_at: Completion timestamp

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if completed_at:
                cursor.execute("""
                    UPDATE payments
                    SET status = ?, completed_at = ?
                    WHERE payment_id = ?
                """, (status, completed_at, payment_id))
            else:
                cursor.execute("""
                    UPDATE payments
                    SET status = ?
                    WHERE payment_id = ?
                """, (status, payment_id))

            conn.commit()
            logger.info(f"Updated payment {payment_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {str(e)}")
            return False

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        """
        Get payment by ID.

        Args:
            payment_id: Payment ID

        Returns:
            Payment dictionary or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
            payment = cursor.fetchone()

            return dict(payment) if payment else None

        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {str(e)}")
            return None

    # Feature pricing operations
    def get_feature_cost(self, feature_name: str) -> Optional[float]:
        """
        Get cost of a feature in credits.

        Args:
            feature_name: Feature name

        Returns:
            Cost in credits or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT credit_cost FROM feature_pricing
                WHERE feature_name = ? AND enabled = 1
            """, (feature_name,))

            result = cursor.fetchone()
            return result['credit_cost'] if result else None

        except Exception as e:
            logger.error(f"Error getting feature cost for {feature_name}: {str(e)}")
            return None

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
