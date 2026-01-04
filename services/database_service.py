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
                    feature_type TEXT,
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

            # Migration: Add last_free_trial_used_at column for recurring free trial system
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_free_trial_used_at TIMESTAMP")
                logger.info("Added last_free_trial_used_at column to users table")

                # Migration Strategy: Reset all existing users' trials (Option A)
                # Set last_free_trial_used_at = NULL for all users
                # This gives everyone immediate access to the new recurring trial system
                cursor.execute("""
                    UPDATE users
                    SET last_free_trial_used_at = NULL,
                        free_image_processing_used = 0
                    WHERE 1=1
                """)
                logger.info("Reset all users' free trials for recurring system migration")

            except Exception as e:
                logger.debug(f"Migration already applied or error: {e}")

            # Migration: Add vip_tier column for VIP system
            try:
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN vip_tier TEXT DEFAULT 'none'
                    CHECK(vip_tier IN ('none', 'vip', 'black_gold'))
                """)
                logger.info("Added vip_tier column to users table")
            except Exception as e:
                logger.debug(f"vip_tier column already exists or error: {e}")

            # Migration: Add metadata column to payments for VIP purchases
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN metadata TEXT")
                logger.info("Added metadata column to payments table")
            except Exception:
                pass  # Column already exists

            # Migration: Add language_code to payments for webhook translation
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN language_code TEXT DEFAULT 'zh_CN'")
                logger.info("Added language_code column to payments table")
            except Exception:
                pass  # Column already exists

            # Migration: Add payment_method to track payment method used
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN payment_method TEXT DEFAULT 'alipay'")
                logger.info("Added payment_method column to payments table")
            except Exception:
                pass  # Column already exists

            # Migration: Add daily discount system columns
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN interaction_days INTEGER DEFAULT 0")
                logger.info("Added interaction_days column to users table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_interaction_date TEXT")
                logger.info("Added last_interaction_date column to users table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_discount_rate REAL")
                logger.info("Added daily_discount_rate column to users table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_discount_tier TEXT")
                logger.info("Added daily_discount_tier column to users table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_discount_date TEXT")
                logger.info("Added daily_discount_date column to users table")
            except Exception:
                pass  # Column already exists

            # Migration: Add feature_type column to transactions for tracking specific features
            try:
                cursor.execute("ALTER TABLE transactions ADD COLUMN feature_type TEXT")
                logger.info("Added feature_type column to transactions table")
            except Exception:
                pass  # Column already exists

            # Migration: Add daily usage tracking columns for VIP limits
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_usage_count INTEGER DEFAULT 0")
                logger.info("Added daily_usage_count column to users table")
            except Exception:
                pass  # Column already exists

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN daily_usage_date TEXT")
                logger.info("Added daily_usage_date column to users table")
            except Exception:
                pass  # Column already exists

            # Migration: Add language preference for multi-language support
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN language_preference TEXT DEFAULT 'zh_CN'")
                logger.info("Added language_preference column to users table")
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

            # Insert video processing feature pricing (图片转视频脱衣 = 30 积分)
            cursor.execute("""
                INSERT OR IGNORE INTO feature_pricing (feature_name, credit_cost, description)
                VALUES ('video_processing', 30.0, '图片转视频脱衣')
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
                SET free_image_processing_used = 1,
                    last_free_trial_used_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
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
        reference_id: str = None,
        feature_type: str = None
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
            feature_type: Optional feature type (e.g., 'image_bra', 'image_undress', 'video_style_a', 'video_style_b', 'video_style_c')

        Returns:
            Transaction ID if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO transactions
                (user_id, transaction_type, amount, balance_before, balance_after, description, reference_id, feature_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, transaction_type, amount, balance_before, balance_after, description, reference_id, feature_type))

            conn.commit()
            transaction_id = cursor.lastrowid
            logger.info(f"Created transaction {transaction_id} for user {user_id}: {transaction_type} {amount} (feature: {feature_type})")
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
        message_id: int = None,
        language_code: str = None,
        payment_method: str = 'alipay'
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
            language_code: User's language preference for webhook translation
            payment_method: Payment method used ('stars', 'alipay', 'wechat')

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get user's language if not provided
            if language_code is None:
                language_code = self.get_user_language(user_id)

            cursor.execute("""
                INSERT INTO payments
                (payment_id, user_id, provider, amount, currency, credits_amount, status, payment_url, chat_id, message_id, language_code, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (payment_id, user_id, provider, amount, currency, credits_amount, status, payment_url, chat_id, message_id, language_code, payment_method))

            conn.commit()
            logger.info(f"Created payment record {payment_id} for user {user_id} (method: {payment_method}, lang: {language_code})")
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

    # VIP operations
    def get_vip_tier(self, user_id: int) -> str:
        """
        Get user's VIP tier.

        Args:
            user_id: User ID

        Returns:
            'none', 'vip', or 'black_gold'
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT vip_tier FROM users WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()

            if result and result['vip_tier']:
                return result['vip_tier']
            return 'none'

        except Exception as e:
            logger.error(f"Error getting VIP tier for user {user_id}: {str(e)}")
            return 'none'

    def set_vip_tier(self, user_id: int, tier: str) -> bool:
        """
        Set user's VIP tier.

        Args:
            user_id: User ID
            tier: 'none', 'vip', or 'black_gold'

        Returns:
            True if successful
        """
        try:
            # Validate tier
            if tier not in ['none', 'vip', 'black_gold']:
                logger.error(f"Invalid VIP tier: {tier}")
                return False

            conn = self._get_connection()
            cursor = conn.cursor()

            # Ensure user exists
            self.get_user(user_id)

            # Update VIP tier
            cursor.execute("""
                UPDATE users
                SET vip_tier = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (tier, user_id))

            conn.commit()
            logger.info(f"Set VIP tier for user {user_id} to {tier}")
            return True

        except Exception as e:
            logger.error(f"Error setting VIP tier for user {user_id}: {str(e)}")
            conn.rollback()
            return False

    def is_vip(self, user_id: int) -> bool:
        """
        Check if user has any VIP status.

        Args:
            user_id: User ID

        Returns:
            True if user is VIP or Black Gold VIP
        """
        tier = self.get_vip_tier(user_id)
        return tier in ['vip', 'black_gold']

    def is_black_gold_vip(self, user_id: int) -> bool:
        """
        Check if user has Black Gold VIP status.

        Args:
            user_id: User ID

        Returns:
            True if user is Black Gold VIP
        """
        return self.get_vip_tier(user_id) == 'black_gold'

    # Daily discount operations
    def update_user_interaction(self, user_id: int, current_date: str):
        """
        Update user interaction tracking.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format (GMT+8)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get user's last interaction date
            cursor.execute("""
                SELECT last_interaction_date, interaction_days
                FROM users
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if not result:
                return

            last_date = result['last_interaction_date']
            current_days = result['interaction_days'] or 0

            # If it's a new day, increment interaction_days
            if last_date != current_date:
                new_days = current_days + 1
                cursor.execute("""
                    UPDATE users
                    SET interaction_days = ?,
                        last_interaction_date = ?
                    WHERE user_id = ?
                """, (new_days, current_date, user_id))
                conn.commit()
                logger.info(f"Updated interaction for user {user_id}: day {new_days}")

        except Exception as e:
            logger.error(f"Error updating user interaction for {user_id}: {str(e)}")

    def get_user_discount_info(self, user_id: int) -> Optional[Dict]:
        """
        Get user's discount information.

        Args:
            user_id: User ID

        Returns:
            Dictionary with discount info or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT interaction_days, last_interaction_date,
                       daily_discount_rate, daily_discount_tier, daily_discount_date
                FROM users
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"Error getting discount info for user {user_id}: {str(e)}")
            return None

    def save_daily_discount(self, user_id: int, tier: str, rate: float, discount_date: str):
        """
        Save user's daily discount.

        Args:
            user_id: User ID
            tier: Discount tier (SSR, SR, R, C)
            rate: Discount rate (0.5, 0.7, 0.85, 0.95)
            discount_date: Date in YYYY-MM-DD format (GMT+8)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET daily_discount_tier = ?,
                    daily_discount_rate = ?,
                    daily_discount_date = ?
                WHERE user_id = ?
            """, (tier, rate, discount_date, user_id))

            conn.commit()
            logger.info(f"Saved daily discount for user {user_id}: {tier} ({rate})")

        except Exception as e:
            logger.error(f"Error saving daily discount for user {user_id}: {str(e)}")

    # Daily usage tracking for VIP limits
    def get_daily_usage_count(self, user_id: int, current_date: str) -> int:
        """
        Get user's daily usage count.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format (GMT+8)

        Returns:
            Daily usage count
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT daily_usage_count, daily_usage_date
                FROM users
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if not result:
                return 0

            usage_date = result['daily_usage_date']
            usage_count = result['daily_usage_count'] or 0

            # If it's a new day, reset the count
            if usage_date != current_date:
                return 0

            return usage_count

        except Exception as e:
            logger.error(f"Error getting daily usage for user {user_id}: {str(e)}")
            return 0

    def increment_daily_usage(self, user_id: int, current_date: str) -> bool:
        """
        Increment user's daily usage count.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format (GMT+8)

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get current usage
            cursor.execute("""
                SELECT daily_usage_count, daily_usage_date
                FROM users
                WHERE user_id = ?
            """, (user_id,))

            result = cursor.fetchone()
            if not result:
                return False

            usage_date = result['daily_usage_date']
            usage_count = result['daily_usage_count'] or 0

            # If it's a new day, reset count to 1
            if usage_date != current_date:
                new_count = 1
            else:
                new_count = usage_count + 1

            # Update usage
            cursor.execute("""
                UPDATE users
                SET daily_usage_count = ?,
                    daily_usage_date = ?
                WHERE user_id = ?
            """, (new_count, current_date, user_id))

            conn.commit()
            logger.info(f"Updated daily usage for user {user_id}: {new_count} (date: {current_date})")
            return True

        except Exception as e:
            logger.error(f"Error incrementing daily usage for user {user_id}: {str(e)}")
            return False

    def get_bra_usage_count(self, user_id: int, current_date: str) -> int:
        """
        Get count of bra feature uses today for a specific user.

        Args:
            user_id: User ID
            current_date: Current date in YYYY-MM-DD format (GMT+8)

        Returns:
            Count of bra feature uses today
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE user_id = ?
                AND feature_type = 'image_bra'
                AND DATE(created_at) = ?
            """, (user_id, current_date))

            result = cursor.fetchone()
            return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Error getting bra usage count for user {user_id}: {str(e)}")
            return 0

    # Language preference operations
    def get_user_language(self, user_id: int) -> str:
        """
        Get user's language preference.

        Args:
            user_id: User ID

        Returns:
            Language code (default: zh_CN)
        """
        user = self.get_user(user_id)
        return user.get('language_preference', 'zh_CN') if user else 'zh_CN'

    def set_user_language(self, user_id: int, language: str) -> bool:
        """
        Set user's language preference.

        Args:
            user_id: User ID
            language: Language code (e.g., 'zh_CN', 'en_US', 'ja_JP')

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Ensure user exists
            self.get_user(user_id)

            # Update language preference
            cursor.execute("""
                UPDATE users
                SET language_preference = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (language, user_id))

            conn.commit()
            logger.info(f"Set language for user {user_id} to {language}")
            return True

        except Exception as e:
            logger.error(f"Error setting language for user {user_id}: {str(e)}")
            return False

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
