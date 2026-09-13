from typing import Any

from fastapi import APIRouter

from ...core.enums.document import DocumentType
from ...dependencies import SettingsDep

system_router = APIRouter(
    tags=["System"],
)


@system_router.get("/config")
def config(
    settings: SettingsDep,
) -> dict[str, Any]:
    """Return public application configuration."""
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_files_per_request": settings.MAX_FILES_PER_REQUEST,
        "accepted_extensions": [
            document_type.extension for document_type in DocumentType
        ],
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "max_question_length": settings.MAX_QUESTION_LENGTH,
    }
