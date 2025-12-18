"""Credit domain exceptions."""


class CreditError(Exception):
    """Base exception for credit operations."""
    pass


class InsufficientCreditsError(CreditError):
    """
    User does not have enough credits for an operation.

    Attributes:
        user_id: User ID
        required: Credits required
        available: Credits available
    """
    def __init__(self, user_id: int, required: float, available: float):
        self.user_id = user_id
        self.required = required
        self.available = available
        super().__init__(
            f"User {user_id} has insufficient credits: "
            f"need {required}, have {available}"
        )


class InvalidAmountError(CreditError):
    """
    Invalid credit amount specified.

    Attributes:
        amount: The invalid amount
    """
    def __init__(self, amount: float, reason: str = None):
        self.amount = amount
        self.reason = reason
        message = f"Invalid credit amount: {amount}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)
