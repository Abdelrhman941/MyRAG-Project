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
    """Reuse a safe upstream request ID or generate a new one."""
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
    """Attach request IDs and log request duration and outcome."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _resolve_request_id(request)

        request.state.request_id = request_id
        set_request_id(request_id)

        start = time.perf_counter()

        try:
            response = await call_next(request)

            logger.info(
                "%s %s -> %s in %.2f ms",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - start) * 1000,
            )

            response.headers["x-request-id"] = request_id
            return response

        except Exception:
            logger.exception(
                "%s %s failed after %.2f ms",
                request.method,
                request.url.path,
                (time.perf_counter() - start) * 1000,
            )
            raise

        finally:
            clear_request_id()
