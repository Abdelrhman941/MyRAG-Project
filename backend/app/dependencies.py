from __future__ import annotations

from typing import Annotated, cast
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .core import Settings, get_settings
from .core.exceptions import NotFoundError, QueueUnavailableError
from .infrastructure import (
    FileStoragePort,
    LLMProviderPort,
    SessionRepositoryPort,
    VectorStorePort,
)
from .infrastructure import get_db as _get_db
from .infrastructure.ports import SessionData
from .retrieval.service import RetrievalService
from .services import ChatService, DocumentService

# -------- App Settings --------
type SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]


# -------- Database --------
type SessionDep = Annotated[
    AsyncSession,
    Depends(_get_db),
]


# -------- Storage --------
def get_storage(request: Request) -> FileStoragePort:
    """Return the application document-storage adapter."""
    return cast(
        FileStoragePort,
        request.app.state.document_storage,
    )


type StorageDep = Annotated[
    FileStoragePort,
    Depends(get_storage),
]


# -------- Vector Store --------
def get_vector_store(request: Request) -> VectorStorePort:
    """Return the application vector-store adapter."""
    return cast(
        VectorStorePort,
        request.app.state.vector_store,
    )


type VectorStoreDep = Annotated[
    VectorStorePort,
    Depends(get_vector_store),
]


# -------- Chat Sessions --------
def get_session_repository(
    session: SessionDep,
) -> SessionRepositoryPort:
    """Build the session repository for the current database session."""
    from .infrastructure import SqliteSessionRepository

    return SqliteSessionRepository(session)


type SessionRepositoryDep = Annotated[
    SessionRepositoryPort,
    Depends(get_session_repository),
]


async def get_session_or_404(
    session_id: UUID,
    repository: SessionRepositoryDep,
) -> SessionData:
    """Return a session or raise a not-found error."""
    session = await repository.get_session(session_id)

    if session is None:
        raise NotFoundError(
            message=f"Session {session_id} not found",
        )

    return session


type ValidSessionDep = Annotated[
    SessionData,
    Depends(get_session_or_404),
]


# -------- LLM Provider --------
def get_llm_provider(
    request: Request,
    settings: SettingsDep,
) -> LLMProviderPort:
    """Build the configured LLM provider adapter."""
    from .infrastructure import OpenAICompatibleLLM

    return OpenAICompatibleLLM(
        settings,
        cast(object, request.app.state.http_client),  # type: ignore[arg-type]
    )


type LLMProviderDep = Annotated[
    LLMProviderPort,
    Depends(get_llm_provider),
]


# -------- Retrieval Service --------
def get_retrieval_service(
    vector_store: VectorStoreDep,
    settings: SettingsDep,
) -> RetrievalService:
    """Build the retrieval service."""
    return RetrievalService(
        vector_store,
        settings,
    )


type RetrievalServiceDep = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


# -------- ARQ Background Jobs --------
def get_arq_pool(request: Request) -> ArqRedis:
    """Return the ARQ pool or fail with a service-unavailable error."""
    pool = getattr(
        request.app.state,
        "arq_pool",
        None,
    )

    if pool is None:
        raise QueueUnavailableError()

    return cast(ArqRedis, pool)


type ArqPoolDep = Annotated[
    ArqRedis,
    Depends(get_arq_pool),
]


# -------- Document Service --------
def get_document_service(
    session: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
    vector_store: VectorStoreDep,
) -> DocumentService:
    """Build the document service."""
    return DocumentService(
        session,
        storage,
        settings,
        vector_store,
    )


type DocumentServiceDep = Annotated[
    DocumentService,
    Depends(get_document_service),
]


# -------- Chat Service --------
def get_chat_service(
    repository: SessionRepositoryDep,
    retrieval_service: RetrievalServiceDep,
    llm: LLMProviderDep,
    settings: SettingsDep,
) -> ChatService:
    """Build the chat service."""
    return ChatService(
        repository,
        retrieval_service,
        llm,
        settings,
    )


type ChatServiceDep = Annotated[
    ChatService,
    Depends(get_chat_service),
]


__all__ = [
    "ArqPoolDep",
    "ChatServiceDep",
    "DocumentServiceDep",
    "LLMProviderDep",
    "RetrievalServiceDep",
    "SessionDep",
    "SessionRepositoryDep",
    "SettingsDep",
    "StorageDep",
    "ValidSessionDep",
    "VectorStoreDep",
]
