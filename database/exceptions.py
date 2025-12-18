"""
Database exception hierarchy for specific error handling.

This replaces the 179 generic 'except Exception' blocks found in the codebase
with specific exception types that allow targeted error handling and better
debugging.
"""


class DatabaseError(Exception):
    """Base exception for all database errors."""
    pass


class ConnectionError(DatabaseError):
    """Failed to connect to database or connection was lost."""
    pass


class IntegrityError(DatabaseError):
    """
    Data integrity violation (foreign key, unique constraint, check constraint).

    Attributes:
        constraint: Name of the constraint that was violated (if available)
    """
    def __init__(self, message: str, constraint: str = None):
        super().__init__(message)
        self.constraint = constraint


class NotFoundError(DatabaseError):
    """
    Entity not found in database.

    Attributes:
        entity_type: Type of entity (e.g., 'User', 'Payment')
        entity_id: ID of the entity that wasn't found
    """
    def __init__(self, entity_type: str, entity_id: any):
        super().__init__(f"{entity_type} not found: {entity_id}")
        self.entity_type = entity_type
        self.entity_id = entity_id


class TransactionError(DatabaseError):
    """Transaction commit or rollback failed."""
    pass


class MigrationError(DatabaseError):
    """
    Migration execution failed.

    Attributes:
        migration_version: Version number of the failed migration
    """
    def __init__(self, migration_version: int, message: str):
        super().__init__(f"Migration {migration_version} failed: {message}")
        self.migration_version = migration_version


class DuplicateError(IntegrityError):
    """Duplicate key violation (UNIQUE constraint)."""
    pass


class QueryError(DatabaseError):
    """SQL query execution failed."""
    pass
