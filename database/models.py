"""
Type-safe database models using TypedDict.

These models provide:
- IDE autocomplete for all database fields
- Type checking to catch typos at development time
- Clear schema documentation
- Replacement for untyped Dict returns
"""

from typing import TypedDict, Optional
from datetime import datetime
import sqlite3


class User(TypedDict, total=False):
    """
    User database model.

    Fields:
        user_id: Telegram user ID (primary key)
        telegram_username: Telegram username (optional)
        credit_balance: Current credit balance
        total_spent: Total amount spent (CNY)
        free_image_processing_used: Whether free trial has been used
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_free_trial_used_at: Last time free trial was used
        vip_tier: VIP status ('none', 'vip', 'black_gold')
        interaction_days: Number of days user has interacted
        last_interaction_date: Last interaction date (YYYY-MM-DD)
        daily_discount_rate: Current daily discount rate (0.5-0.95)
        daily_discount_tier: Current discount tier ('SSR', 'SR', 'R', 'C')
        daily_discount_date: Date discount was revealed (YYYY-MM-DD)
        daily_usage_count: Usage count for current day
        daily_usage_date: Date of usage count (YYYY-MM-DD)
    """
    user_id: int
    telegram_username: Optional[str]
    credit_balance: float
    total_spent: float
    free_image_processing_used: bool
    created_at: datetime
    updated_at: datetime
    last_free_trial_used_at: Optional[datetime]
    vip_tier: str
    interaction_days: int
    last_interaction_date: Optional[str]
    daily_discount_rate: Optional[float]
    daily_discount_tier: Optional[str]
    daily_discount_date: Optional[str]
    daily_usage_count: int
    daily_usage_date: Optional[str]


class Transaction(TypedDict, total=False):
    """
    Transaction database model.

    Fields:
        id: Transaction ID (primary key)
        user_id: User who made the transaction
        transaction_type: Type of transaction ('topup', 'deduction', 'refund')
        amount: Transaction amount (positive for topup/refund, negative for deduction)
        balance_before: Balance before transaction
        balance_after: Balance after transaction
        description: Human-readable description
        reference_id: Reference ID for external systems (e.g., payment ID)
        feature_type: Feature that caused the transaction (e.g., 'image_undress')
        created_at: Transaction timestamp
    """
    id: int
    user_id: int
    transaction_type: str
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str]
    reference_id: Optional[str]
    feature_type: Optional[str]
    created_at: datetime


class Payment(TypedDict, total=False):
    """
    Payment database model.

    Fields:
        payment_id: Payment ID (primary key)
        user_id: User who initiated the payment
        provider: Payment provider ('taitaitai')
        amount: Payment amount in CNY
        currency: Currency code ('CNY')
        credits_amount: Credits to be granted on completion
        status: Payment status ('pending', 'completed', 'failed', 'expired', 'cancelled')
        payment_url: URL for user to complete payment
        chat_id: Telegram chat ID (for editing messages)
        message_id: Telegram message ID (for editing messages)
        metadata: Additional metadata (e.g., 'vip_tier:vip')
        created_at: Payment creation timestamp
        completed_at: Payment completion timestamp
        expires_at: Payment expiration timestamp
    """
    payment_id: str
    user_id: int
    provider: str
    amount: float
    currency: str
    credits_amount: float
    status: str
    payment_url: Optional[str]
    chat_id: Optional[int]
    message_id: Optional[int]
    metadata: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]


# Type conversion helpers

def row_to_user(row: sqlite3.Row) -> User:
    """Convert sqlite3.Row to User model."""
    return User(**dict(row))


def row_to_transaction(row: sqlite3.Row) -> Transaction:
    """Convert sqlite3.Row to Transaction model."""
    return Transaction(**dict(row))


def row_to_payment(row: sqlite3.Row) -> Payment:
    """Convert sqlite3.Row to Payment model."""
    return Payment(**dict(row))
