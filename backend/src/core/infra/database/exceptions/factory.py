from .exceptions import ForeignKeyViolationError, NotNullViolationError, \
    ReadOnlyViolationError, UniqueViolationError
from .mapper import DatabaseExceptionMapper


def create_postgres_exception_mapper() -> DatabaseExceptionMapper:
    postgres_mapping = {
        "23505": UniqueViolationError,
        "23503": ForeignKeyViolationError,
        "23502": NotNullViolationError,
        "25006": ReadOnlyViolationError,
    }
    return DatabaseExceptionMapper(mapping_registry=postgres_mapping)
