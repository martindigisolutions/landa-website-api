"""
Orders router - Primary endpoint for order creation with lock system
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from jose import jwt, JWTError

from database import get_db
from models import User
from config import SECRET_KEY, ALGORITHM
from services import checkout_service
from schemas.checkout import OrderCreate

router = APIRouter(prefix="/orders", tags=["Orders"])

# Optional OAuth2 scheme (doesn't auto-raise 401)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Optional[str]:
    """Extract session ID from header"""
    return x_session_id


def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get("sub")
        if not identifier:
            return None
        
        user = db.query(User).filter(
            or_(
                User.email == identifier,
                User.phone == identifier,
                User.whatsapp_phone == identifier
            )
        ).first()
        
        if not user or user.is_blocked or user.is_suspended:
            return None
        
        return user
    except JWTError:
        return None


@router.post(
    "",
    summary="Create order with lock token",
    description="""
    Create an order using a valid lock token.
    
    **Flow:**
    1. Call POST /cart/lock to reserve stock
    2. Process payment (Stripe/Zelle)
    3. Call POST /orders with lock_token
    
    **Request Body:**
    - `lock_token`: Token from POST /cart/lock (required)
    - `payment_id`: Stripe payment ID (optional, for confirmation)
    
    **Response:**
    - `success`: true/false
    - `order_id`: Created order ID
    - `order_number`: Human-readable order number
    - `status`: Order status ("paid" for Stripe, "pending_verification" for Zelle)
    
    **Errors:**
    - `lock_expired`: Lock timed out, need to create new lock
    - `lock_already_used`: Lock was already used
    - `lock_not_found`: Invalid lock token
    """
)
def create_order(
    data: OrderCreate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return checkout_service.create_order(data, session_id, user, db)
