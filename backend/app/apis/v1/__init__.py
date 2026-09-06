from fastapi import APIRouter

from . import chat, documents
from .system import system_router

api_v1_router = APIRouter(
    prefix="/api/v1",
)

api_v1_router.include_router(chat.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(
    system_router,
    prefix="/system",
)

__all__ = ["api_v1_router"]
