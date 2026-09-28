from datetime import datetime
from typing import Any

from httpx import AsyncClient, Response


class APITestBase:
    def _stringify_response_body(self, resp: Response) -> str:
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        stringified_body = str(body)
        if len(stringified_body) > 2000:
            stringified_body = stringified_body[:2000] + "... [TRUNCATED]"

        return stringified_body

    def _assert_status_code(self, resp: Response, status_code: int) -> None:
        if resp.status_code == status_code:
            return

        assert resp.status_code == status_code, (
            f"\n[Status Code Mismatch] {resp.request.method} {resp.request.url}\n"
            f"Expected status: {status_code} | Actual status: {resp.status_code}\n"
            f"Response body: {self._stringify_response_body(resp)}\n"
        )

    def _get_client_method(self, client: AsyncClient, method: str) -> callable:
        client_method = getattr(client, method.lower())
        if client_method is None:
            raise ValueError(f"Class {client.__class__.__name__} has not method '{method}'.")
        return client_method

    def _prepare_request_data(self, path: str, method: str, data: dict | None = None) -> dict:
        request_data = {"url": path}

        if method.lower() in ("get", "delete"):
            request_data["params"] = data
        else:
            request_data["json"] = data

        return request_data

    async def _execute_and_assert_status_code(
            self,
            client: AsyncClient,
            method: str,
            path: str,
            status_code: int,
            data: dict[str, Any] | None = None
    ) -> Response:
        client_method = self._get_client_method(client, method)
        resp = await client_method(**self._prepare_request_data(path, method, data))
        self._assert_status_code(resp, status_code)
        return resp

    async def _assert_filter_validation_error(self, client: AsyncClient, path: str,
                                              query_params: dict[str, Any]) -> None:
        await self._execute_and_assert_status_code(client, "GET", path, 422, query_params)

    async def _assert_unauthorized_error(self, client: AsyncClient, method: str, path: str) -> None:
        await self._execute_and_assert_status_code(client, method, path, 401)

    async def _assert_forbidden_error(self, client: AsyncClient, method: str, path: str) -> None:
        await self._execute_and_assert_status_code(client, method, path, 403)

    async def _assert_accepted(
            self,
            client: AsyncClient,
            method: str,
            path: str,
            data: dict[str, Any] | None = None
    ) -> Response | None:
        return await self._execute_and_assert_status_code(client, method, path, 202, data)

    async def _assert_ok(
            self,
            client: AsyncClient,
            method: str,
            path: str,
            data: dict[str, Any] | None = None
    ) -> Response | None:
        return await self._execute_and_assert_status_code(client, method, path, 200, data)

    async def _get_item_by_id(
            self,
            client: AsyncClient,
            path: str,
            obj_id: int,
            data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        resp = await self._assert_ok(client, "GET", path + str(obj_id), data)
        return resp.json()

    async def _assert_sorting_success(
            self,
            client: AsyncClient,
            path: str,
            sorting_field: str,
            earlier_obj: Any,
            later_obj: Any,
            *,
            lookup_field: str = "id"
    ) -> None:
        assert type(earlier_obj) is type(later_obj), (
            f"Types of objects don't match: {type(earlier_obj)} and {type(later_obj)}"
        )

        if lookup_field == "id" and sorting_field != "id":
            lookup_field = sorting_field.lstrip("-")

        expected_earlier = earlier_obj.get(lookup_field) if isinstance(earlier_obj, dict) else getattr(earlier_obj,
                                                                                                       lookup_field,
                                                                                                       None)
        expected_later = later_obj.get(lookup_field) if isinstance(later_obj, dict) else getattr(later_obj,
                                                                                                 lookup_field, None)

        assert expected_earlier is not None and expected_later is not None, \
            f"Lookup field '{lookup_field}' not found in test objects"
        assert str(expected_earlier) != str(
            expected_later), "Test objects must have different lookup values to verify sorting"

        is_desc = sorting_field.startswith("-")
        expected_value = expected_later if is_desc else expected_earlier

        item = await self._get_first_of_paginated(
            client=client,
            path=path,
            query_params={"order_by": sorting_field},
        )

        actual_value = item.get(lookup_field) if isinstance(item, dict) else getattr(item, lookup_field, None)
        assert actual_value is not None, f"API response item has no attribute/key '{lookup_field}'"

        if isinstance(expected_value, datetime) and isinstance(actual_value, str):
            try:
                comparison_actual = datetime.fromisoformat(actual_value)
            except ValueError:
                comparison_actual = actual_value
            comparison_expected = expected_value
        else:
            comparison_actual = str(actual_value)
            comparison_expected = str(expected_value)

        assert comparison_actual == comparison_expected, (
            f"Sorting failed for '{sorting_field}'. "
            f"Expected first item {lookup_field}={expected_value}, got {actual_value}"
        )

    def _first_of_paginated_response(self, resp: Response) -> dict:
        self._assert_status_code(resp, 200)

        data = resp.json()
        assert "results" in data, "Key 'results' not found in api response."

        results = data["results"]
        assert isinstance(results, list), "'results' must be a list."
        assert len(results) > 0, "'results' must not be empty."

        first_result = results[0]
        assert isinstance(first_result, dict), "First result must be a dict."

        return first_result

    def _count_of_paginated_response(self, resp: Response) -> int:
        self._assert_status_code(resp, 200)

        data = resp.json()
        assert "count" in data, "Key 'count' not found in api response."

        count = data["count"]
        assert isinstance(count, int), "'count' must be an integer."

        return count

    def _len_of_paginated_response(self, resp: Response) -> int:
        self._assert_status_code(resp, 200)

        data = resp.json()
        assert "count" in data, "Key 'count' not found in api response."

        results = data["results"]
        assert isinstance(results, list), "'results' must be an len."

        return len(results)

    async def _get_first_of_paginated(
            self,
            client: AsyncClient,
            path: str,
            query_params: dict | None = None
    ) -> dict:
        resp = await self._execute_and_assert_status_code(client, "GET", path, 200, query_params)
        return self._first_of_paginated_response(resp)

    async def _get_first_and_only_of_paginated(
            self,
            client: AsyncClient,
            path: str,
            query_params: dict | None = None
    ) -> dict:
        resp = await self._execute_and_assert_status_code(client, "GET", path, 200, query_params)

        count = self._count_of_paginated_response(resp)
        assert count == 1, (
            f"\n [ Expected Count Mismatch ] {resp.request.method} {resp.request.url}\n"
            f"Expected count: 1 | Actual count: {count}\n"
            f"Response body: {self._stringify_response_body(resp)}"
        )
        return self._first_of_paginated_response(resp)

    async def _assert_limit_applied(
            self,
            client: AsyncClient,
            path: str,
            limit: int,
    ) -> None:
        resp = await client.get(path, params={"limit": limit})
        actual_len = self._len_of_paginated_response(resp)
        assert actual_len == limit, (
            f"\n [ Expected Limit Mismatch ] {resp.request.method} {resp.request.url}\n"
            f"Expected limit: {limit} | Actual limit: {actual_len}\n"
            f"Response body: {self._stringify_response_body(resp)}"
        )

    async def _assert_offset_applied(
            self,
            client: AsyncClient,
            path: str,
            offset: int,
            lookup_value: Any,
            *,
            lookup_field: str = "id"
    ) -> None:
        item = await self._get_first_of_paginated(
            client=client,
            path=path,
            query_params={"offset": offset},
        )

        assert item.get(lookup_field) == lookup_value, (
            f"\n [ Expected Offset Mismatch ] GET {path}\n"
            f"Expected valued of field '{lookup_field}': {lookup_value} | Actual value: {item.get(lookup_field)}"
            f"Item in response: {item}"
        )
