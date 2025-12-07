from pydantic import BaseModel


class OAuth2TokenRequest(BaseModel):
    """OAuth2 Client Credentials token request"""
    grant_type: str
    client_id: str
    client_secret: str


class OAuth2TokenResponse(BaseModel):
    """OAuth2 token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str

