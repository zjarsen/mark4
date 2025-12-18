"""Database layer for mark4 bot - provides type-safe, transaction-safe data access."""

from .connection import DatabaseConnection
from .exceptions import (
    DatabaseError,
    ConnectionError,
    IntegrityError,
    NotFoundError,
    TransactionError,
    MigrationError,
    DuplicateError,
    QueryError
)
from .models import User, Transaction, Payment

__all__ = [
    'DatabaseConnection',
    'DatabaseError',
    'ConnectionError',
    'IntegrityError',
    'NotFoundError',
    'TransactionError',
    'MigrationError',
    'DuplicateError',
    'QueryError',
    'User',
    'Transaction',
    'Payment'
]
