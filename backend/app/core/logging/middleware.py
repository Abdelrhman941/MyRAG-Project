from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .context import clear_request_id, set_request_id

logger = logging.getLogger("app.request")

_MAX_REQUEST_ID_LENGTH = 64


def _resolve_request_id(request: Request) -> str:
    """Reuse an upstream x-request-id only if it looks safe, else generate one."""

    candidate = request.headers.get("x-request-id")
    if (
        candidate
        and len(candidate) <= _MAX_REQUEST_ID_LENGTH
        and candidate.isascii()
        and candidate.isprintable()
    ):
        return candidate
    return str(uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every incoming HTTP request and its outcome.

    Resolves or generates a request ID, stores it in request.state and
    logging context, measures request duration, logs success/failure,
    and returns the request ID in the response header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = _resolve_request_id(request)
        request.state.request_id = request_id
        set_request_id(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
            raise
        else:
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
            response.headers["x-request-id"] = request_id
            return response
        finally:
            clear_request_id()
