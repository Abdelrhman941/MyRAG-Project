from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Final, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.exceptions import AppError

logger = logging.getLogger(__name__)


HTTP_STATUS_ERROR_CODES: Final[dict[int, str]] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable_entity",
    429: "rate_limit_exceeded",
    500: "internal_server_error",
    501: "not_implemented",
    502: "bad_gateway",
    503: "service_unavailable",
    504: "gateway_timeout",
}


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build the standard API error response.

    Uses request.state (not the logging contextvar) for request_id, since
    request.state is available in all exception handlers.
    """

    error: dict[str, Any] = {"code": code, "message": message}

    if details:
        error["details"] = details

    request_id = getattr(request.state, "request_id", None)
    if request_id:
        error["request_id"] = request_id

    response_headers = dict(headers) if headers else {}
    if request_id:
        response_headers["x-request-id"] = request_id

    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers=response_headers or None,
    )


def _get_http_error_code(status_code: int) -> str:
    """Return a stable API error code for an HTTP status."""

    return HTTP_STATUS_ERROR_CODES.get(status_code, "http_error")


def _safe_http_detail(detail: Any) -> str:
    """Return a safe client-facing HTTP error message."""

    if isinstance(detail, str):
        return detail

    return "An HTTP error occurred."


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Normalize Starlette/FastAPI HTTP exceptions."""

    http_exception = cast(StarletteHTTPException, exc)

    if http_exception.status_code >= 500:
        logger.error(
            "HTTP exception",
            exc_info=http_exception,
            extra={
                "event": "api.http_exception",
                "status_code": http_exception.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )

    return _error_response(
        request=request,
        status_code=http_exception.status_code,
        code=_get_http_error_code(http_exception.status_code),
        message=_safe_http_detail(http_exception.detail),
        headers=http_exception.headers,
    )


async def request_validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Translate request validation errors into a consistent response."""

    validation_error = cast(RequestValidationError, exc)

    details = [
        {
            "type": error.get("type"),
            "location": list(error.get("loc", ())),
            "message": error.get("msg"),
        }
        for error in validation_error.errors()
    ]

    logger.warning(
        "Request validation failed",
        extra={
            "event": "api.validation_error",
            "path": request.url.path,
            "method": request.method,
        },
    )

    return _error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe response for unexpected failures.

    No logging here — RequestLoggingMiddleware already logs the full
    traceback with method/path/duration before this handler runs
    (it sits inside the middleware, this handler runs in ServerErrorMiddleware,
    outside it). Logging here too would duplicate every 500 in the logs.
    """

    return _error_response(
        request=request,
        status_code=500,
        code="internal_server_error",
        message="An unexpected error occurred.",
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Normalize application-domain errors into the standard response."""

    if exc.status_code >= 500:
        logger.error(
            "Application error",
            exc_info=exc,
            extra={
                "event": "api.app_error",
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )
    else:
        logger.warning(
            "Application error",
            extra={
                "event": "api.app_error",
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )

    return _error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all application-wide exception handlers."""

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_exception_handler
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
