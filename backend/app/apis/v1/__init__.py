from fastapi import APIRouter

from . import chat, documents

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(chat.router)
api_v1_router.include_router(documents.router)
