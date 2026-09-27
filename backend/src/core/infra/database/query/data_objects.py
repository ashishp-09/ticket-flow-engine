from dataclasses import dataclass
from typing import Any, Optional


class BaseDTO:
    pass


@dataclass(frozen=True)
class ModificationResult:
    rowcount: int
    returning_rows: list[Any]

    @property
    def success(self) -> bool:
        return self.rowcount > 0 or bool(self.returning_rows)

    @property
    def first_returning(self) -> Optional[Any]:
        return self.returning_rows[0] if self.returning_rows else None

    @property
    def scalar_returning(self) -> Optional[Any]:
        return self.returning_rows[0][0] if self.returning_rows else None
