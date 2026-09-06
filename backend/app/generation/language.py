from __future__ import annotations

import re
from enum import StrEnum


class PromptLanguage(StrEnum):
    """Supported prompt languages."""

    AR = "ar"
    EN = "en"


_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> PromptLanguage:
    """Detect whether text is primarily Arabic or Latin-script English."""
    arabic_count = len(_ARABIC_RE.findall(text))
    latin_count = len(_LATIN_RE.findall(text))

    if arabic_count > latin_count:
        return PromptLanguage.AR

    return PromptLanguage.EN
