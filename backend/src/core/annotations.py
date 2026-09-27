from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from typing import TypeVar


SERVICE_T = TypeVar("SERVICE_T", bound="GenericService")
REPOSITORY_T = TypeVar("REPOSITORY_T", bound="GenericRepository")
UOW_T = TypeVar("UOW_T", bound="AbstractUnitOfWork")

ORM_MODEL_T = TypeVar("ORM_MODEL_T", bound="BaseORMModel")
DTO_T = TypeVar("DTO_T", bound="BaseDTO")
