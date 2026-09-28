from typing import Any


class ServiceException(Exception):
    def __init__(self, message: str):
        self.message = message
        self.extra: dict[str, Any] = {}
        super().__init__(message)


class ForbiddenException(ServiceException):
    pass


class ConflictException(ServiceException):
    pass


class UnauthorizedException(ServiceException):
    pass


class ObjectNotFoundException(ServiceException):
    def __init__(self, table: str, value: any, field: str = "id"):
        if isinstance(value, (list, tuple, set)):
            vals = ", ".join(map(str, value))
            message = f"Objects in table '{table}' with {field}s in [{vals}] do not exist"
        else:
            message = f"Object in table '{table}' with {field} '{value}' does not exist"

        super().__init__(message)
        self.extra = {
            "table": table,
            "field": field,
            "value": value,
        }


class UniqueFieldException(ConflictException):
    def __init__(self, field: str, value: any):
        message = f"Object with unique field '{field}' with value '{value}' already exists."

        super().__init__(message)
        self.extra = {
            "field": field,
            "value": value,
        }


class WrongStateException(ConflictException):
    def __init__(self, expected: str | list[str], current: str | None = None) -> None:
        if isinstance(expected, list):
            expected_str = ", ".join(f"'{state}'" for state in expected)
        else:
            expected_str = f"'{expected}'"

        message = f"Cannot perform this operation due to the object state. Expected: {expected_str}"
        if current is not None:
            message += f", current: '{current}'"

        super().__init__(message)
        self.extra = {
            "expected": expected_str,
            "current": current,
        }
