from typing import Annotated, Any, cast
from uuid import UUID

from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .core import Settings, get_settings
from .core.exceptions import NotFoundError
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

# -------- App-Settings --------
type SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]

# -------- DB --------
type SessionDep = Annotated[
    AsyncSession,
    Depends(_get_db),
]


# -------- Storage --------
def get_storage(request: Request) -> FileStoragePort:
    return cast(FileStoragePort, request.app.state.document_storage)


type StorageDep = Annotated[
    FileStoragePort,
    Depends(get_storage),
]


# -------- Vector Store --------
def get_vector_store(request: Request) -> VectorStorePort:
    return cast(VectorStorePort, request.app.state.vector_store)


type VectorStoreDep = Annotated[
    VectorStorePort,
    Depends(get_vector_store),
]


# -------- Chat Sessions --------
def get_session_repository(session: SessionDep) -> SessionRepositoryPort:
    from .infrastructure import SqliteSessionRepository

    return SqliteSessionRepository(session)


type SessionRepositoryDep = Annotated[
    SessionRepositoryPort,
    Depends(get_session_repository),
]


async def get_session_or_404(
    session_id: UUID, repository: SessionRepositoryDep
) -> SessionData:
    """Verify session exists and return it, or raise 404."""

    session = await repository.get_session(session_id)
    if not session:
        raise NotFoundError(message=f"Session {session_id} not found")
    return session


type ValidSessionDep = Annotated[
    SessionData,
    Depends(get_session_or_404),
]


# -------- LLM Provider --------
def get_llm_provider(request: Request, settings: SettingsDep) -> LLMProviderPort:
    from .infrastructure import OpenAICompatibleLLM

    return OpenAICompatibleLLM(settings, cast(Any, request.app.state.http_client))


type LLMProviderDep = Annotated[
    LLMProviderPort,
    Depends(get_llm_provider),
]


# -------- Retrieval Service --------
def get_retrieval_service(
    vector_store: VectorStoreDep, settings: SettingsDep
) -> RetrievalService:
    return RetrievalService(vector_store, settings)


type RetrievalServiceDep = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


# -------- ARQ Background Jobs --------
def get_arq_pool(request: Request) -> ArqRedis:
    return cast(ArqRedis, request.app.state.arq_pool)


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

    return DocumentService(session, storage, settings, vector_store)


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

    return ChatService(repository, retrieval_service, llm, settings)


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
