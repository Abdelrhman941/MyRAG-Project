from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .core import Settings, get_settings
from .infrastructure import (
    DocumentStorage,
    FileStoragePort,
    LLMProviderPort,
    QdrantVectorStore,
    SessionRepositoryPort,
    VectorStorePort,
)
from .infrastructure import get_db as _get_db
from .retrieval.service import RetrievalService
from .services.chat_service import ChatService

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
def get_storage() -> FileStoragePort:
    return DocumentStorage()


type StorageDep = Annotated[
    FileStoragePort,
    Depends(get_storage),
]


# -------- Vector Store --------
def get_vector_store(settings: SettingsDep) -> VectorStorePort:
    return QdrantVectorStore(settings)


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


# -------- LLM Provider --------
def get_llm_provider(settings: SettingsDep) -> LLMProviderPort:
    from .infrastructure import OpenAICompatibleLLM

    return OpenAICompatibleLLM(settings)


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
