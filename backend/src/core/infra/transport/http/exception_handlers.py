from typing import Any, Callable, Coroutine

from fastapi import Request
from fastapi.responses import JSONResponse


def _build_error_content(exc: Exception) -> dict[str, Any]:
    content = {"detail": str(exc)}
    extra = getattr(exc, "extra", None)
    if extra:
        content["extra"] = extra
    return content


def create_exception_handler(
        status_code: int,
) -> Callable[[Request, Exception], Coroutine[Any, Any, JSONResponse]]:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content=_build_error_content(exc)
        )

    return handler
