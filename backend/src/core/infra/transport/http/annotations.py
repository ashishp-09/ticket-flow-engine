from __future__ import annotations

from typing import TypeVar, Annotated

from fastapi.params import Path
from pydantic import BaseModel as PydanticBaseModel, Field, StringConstraints

from src.core.infra.database.constants import DB_INT_MAX

PYDANTIC_MODEL_T = TypeVar("PYDANTIC_MODEL_T", bound=PydanticBaseModel)
Int32Path = Annotated[int, Path(ge=1, le=DB_INT_MAX)]

Int32 = Annotated[int, Field(ge=-2147483648, le=2147483647)]
PositiveInt32 = Annotated[int, Field(ge=1, le=2147483647)]
NonNegativeInt32 = Annotated[int, Field(ge=0, le=2147483647)]
NonEmptyString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
