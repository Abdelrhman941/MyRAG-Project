from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .core import Settings, get_settings
from .infrastructure import DocumentStorage
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
def get_storage() -> DocumentStorage:
    return DocumentStorage()


type StorageDep = Annotated[
    DocumentStorage,
    Depends(get_storage),
]
