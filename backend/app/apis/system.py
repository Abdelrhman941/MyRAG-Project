# app/apis/system.py
from fastapi import APIRouter, Request, Response

from ..dependencies import SettingsDep

system_router = APIRouter(tags=["System"])


@system_router.get("/")
def root(settings: SettingsDep) -> dict[str, str]:
    """Return basic application metadata."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
    }


@system_router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@system_router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, str]:
    """Readiness probe checking model load status."""
    error = getattr(request.app.state, "model_error", None)
    if error:
        response.status_code = 503
        return {"status": "error", "detail": error}

    is_ready = getattr(request.app.state, "model_ready", False)
    if not is_ready:
        response.status_code = 503
        return {"status": "warming"}

    return {"status": "ready"}
