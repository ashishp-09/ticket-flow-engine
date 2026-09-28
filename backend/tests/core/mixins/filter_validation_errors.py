from datetime import datetime
from typing import Any, Callable

import pytest

from core.mixins.generic import BaseGeneratedMixin
from core.testing.base import APITestBase
from core.types import AuthClientFactory
from core.utils import generate_error_values_for_awaredatetime, generate_error_values_for_int, \
    generate_error_values_for_list, generate_error_values_for_str
from src.modules.user.models import UserRole


class FilterValidationErrorsMixin(BaseGeneratedMixin):
    _GENERATORS: dict[type, Callable[..., list[Any]]] = {
        int: generate_error_values_for_int,
        str: generate_error_values_for_str,
        list: generate_error_values_for_list,
        datetime: generate_error_values_for_awaredatetime,
    }

    @classmethod
    def with_params(
            cls,
            path: str,
            role: UserRole | None = None,
            *,
            filters: dict[str, type | tuple[type, dict[str, Any]]],
    ) -> type:
        parametrize_cases = []

        for field, conf in filters.items():
            f_type, kwargs = conf if isinstance(conf, tuple) else (conf, {})

            if f_type not in cls._GENERATORS:
                raise ValueError(f"Unknown filter type: {f_type}")

            for val in cls._GENERATORS[f_type](**kwargs):
                parametrize_cases.append((field, val))

        class Container(APITestBase):
            @pytest.mark.parametrize("field, value", parametrize_cases)
            async def test_filter_validation_error(
                    self,
                    auth_client_factory: AuthClientFactory,
                    field: str,
                    value: Any
            ) -> None:
                role_arg = UserRole(role) if role is not None else None
                await self._assert_filter_validation_error(
                    client=auth_client_factory(role_arg),
                    path=path,
                    query_params={field: value},
                )

        return cls._generate(path, Container)
