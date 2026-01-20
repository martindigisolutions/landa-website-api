from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from jose import jwt, JWTError
import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from models import User, PasswordResetRequest
from schemas.auth import UserCreate, UserUpdate, ResetPasswordSchema
from config import SECRET_KEY, ALGORITHM, FRONTEND_RESET_URL, PASSWORD_RESET_MAX_REQUESTS_PER_HOUR, get_store_config
from utils import send_email
from security import create_reset_token

oauth2_scheme = None  # Defined in main auth.py for dependency injection

# OAuth2 scheme that doesn't auto-error (for optional auth)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against a hash using bcrypt directly.
    Returns False if hash format is invalid.
    """
    try:
        # Check if it's a valid bcrypt hash
        if not hashed or not hashed.startswith(('$2a$', '$2b$', '$2y$')):
            return False
        plain_bytes = plain.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        # Any error (invalid hash format, etc.) = invalid password
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=365))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def _validate_token_and_get_user(db: Session, token: str, raise_on_error: bool = True):
    """
    Internal helper to validate token and return user.
    
    Args:
        db: Database session
        token: JWT token string
        raise_on_error: If True, raises HTTPException on invalid token. If False, returns None.
    
    Returns:
        User object if valid, None if invalid and raise_on_error=False
    
    Raises:
        HTTPException 401/403 if invalid and raise_on_error=True
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get("sub")
        if not identifier:
            if raise_on_error:
                raise credentials_exception
            return None
    except JWTError:
        if raise_on_error:
            raise credentials_exception
        return None
    
    user = get_user_by_email_or_phone(db, identifier)
    if not user:
        if raise_on_error:
            raise credentials_exception
        return None
    
    # Check if user is blocked
    if user.is_blocked:
        if raise_on_error:
            raise HTTPException(
                status_code=403, 
                detail="Your account has been blocked. Please contact support."
            )
        return None
    
    # Check if user is suspended
    if user.is_suspended:
        if raise_on_error:
            raise HTTPException(
                status_code=403, 
                detail="Your account has been temporarily suspended. Please contact support."
            )
        return None
    
    return user


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Requires authentication. Raises 401 if not authenticated.
    Use for endpoints that require a logged-in user.
    """
    return _validate_token_and_get_user(db, token, raise_on_error=True)


def get_optional_user(
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme_optional)
):
    """
    Returns User if authenticated, None if not.
    Does NOT raise an exception for missing/invalid tokens.
    Use this for endpoints that work for both guests and logged-in users.
    """
    if not token:
        return None
    return _validate_token_and_get_user(db, token, raise_on_error=False)


def get_catalog_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme_optional)
):
    """
    Smart dependency for catalog endpoints (products, categories, brands).
    - Wholesale mode: requires authentication (raises 401 if not logged in)
    - Retail mode: returns User if logged in, None if guest
    """
    config = get_store_config()
    
    if config["require_auth_for_catalog"]:
        # Wholesale: must be authenticated
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view catalog",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _validate_token_and_get_user(db, token, raise_on_error=True)
    else:
        # Retail: optional auth
        if not token:
            return None
        return _validate_token_and_get_user(db, token, raise_on_error=False)


def get_cart_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme_optional)
):
    """
    Smart dependency for cart endpoints.
    - Wholesale mode: requires authentication
    - Retail mode: returns User if logged in, None if guest (uses session_id)
    """
    config = get_store_config()
    
    if config["require_auth_for_cart"]:
        # Wholesale: must be authenticated
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to manage cart",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return _validate_token_and_get_user(db, token, raise_on_error=True)
    else:
        # Retail: optional auth
        if not token:
            return None
        return _validate_token_and_get_user(db, token, raise_on_error=False)


def get_user_by_email_or_phone(db: Session, identifier: str):
    """Find user by email, phone, or whatsapp_phone"""
    return db.query(User).filter(
        or_(
            User.email == identifier, 
            User.phone == identifier,
            User.whatsapp_phone == identifier
        )
    ).first()

def authenticate_user(db: Session, identifier: str, password: str):
    user = get_user_by_email_or_phone(db, identifier)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def register_user(user: UserCreate, db: Session):
    if get_user_by_email_or_phone(db, user.email) or get_user_by_email_or_phone(db, user.phone):
        raise HTTPException(status_code=400, detail="Email or phone already registered")
    
    # Check whatsapp_phone if provided
    if user.whatsapp_phone:
        existing = db.query(User).filter(User.whatsapp_phone == user.whatsapp_phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="WhatsApp phone already registered")

    # Determine user_type: use provided value or default from STORE_CONFIG
    config = get_store_config()
    user_type = user.user_type if user.user_type else config["default_user_type"]
    
    hashed = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        whatsapp_phone=user.whatsapp_phone,
        email=user.email,
        birthdate=user.birthdate,
        user_type=user_type,
        registration_complete=True,
        hashed_password=hashed,
        password_last_updated=datetime.utcnow(),
        password_requires_update=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate access token so user is logged in immediately
    identifier = new_user.email or new_user.phone or new_user.whatsapp_phone
    access_token = create_access_token(data={"sub": identifier}, expires_delta=timedelta(days=365))
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
            "phone": new_user.phone,
            "whatsapp_phone": new_user.whatsapp_phone,
            "user_type": new_user.user_type,
            "registration_complete": new_user.registration_complete
        }
    }

def update_user_profile(user_id: int, updates: UserUpdate, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = updates.dict(exclude_unset=True)
    
    # Handle password separately - hash it and update related fields
    if "password" in update_data:
        password = update_data.pop("password")
        user.hashed_password = get_password_hash(password)
        user.password_last_updated = datetime.utcnow()
        user.password_requires_update = False  # Clear the flag once password is set
    
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return {"msg": "User updated successfully", "user": update_data}

def login_user(form_data, db: Session):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email/phone or password")

    # Check if user is blocked
    if user.is_blocked:
        raise HTTPException(
            status_code=403, 
            detail="Your account has been blocked. Please contact support."
        )
    
    # Check if user is suspended
    if user.is_suspended:
        raise HTTPException(
            status_code=403, 
            detail="Your account has been temporarily suspended. Please contact support."
        )

    # Use email, phone, or whatsapp_phone as identifier for token
    identifier = user.email or user.phone or user.whatsapp_phone
    access_token = create_access_token(data={"sub": identifier}, expires_delta=timedelta(days=365))

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "whatsapp_phone": user.whatsapp_phone,
            "user_type": user.user_type,
            "registration_complete": user.registration_complete
        }
    }


def request_password_reset(email: str, db: Session):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count recent reset attempts within the past hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_attempts = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id == user.id,
        PasswordResetRequest.created_at >= one_hour_ago
    ).count()

    if recent_attempts >= PASSWORD_RESET_MAX_REQUESTS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"You can request a password reset only {PASSWORD_RESET_MAX_REQUESTS_PER_HOUR} times per hour."
        )
    db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id == user.id,
        PasswordResetRequest.used == False
    ).update({"used": True})

    token = create_reset_token({"user_id": user.id})
    reset_link = f"{FRONTEND_RESET_URL}{token}"

    request = PasswordResetRequest(user_id=user.id, token=token)
    db.add(request)
    db.commit()

    html_body = f"""
        <html>
        <body>
            <p>Hello,</p>
            <p>You requested a password reset. Click the link below to reset your password:</p>
            <p><a href=\"{reset_link}\">Reset Password</a></p>
            <p>If you did not request this, please ignore this email.</p>
        </body>
        </html>
    """
    send_email(email, "Password Reset", html_body)

    return {"msg": "Reset link sent"}

def reset_password(data: ResetPasswordSchema, db: Session):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        exp_timestamp = payload.get("exp")
        if user_id is None or exp_timestamp is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    reset_entry = db.query(PasswordResetRequest).filter_by(token=data.token).first()
    if not reset_entry or reset_entry.used:
        raise HTTPException(status_code=400, detail="This reset link is invalid or already used.")

    if datetime.utcnow().timestamp() > exp_timestamp:
        raise HTTPException(status_code=400, detail="Token has expired.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(data.new_password)
    user.password_last_updated = datetime.utcnow()
    user.password_requires_update = False  # Clear the flag
    db.add(user)

    reset_entry.used = True
    db.add(reset_entry)

    db.commit()

    return {"msg": "Password reset successful"}

def get_user_by_id(user_id: int, current_user: User, db: Session):
    if current_user.user_type != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=403, detail="You are not authorized to access this user's information."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _user_to_response(user)


def _user_to_response(user: User) -> dict:
    """Convert User model to response dict with computed fields"""
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "whatsapp_phone": user.whatsapp_phone,
        "email": user.email,
        "birthdate": user.birthdate,
        "user_type": user.user_type,
        "registration_complete": user.registration_complete,
        "created_at": user.created_at,
        # Password status - computed fields
        "has_password": user.hashed_password is not None and len(user.hashed_password) > 0,
        "password_requires_update": user.password_requires_update or False,
        "password_last_updated": user.password_last_updated,
    }

