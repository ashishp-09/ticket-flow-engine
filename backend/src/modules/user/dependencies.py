from typing import Annotated, Optional

from fastapi import Depends, Query

from src.app.uow import create_app_uow
from src.core.infra.database import get_service_factory
from .models import UserRole
from .roles import RoleChecker
from .schemas import UsersFilterParamsSchema
from .services import UserService

UserServiceDep = Annotated[UserService, Depends(get_service_factory(create_app_uow, UserService))]

OptionalUserIdDep = Annotated[Optional[int], Depends(RoleChecker(optional=True))]
AnyUserIdDep = Annotated[int, Depends(RoleChecker())]

VerifiedUserIdDep = Annotated[int, Depends(RoleChecker(required_role=UserRole.VERIFIED_USER))]
ModeratorUserIdDep = Annotated[int, Depends(RoleChecker(required_role=UserRole.MODERATOR))]
AdminUserIdDep = Annotated[int, Depends(RoleChecker(required_role=UserRole.ADMIN))]

UserFiltersDep = Annotated[UsersFilterParamsSchema, Query()]
