from pydantic import BaseModel as PydanticBaseModel


class Token(PydanticBaseModel):
    access_token: str | None = None
    token_type: str | None = None
    exp: int | None = None
    id_token: str | None = None
    refresh_token: str | None = None
    refresh_token_id: str | None = None
    scope: str | None = None
    token_type: str | None = None
    userId: str | None = None


class RefreshTokenRequest(PydanticBaseModel):
    refresh_token: str
