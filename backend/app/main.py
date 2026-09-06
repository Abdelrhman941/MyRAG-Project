from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .apis import api_v1_router, health_router, register_exception_handlers
from .core import (
    Environment,
    RequestLoggingMiddleware,
    Settings,
    get_settings,
    limiter,
    setup_logging,
)
from .embeddings.model import get_embedding_model
from .infrastructure import DocumentStorage, build_vector_store

logger = logging.getLogger(__name__)


async def _close_vector_store(app: FastAPI) -> None:
    """Close the vector-store client when the adapter exposes an async close."""
    vector_store = getattr(app.state, "vector_store", None)
    if vector_store is None:
        return

    client = getattr(vector_store, "client", None)
    close = getattr(client, "close", None)

    if close is None:
        return

    try:
        result = close()
        if result is not None:
            await result
    except Exception:
        logger.exception("Failed to close vector store client")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize application resources and release them on shutdown."""
    settings: Settings = app.state.settings

    app.state.http_client = httpx.AsyncClient()
    app.state.document_storage = DocumentStorage()
    app.state.vector_store = build_vector_store(settings)

    app.state.model_ready = False
    app.state.model_error = None

    def _load_model() -> None:
        get_embedding_model(settings.EMBEDDING_MODEL)

    def _model_loaded(task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception as exc:
            app.state.model_ready = False
            app.state.model_error = str(exc)
            logger.exception("Failed to load embedding model")
        else:
            app.state.model_ready = True
            app.state.model_error = None
            logger.info(
                "Embedding model loaded successfully",
                extra={"event": "embedding.model_ready"},
            )

    model_load_task = asyncio.create_task(asyncio.to_thread(_load_model))
    model_load_task.add_done_callback(_model_loaded)
    app.state.model_load_task = model_load_task

    from arq import create_pool
    from arq.connections import RedisSettings

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    try:
        app.state.arq_pool = await create_pool(redis_settings)
        logger.info("ARQ Redis pool connected")
    except Exception:
        app.state.arq_pool = None
        logger.exception("Failed to create ARQ Redis pool")

    try:
        await app.state.vector_store.ensure_collection()
        logger.info("Vector store collection is ready")
    except Exception:
        logger.exception("Failed to ensure vector store collection")

    try:
        yield
    finally:
        logger.info("Application shutdown started")

        model_task: asyncio.Task[None] | None = getattr(
            app.state,
            "model_load_task",
            None,
        )
        if model_task is not None and not model_task.done():
            model_task.cancel()
            with suppress(asyncio.CancelledError):
                await model_task

        arq_pool = getattr(app.state, "arq_pool", None)
        if arq_pool is not None:
            try:
                await arq_pool.close()
            except Exception:
                logger.exception("Failed to close ARQ Redis pool")

        await _close_vector_store(app)

        http_client = getattr(app.state, "http_client", None)
        if http_client is not None:
            try:
                await http_client.aclose()
            except Exception:
                logger.exception("Failed to close HTTP client")

        logger.info("Application shutdown complete")


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

    app.state.settings = settings
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
