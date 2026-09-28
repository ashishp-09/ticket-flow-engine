import pytest

from core.mixins.generic import BaseGeneratedMixin
from core.testing.base import APITestBase
from core.types import AuthClientFactory
from core.utils import generate_error_values_for_int, generate_error_values_for_order_by
from src.modules.user.models import UserRole


class PaginationErrorsMixin(BaseGeneratedMixin):
    @classmethod
    def with_params(
            cls,
            path: str,
            role: str | None = None,
    ) -> type:
        class Container(APITestBase):
            @pytest.mark.parametrize("value", generate_error_values_for_int(min_value=0, max_value=100))
            async def test_limit_validation_errors(
                    self,
                    value: str | int,
                    auth_client_factory: AuthClientFactory,
            ) -> None:
                role_arg = UserRole(role) if role is not None else None
                await self._assert_filter_validation_error(
                    client=auth_client_factory(role_arg),
                    path=path,
                    query_params={"limit": value}
                )

            @pytest.mark.parametrize("value", generate_error_values_for_int(min_value=0))
            async def test_offset_validation_errors(
                    self,
                    value: str | int,
                    auth_client_factory: AuthClientFactory,
            ) -> None:
                role_arg = UserRole(role) if role is not None else None
                await self._assert_filter_validation_error(
                    client=auth_client_factory(role_arg),
                    path=path,
                    query_params={"offset": value}
                )

        return cls._generate(path, Container)


class OrderByErrorsMixin(BaseGeneratedMixin):
    @classmethod
    def with_params(
            cls,
            path: str,
            role: str | None = None,
            *,
            invalid_field: str,
    ) -> type:
        values = generate_error_values_for_order_by(invalid_field)

        class Container(APITestBase):
            @pytest.mark.parametrize("value", values)
            async def test_order_by_validation_errors(
                    self,
                    value: str,
                    auth_client_factory: AuthClientFactory,
            ) -> None:
                role_arg = UserRole(role) if role is not None else None
                await self._assert_filter_validation_error(
                    client=auth_client_factory(role_arg),
                    path=path,
                    query_params={"order_by": value}
                )

        return cls._generate(path, Container)
