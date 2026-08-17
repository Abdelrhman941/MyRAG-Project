from typing import Annotated

from fastapi import Depends

from .core import Settings, get_settings

# -------- App-Settings --------
SettingsDep = Annotated[
    Settings,
    Depends(get_settings),
]
