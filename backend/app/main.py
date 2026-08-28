# app/main.py
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .apis import (
    api_v1_router,
    base_router,
    register_exception_handlers,
)
from .core import (
    Environment,
    RequestLoggingMiddleware,
    Settings,
    get_settings,
    limiter,
    setup_logging,
)
from .embeddings.model import get_embedding_model
from .infrastructure import DocumentStorage, QdrantVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()

    app.state.http_client = httpx.AsyncClient()
    app.state.document_storage = DocumentStorage()
    app.state.vector_store = QdrantVectorStore(settings)

    def _load_model() -> None:
        get_embedding_model(settings.EMBEDDING_MODEL)

    def _model_loaded(task: asyncio.Task[None]) -> None:
        try:
            task.result()
            app.state.model_ready = True
            app.state.model_error = None
        except Exception as e:
            app.state.model_ready = False
            app.state.model_error = str(e)
            logging.getLogger(__name__).error(f"Failed to load embedding model: {e}")

    app.state.model_ready = False
    app.state.model_error = None

    task = asyncio.create_task(asyncio.to_thread(_load_model))
    task.add_done_callback(_model_loaded)

    app.state.model_load_task = task

    from arq import create_pool
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    app.state.arq_pool = await create_pool(redis_settings)

    yield

    await app.state.http_client.aclose()
    if hasattr(app.state.vector_store, "client") and hasattr(
        app.state.vector_store.client, "close"
    ):
        await app.state.vector_store.client.close()

    if hasattr(app.state, "arq_pool"):
        await app.state.arq_pool.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    setup_logging(
        json_logs=settings.ENVIRONMENT is Environment.PRODUCTION,
        noisy_loggers={"transformers": logging.WARNING},
    )

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    # Note: allow_credentials=True + allow_origins=["*"] is spec-invalid.
    # CORS_ORIGINS must remain an explicit whitelist.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(base_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
