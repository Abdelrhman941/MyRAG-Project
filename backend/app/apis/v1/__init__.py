from fastapi import APIRouter

from . import documents

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(documents.router)
