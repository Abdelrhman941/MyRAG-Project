from enum import StrEnum


class Environment(StrEnum):
    """Application runtime environment."""

    LOCAL = "local"
    PRODUCTION = "production"
