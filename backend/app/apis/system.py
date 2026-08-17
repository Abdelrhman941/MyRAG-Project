# app/apis/system.py
from fastapi import APIRouter

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
