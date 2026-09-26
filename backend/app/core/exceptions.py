"""Domain-level exceptions used across services and translated to HTTP
responses by API exception handlers. Keeps routes and services free of
framework-specific error handling."""


class PharmaOneError(Exception):
    """Base class for application errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(PharmaOneError):
    """Raised when a requested resource does not exist."""


class ValidationError(PharmaOneError):
    """Raised when input fails a business rule (distinct from schema validation)."""
