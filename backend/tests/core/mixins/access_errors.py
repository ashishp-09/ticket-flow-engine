from typing import Literal

from core.mixins.generic import BaseGeneratedMixin
from core.testing.base import APITestBase
from core.types import AsAnonymClient, WithRoleClient
from src.modules.user.models import UserRole


class UnauthenticatedAccessMixin(BaseGeneratedMixin):
    @classmethod
    def with_params(
            cls,
            method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
            path: str,
    ) -> type:
        class Container(APITestBase):
            async def test_error_when_unauthorized(
                    self,
                    as_anonym: AsAnonymClient,
            ) -> None:
                await self._assert_unauthorized_error(
                    client=as_anonym(),
                    method=method,
                    path=path,
                )

        return cls._generate(f"{method}_{path}", Container)


class UnauthorizedAccessMixin(BaseGeneratedMixin):
    @classmethod
    def with_params(
            cls,
            method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
            path: str,
            role: UserRole,
    ) -> type:
        class Container(APITestBase):
            async def test_error_when_user_has_no_rights(
                    self,
                    with_role: WithRoleClient,
            ) -> None:
                await self._assert_forbidden_error(
                    client=with_role(UserRole(role)),
                    method=method,
                    path=path,
                )

        return cls._generate(f"{method}_{role}_{path}", Container)
