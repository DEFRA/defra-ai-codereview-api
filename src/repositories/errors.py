"""Custom repository exceptions."""


class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass


"""Repository error classes."""


class RepositoryError(Exception):
    """Repository operation error."""
    pass


class DuplicateError(Exception):
    """Raised when attempting to create a duplicate record."""
    pass
