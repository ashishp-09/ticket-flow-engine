from typing import Any, Optional


class DatabaseError(Exception):
    message: str = "Database error occurred"

    def __init__(
            self,
            message: Optional[str] = None,
            constraint: Optional[str] = None,
            table: Optional[str] = None,
            column: Optional[str] = None,
            detail: Optional[Any] = None,
    ) -> None:
        self.message = message or self.message
        self.constraint = constraint
        self.table = table
        self.column = column
        self.detail = detail
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.table:
            parts.append(f"Table: {self.table}")
        if self.constraint:
            parts.append(f"Constraint: {self.constraint}")
        if self.column:
            parts.append(f"Column: {self.column}")
        if self.detail:
            parts.append(f"Detail: {self.detail}")
        return " | ".join(parts)


class UniqueViolationError(DatabaseError):
    message: str = "Unique constraint violation detected"


class ForeignKeyViolationError(DatabaseError):
    message: str = "Foreign key constraint violation detected"


class NotNullViolationError(DatabaseError):
    message: str = "Not null constraint violation detected"


class ReadOnlyViolationError(DatabaseError):
    message: str = "Write operation attempted in read-only transaction"
