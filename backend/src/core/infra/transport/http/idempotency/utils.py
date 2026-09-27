import json
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import Response


def get_idempotency_key(request: Request) -> str | None:
    raw_key = request.headers.get("idempotency-key")
    if not raw_key:
        return None

    cleaned_key = str(raw_key).strip()
    if cleaned_key.lower() in ("", "none", "null"):
        return None

    return cleaned_key


def get_idempotency_cache_key(idempotency_key: str) -> str:
    return f"idempotency:{idempotency_key}"


def get_idempotency_lock_key(cache_key: str) -> str:
    return f"lock:{cache_key}"


def serialize_to_json(data: Any) -> str:
    return json.dumps(jsonable_encoder(data))


def _extract_request(*args: Any, **kwargs: Any) -> Request | None:
    return kwargs.get("request") or next(
        (arg for arg in args if isinstance(arg, Request)), None
    )


def _extract_response_arg(*args: Any, **kwargs: Any) -> Response | None:
    return kwargs.get("response") or next(
        (arg for arg in args if isinstance(arg, Response)), None
    )


def _resolve_status_code(response: Any, request: Request, *args: Any, **kwargs: Any) -> int:
    if isinstance(response, Response):
        return response.status_code

    response_arg = _extract_response_arg(*args, **kwargs)
    if response_arg is not None:
        return response_arg.status_code

    route = request.scope.get("route")
    if route is not None and getattr(route, "status_code", None) is not None:
        return route.status_code

    return status.HTTP_200_OK


def _prepare_cache_payload(response: Any, status_code: int) -> str:
    content = serialize_to_json(response) if not isinstance(response, Response) else response.body.decode("utf-8")
    return json.dumps({"status_code": status_code, "content": content})


def _restore_response(cached_str: str) -> Response:
    data = json.loads(cached_str)
    return Response(
        content=data["content"],
        status_code=data["status_code"],
        media_type="application/json"
    )


def _should_cache(status_code: int) -> bool:
    return status.HTTP_200_OK <= status_code < status.HTTP_300_MULTIPLE_CHOICES
