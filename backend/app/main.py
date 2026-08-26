# app/main.py
from __future__ import annotations

import logging

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
    )

    app.state.limiter = limiter

    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    app.include_router(base_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
