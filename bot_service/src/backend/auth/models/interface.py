from datetime import datetime

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class TokenData(PydanticBaseModel):
    """Data model for token information."""

    username: str | None = None
    scopes: list[str] = []
