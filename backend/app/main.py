from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .apis import (
    api_v1_router,
    health_router,
    register_exception_handlers,
)
from .core import (
    RequestLoggingMiddleware,
    Settings,
    get_settings,
    limiter,
    setup_logging,
)
from .embeddings import get_embedding_model
from .infrastructure import DocumentStorage, build_vector_store
from .infrastructure.db.session import dispose_engine

logger = logging.getLogger(__name__)


async def _close_vector_store(app: FastAPI) -> None:
    """Close the application-owned vector store client."""
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
    """Initialize and release application-wide resources."""
    settings: Settings = app.state.settings

    # Runtime initialization.
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Fail-loud (but not fatal) on a missing LLM key: the server still boots
    # so /readyz works, but the operator immediately sees why chat fails
    # instead of discovering it via a 401/502 on the first message.
    if not settings.LLM_API_KEY:
        logger.warning(
            "LLM_API_KEY is empty — every chat request will fail with an "
            "LLM provider error. Set LLM_API_KEY in backend/.env."
        )

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
            app.state.model_error = str(exc)

            logger.exception(
                "Failed to load embedding model",
            )

        else:
            app.state.model_ready = True
            app.state.model_error = None

            logger.info("Embedding model ready")

    model_load_task = asyncio.create_task(
        asyncio.to_thread(_load_model),
    )
    model_load_task.add_done_callback(_model_loaded)
    app.state.model_load_task = model_load_task

    redis_settings = RedisSettings.from_dsn(
        settings.REDIS_URL,
    )

    try:
        app.state.arq_pool = await create_pool(
            redis_settings,
        )
        logger.info("ARQ Redis pool connected")

    except Exception:
        app.state.arq_pool = None
        logger.exception("Failed to connect to ARQ Redis")

    try:
        await app.state.vector_store.ensure_collection()
        logger.info("Vector store collection is ready")

    except Exception:
        logger.exception(
            "Failed to initialize vector store collection",
        )

    try:
        yield

    finally:
        logger.info("Application shutdown started")

        task_to_cancel = getattr(
            app.state,
            "model_load_task",
            None,
        )

        if task_to_cancel is not None and not task_to_cancel.done():
            task_to_cancel.cancel()

            with suppress(asyncio.CancelledError):
                await task_to_cancel

        arq_pool = getattr(
            app.state,
            "arq_pool",
            None,
        )

        if arq_pool is not None:
            try:
                arq_pool.close()
                await arq_pool.wait_closed()
            except Exception:
                logger.exception(
                    "Failed to close ARQ Redis pool",
                )

        await _close_vector_store(app)

        http_client = getattr(
            app.state,
            "http_client",
            None,
        )

        if http_client is not None:
            try:
                await http_client.aclose()
            except Exception:
                logger.exception(
                    "Failed to close HTTP client",
                )

        await dispose_engine()

        logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()

    setup_logging()

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

    app.add_middleware(
        RequestLoggingMiddleware,
    )

    app.include_router(health_router)
    app.include_router(api_v1_router)

    register_exception_handlers(app)

    return app


app = create_app()
