from typing import Any

from src.app.exceptions import ObjectNotFoundException, ServiceException, UniqueFieldException, WrongStateException
from src.app.uow import AppUnitOfWork
from src.core.infra.transport.http import PaginatedResponseSchema
from src.core.security import PasswordManager
from src.core.security.jwt_tokens import JWTManager
from src.domain.services.base import GenericService
from .exceptions import (
    CannotBanAdminException,
    CannotBanYourselfException,
    CannotUnbanYourselfException,
    CurrentUserIsBannedException, IncorrectLoginDataException,
    UserIsBannedException,
)
from .models import UserRole
from .schemas import (
    UserCreateResponseSchema,
    UserCreateSchema,
    UserLoginResponseSchema,
    UserLoginSchema,
    UserResponseSchema,
)


class UserService(GenericService[AppUnitOfWork]):
    async def create(self, pwd_manager: PasswordManager, data: UserCreateSchema) -> UserCreateResponseSchema:
        async with self.uow:
            try:
                existing_obj = await self.uow.user.get(email=data.email)
            except ValueError:
                existing_obj = None

            if existing_obj:
                raise UniqueFieldException(
                    field="email",
                    value=data.email,
                )

            hashed_password = await pwd_manager.hash_password(data.password)
            user_data = data.model_dump()
            user_data["password"] = hashed_password

            obj = await self.uow.user.create(**user_data)
            await self.uow.commit()

        await self.tasks.perform_task(name="order:transfer_anonym_orders", email=data.email)

        return UserCreateResponseSchema.model_validate(obj)

    async def authenticate(
            self, data: UserLoginSchema, pwd_manager: PasswordManager, jwt_manager: JWTManager
    ) -> UserLoginResponseSchema:
        async with self.uow.as_readonly():
            user = await self.uow.user.get(email=data.email)

        if not user or not await pwd_manager.verify_password(data.password, user.password):
            raise IncorrectLoginDataException()

        if not user.is_active:
            raise CurrentUserIsBannedException()

        token = jwt_manager.create_access_token(
            data={
                "sub": str(user.id),
                "role": user.role.value,
            }
        )

        return UserLoginResponseSchema(access_token=token, token_type="bearer")

    async def apply_for_verification(self, user_id: int) -> bool:
        async with self.uow:
            user_dto = await (
                self.uow.user
                .filter(id=user_id, role=UserRole.USER, is_active=True)
                .update(role=UserRole.ON_VERIFICATION)
            )

            if user_dto is not None:
                await self.uow.commit()
                return True

            user = await self.uow.user.get(id=user_id)

        if user is None:
            raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=user_id)

        if not user.is_active:
            raise CurrentUserIsBannedException()

        if user.role == UserRole.ON_VERIFICATION:
            return True
        else:
            raise WrongStateException(current=user.role, expected=UserRole.USER)

    async def verify(self, user_id: int, result: bool) -> bool:
        async with self.uow:
            target_role = UserRole.VERIFIED_USER if result else UserRole.USER

            user_dto = await (
                self.uow.user
                .filter(id=user_id, role=UserRole.ON_VERIFICATION, is_active=True)
                .update(role=target_role)
            )

            if user_dto is not None:
                await self.uow.commit()
                return True

            user = await self.uow.user.get(id=user_id)

        if user is None:
            raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=user_id)

        if not user.is_active:
            raise UserIsBannedException()

        if user.role == target_role:
            return True
        else:
            raise WrongStateException(current=user.role, expected=UserRole.ON_VERIFICATION)

    async def ban(self, user_id: int, actor_id: int) -> bool:
        if user_id == actor_id:
            raise CannotBanYourselfException()

        async with self.uow:
            user_dto = await self.uow.user.filter(id=user_id, role__ne=UserRole.ADMIN).update(is_active=False)

            if user_dto is not None:
                await self.uow.commit()
                return True

            user = await self.uow.user.get(id=user_id)

        if not user:
            raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=user_id)

        if user.role == UserRole.ADMIN:
            raise CannotBanAdminException()

        if not user.is_active:
            return True

        raise ServiceException("Unexpected user state.")

    async def unban(self, user_id: int, actor_id: int) -> bool:
        if user_id == actor_id:
            raise CannotUnbanYourselfException()

        async with self.uow:
            user_dto = await self.uow.user.filter(id=user_id).update(is_active=True)

            if user_dto is not None:
                await self.uow.commit()
                return True

            user = await self.uow.user.get(id=user_id)

        if not user:
            raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=user_id)

        if user.is_active:
            return True

        raise ServiceException("Unexpected user state.")

    async def get(self, user_id: int) -> UserResponseSchema:
        async with self.uow.as_readonly():
            user_dto = await self.uow.user.get(id=user_id)

        if not user_dto:
            raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=user_id)

        return UserResponseSchema.model_validate(user_dto)

    async def get_all(
            self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100,
            order_by: str | None = None
    ) -> PaginatedResponseSchema[UserResponseSchema]:
        async with self.uow.as_readonly():
            items, count = (
                await self.uow.user
                .filter(**(filters or {}))
                .order_by(order_by)
                .paginate(limit=limit, offset=offset)
            )

        return self._paginate(
            schema=UserResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )

    async def get_for_verification(
            self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100,
            order_by: str | None = None
    ) -> PaginatedResponseSchema[UserResponseSchema]:
        async with self.uow.as_readonly():
            items, count = (
                await self.uow.user
                .filter(role=UserRole.ON_VERIFICATION, **(filters or {}))
                .order_by(order_by)
                .paginate(limit=limit, offset=offset)
            )

        return self._paginate(
            schema=UserResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )
