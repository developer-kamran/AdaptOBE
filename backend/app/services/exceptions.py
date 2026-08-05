class ConflictError(Exception):
    """Raised when a uniqueness constraint would be violated."""


class NotFoundError(Exception):
    """Raised when a requested record does not exist."""
