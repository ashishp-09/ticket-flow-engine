from typing import Annotated

from fastapi import Depends, Query

from src.core.security import JWTManager, PasswordManager
from src.core.settings import get_settings
from .schemas.pagination import PaginationParamsSchema

config = get_settings()


async def get_jwt_manager() -> JWTManager:
    return JWTManager(
        secret_key=config.jwt_secret_key, algorithm=config.jwt_algorithm, expire_seconds=config.jwt_expires_in
    )


def get_password_manager() -> PasswordManager:
    return PasswordManager(algorithm=config.password_algorithm, iterations=config.password_iterations)


JWTManagerDep = Annotated[JWTManager, Depends(get_jwt_manager)]
PasswordManagerDep = Annotated[PasswordManager, Depends(get_password_manager)]
PaginationParamsDep = Annotated[PaginationParamsSchema, Query()]
