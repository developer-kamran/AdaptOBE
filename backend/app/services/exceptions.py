class ConflictError(Exception):
    """Raised when a uniqueness constraint would be violated."""


class NotFoundError(Exception):
    """Raised when a requested record does not exist."""


class PermissionDeniedError(Exception):
    """Raised when a user may not act on a resource they do not own."""


class ValidationError(Exception):
    """Raised when a request is well-formed but semantically invalid."""


class LLMGenerationError(Exception):
    """Raised when an external LLM call fails or returns unusable output."""
