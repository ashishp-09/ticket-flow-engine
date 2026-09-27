from typing import NoReturn, Optional, Type
from sqlalchemy.exc import DBAPIError

from .exceptions import DatabaseError


class DatabaseExceptionMapper:
    def __init__(self, mapping_registry: Optional[dict[str, Type[DatabaseError]]] = None) -> None:
        self._mapping_registry = mapping_registry or {}

    def register_code(self, code: str, exception_cls: Type[DatabaseError]) -> None:
        self._mapping_registry[code] = exception_cls

    def handle(self, exc: DBAPIError) -> NoReturn:
        orig_err = exc.orig
        if not orig_err and hasattr(exc, "__cause__"):
            orig_err = exc.__cause__

        sqlstate = getattr(orig_err, "sqlstate", None)
        if not sqlstate and hasattr(orig_err, "__cause__"):
            orig_err = getattr(orig_err, "__cause__", None)
            sqlstate = getattr(orig_err, "sqlstate", None)

        if sqlstate in self._mapping_registry:
            error_class = self._mapping_registry[sqlstate]
            diag = getattr(orig_err, "diag", None)

            if diag is not None:
                raise error_class(
                    constraint=getattr(diag, "constraint_name", None),
                    table=getattr(diag, "table_name", None),
                    column=getattr(diag, "column_name", None),
                    detail=getattr(diag, "message_detail", None) or str(orig_err),
                ) from exc

            raise error_class(detail=str(orig_err)) from exc

        raise DatabaseError(
            message="Unhandled database exception occurred",
            detail=str(exc)
        ) from exc
