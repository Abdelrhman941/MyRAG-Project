# app/main.py
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

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

    yield


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

    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(base_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
