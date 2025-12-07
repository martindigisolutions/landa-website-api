from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from services import admin_service
from schemas.oauth import OAuth2TokenResponse

router = APIRouter(prefix="/oauth", tags=["OAuth2"])


@router.post(
    "/token",
    response_model=OAuth2TokenResponse,
    summary="Get access token",
    description="Exchange client credentials for an access token. Use grant_type=client_credentials."
)
def get_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    OAuth2 Client Credentials flow.
    
    **Request body (form-urlencoded):**
    - grant_type: Must be "client_credentials"
    - client_id: Your application's client_id
    - client_secret: Your application's client_secret
    
    **Response:**
    - access_token: JWT token to use in Authorization header
    - token_type: "Bearer"
    - expires_in: Token lifetime in seconds
    - scope: Space-separated list of granted scopes
    """
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=400,
            detail="Invalid grant_type. Must be 'client_credentials'"
        )
    
    # Authenticate the application
    app = admin_service.authenticate_application(client_id, client_secret, db)
    
    # Create access token
    access_token, expires_in = admin_service.create_app_access_token(app)
    
    return OAuth2TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=expires_in,
        scope=" ".join(app.scopes or [])
    )

