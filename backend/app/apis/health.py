from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..dependencies import SettingsDep

health_router = APIRouter(tags=["health"])


@health_router.get("/")
def root(settings: SettingsDep) -> dict[str, str]:
    """Return basic application metadata."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
    }


@health_router.get("/healthz")
def healthz() -> dict[str, str]:
    """Return liveness status."""
    return {"status": "ok"}


@health_router.get("/readyz")
async def readyz(
    request: Request,
    response: Response,
) -> dict[str, str]:
    """Return readiness status for required runtime dependencies."""
    model_error = getattr(
        request.app.state,
        "model_error",
        None,
    )

    if model_error:
        response.status_code = 503
        # Include the detail so the client (splash screen) can show the
        # actual failure reason instead of a generic error.
        return {"status": "error", "detail": str(model_error)}

    if not getattr(
        request.app.state,
        "model_ready",
        False,
    ):
        response.status_code = 503
        return {"status": "warming"}

    try:
        vector_store = request.app.state.vector_store

        exists = await vector_store.client.collection_exists(
            vector_store.collection_name,
        )

        if not exists:
            response.status_code = 503
            return {"status": "qdrant_not_ready"}

    except Exception as exc:
        response.status_code = 503
        return {"status": "qdrant_unavailable", "detail": str(exc)}

    return {"status": "ready"}
