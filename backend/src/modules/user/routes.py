from fastapi import APIRouter, status

from src.core.infra.transport.http import JWTManagerDep, PasswordManagerDep
from .dependencies import AnyUserIdDep, UserServiceDep
from .schemas import (
    UserCreateResponseSchema,
    UserCreateSchema,
    UserLoginResponseSchema,
    UserLoginSchema,
    UserResponseSchema,
)

user_router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@user_router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user(service: UserServiceDep, user_id: AnyUserIdDep) -> UserResponseSchema:
    return await service.get(user_id=user_id)


@user_router.post("", status_code=status.HTTP_201_CREATED)
async def register(
        service: UserServiceDep,
        pwd_manager: PasswordManagerDep,
        body: UserCreateSchema,
) -> UserCreateResponseSchema:
    return await service.create(pwd_manager=pwd_manager, data=body)


@user_router.post("/login", status_code=status.HTTP_200_OK)
async def login(
        body: UserLoginSchema, service: UserServiceDep, pwd_manager: PasswordManagerDep, jwt_manager: JWTManagerDep
) -> UserLoginResponseSchema:
    return await service.authenticate(data=body, pwd_manager=pwd_manager, jwt_manager=jwt_manager)


@user_router.post("/verification/apply", status_code=status.HTTP_204_NO_CONTENT)
async def apply_for_verification(service: UserServiceDep, user_id: AnyUserIdDep):
    await service.apply_for_verification(user_id)
