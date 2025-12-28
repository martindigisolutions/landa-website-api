from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from models import User, PasswordResetRequest
from schemas.auth import UserCreate, UserUpdate, ResetPasswordSchema
from config import SECRET_KEY, ALGORITHM, FRONTEND_RESET_URL, PASSWORD_RESET_MAX_REQUESTS_PER_HOUR
from utils import send_email
from security import create_reset_token

oauth2_scheme = None  # Defined in main auth.py for dependency injection
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against a hash.
    Returns False if hash format is invalid (e.g., SHA256 from temp passwords).
    """
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        # Hash format not recognized (e.g., SHA256 from single access token users)
        # These users should login via their access link, not regular login
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=365))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get("sub")
        if not identifier:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email_or_phone(db, identifier)
    if not user:
        raise credentials_exception
    
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
    
    return user

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

    hashed = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        whatsapp_phone=user.whatsapp_phone,
        email=user.email,
        birthdate=user.birthdate,
        user_type=user.user_type,
        registration_complete=True,
        hashed_password=hashed
    )
    db.add(new_user)
    db.commit()
    return {"msg": "User created successfully"}

def update_user_profile(user_id: int, updates: UserUpdate, db: Session):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = updates.dict(exclude_unset=True)
    
    # Handle password separately - hash it and use the correct field name
    if "password" in update_data:
        password = update_data.pop("password")
        user.hashed_password = get_password_hash(password)
    
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

    return user

