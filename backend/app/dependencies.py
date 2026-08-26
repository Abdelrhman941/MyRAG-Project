from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .core import Settings, get_settings
from .infrastructure import (
    DocumentStorage,
    FileStoragePort,
    QdrantVectorStore,
    VectorStorePort,
)
from .infrastructure import get_db as _get_db

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
