"""Domain-level exceptions.

All business rule violations are expressed as subclasses of DomainException
so the CLI layer can catch them uniformly and display user-friendly messages.
"""


class DomainException(Exception):
    """Base class for all domain errors."""


class ValidationError(DomainException):
    """A business rule or invariant was violated."""


class EntityNotFoundError(DomainException):
    """A requested entity does not exist."""
