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
async def readyz(request: Request, response: Response) -> dict[str, str]:
    """Readiness probe checking model load status and Qdrant."""
    error = getattr(request.app.state, "model_error", None)
    if error:
        response.status_code = 503
        return {"status": "error", "detail": error}

    is_ready = getattr(request.app.state, "model_ready", False)
    if not is_ready:
        response.status_code = 503
        return {"status": "warming"}

    try:
        vs = request.app.state.vector_store
        exists = await vs.client.collection_exists(vs.collection_name)
        if not exists:
            response.status_code = 503
            return {"status": "qdrant_not_ready"}
    except Exception as e:
        response.status_code = 503
        return {"status": "qdrant_error", "detail": str(e)}

    return {"status": "ready"}


@system_router.get("/api/v1/system/config")
def config(settings: SettingsDep) -> dict:
    from ..core.enums.document import DocumentType

    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_files_per_request": settings.MAX_FILES_PER_REQUEST,
        "accepted_extensions": [t.extension for t in DocumentType],
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
    }
