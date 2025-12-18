"""
Database migration manager with versioning and tracking.

This eliminates the 11 silent migration failures found in the old codebase
by tracking all migration attempts and providing clear error messages.
"""

import sqlite3
import logging
from abc import ABC, abstractmethod
from typing import List, Dict
from pathlib import Path

from ..exceptions import MigrationError

logger = logging.getLogger('mark4_bot')


class Migration(ABC):
    """
    Base class for database migrations.

    Each migration must define:
    - version: Integer version number
    - description: Human-readable description
    - up(): Method to apply the migration
    - down(): Method to rollback (optional)
    """

    version: int = 0
    description: str = ""

    @abstractmethod
    def up(self, cursor: sqlite3.Cursor) -> None:
        """
        Apply migration.

        Args:
            cursor: Database cursor
        """
        raise NotImplementedError

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback migration (optional).

        Args:
            cursor: Database cursor
        """
        pass  # Optional: not all migrations are reversible


class MigrationManager:
    """
    Manages database schema migrations with tracking.

    Key features:
    - Tracks all migration attempts (success and failure)
    - Never silently swallows exceptions
    - Provides audit trail for troubleshooting
    - Version tracking prevents duplicate migrations
    """

    def __init__(self, db_path: str):
        """
        Initialize migration manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_database_exists()
        self._ensure_migration_table()

    def _ensure_database_exists(self):
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_migration_table(self):
        """Create migrations tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                execution_time_ms INTEGER
            )
        """)

        conn.commit()
        conn.close()
        logger.debug("Migration tracking table initialized")

    def get_current_version(self) -> int:
        """
        Get current schema version (highest successfully applied migration).

        Returns:
            Current version number (0 if no migrations applied)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(version) as version
            FROM schema_migrations
            WHERE success = 1
        """)
        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else 0

    def is_applied(self, version: int) -> bool:
        """
        Check if a migration has been successfully applied.

        Args:
            version: Migration version number

        Returns:
            True if migration was applied successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 1 FROM schema_migrations
            WHERE version = ? AND success = 1
        """, (version,))
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration with proper error handling and tracking.

        Args:
            migration: Migration instance to apply

        Returns:
            True if successful

        Raises:
            MigrationError: If migration fails
        """
        # Check if already applied
        if self.is_applied(migration.version):
            logger.info(f"Migration {migration.version} already applied, skipping")
            return True

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        import time
        start_time = time.time()

        try:
            logger.info(
                f"Applying migration {migration.version}: {migration.description}"
            )

            # Apply migration
            migration.up(cursor)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Record successful migration
            cursor.execute("""
                INSERT INTO schema_migrations (
                    version, description, success, execution_time_ms
                )
                VALUES (?, ?, 1, ?)
            """, (migration.version, migration.description, execution_time_ms))

            conn.commit()
            logger.info(
                f"✓ Migration {migration.version} applied successfully "
                f"({execution_time_ms}ms)"
            )
            return True

        except Exception as e:
            logger.error(f"✗ Migration {migration.version} FAILED: {e}")

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Record failed migration (for audit trail)
            try:
                cursor.execute("""
                    INSERT INTO schema_migrations (
                        version, description, success,
                        error_message, execution_time_ms
                    )
                    VALUES (?, ?, 0, ?, ?)
                """, (
                    migration.version,
                    migration.description,
                    str(e),
                    execution_time_ms
                ))
                conn.commit()
            except Exception:
                # If we can't even record the failure, log it
                logger.error(
                    f"Failed to record migration failure for version "
                    f"{migration.version}"
                )

            conn.rollback()
            raise MigrationError(migration.version, str(e)) from e

        finally:
            conn.close()

    def apply_migrations(self, migrations: List[Migration]) -> int:
        """
        Apply multiple migrations in order.

        Args:
            migrations: List of Migration instances

        Returns:
            Number of migrations applied

        Raises:
            MigrationError: If any migration fails
        """
        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: m.version)

        applied_count = 0
        for migration in sorted_migrations:
            if self.apply_migration(migration):
                applied_count += 1

        return applied_count

    def get_failed_migrations(self) -> List[Dict]:
        """
        Get list of failed migrations for troubleshooting.

        Returns:
            List of dicts with migration failure information
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version, description, applied_at, error_message, execution_time_ms
            FROM schema_migrations
            WHERE success = 0
            ORDER BY version
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_migration_history(self) -> List[Dict]:
        """
        Get complete migration history (successful and failed).

        Returns:
            List of dicts with migration information
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT version, description, applied_at, success,
                   error_message, execution_time_ms
            FROM schema_migrations
            ORDER BY version
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def rollback_migration(self, migration: Migration) -> bool:
        """
        Rollback a migration.

        Args:
            migration: Migration instance to rollback

        Returns:
            True if successful

        Raises:
            MigrationError: If rollback fails
        """
        if not self.is_applied(migration.version):
            logger.info(f"Migration {migration.version} not applied, nothing to rollback")
            return True

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            logger.info(
                f"Rolling back migration {migration.version}: {migration.description}"
            )

            # Rollback migration
            migration.down(cursor)

            # Remove from tracking table
            cursor.execute("""
                DELETE FROM schema_migrations
                WHERE version = ?
            """, (migration.version,))

            conn.commit()
            logger.info(f"✓ Migration {migration.version} rolled back successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Rollback of migration {migration.version} FAILED: {e}")
            conn.rollback()
            raise MigrationError(migration.version, f"Rollback failed: {e}") from e

        finally:
            conn.close()
