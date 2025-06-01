from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from models import User, PasswordResetRequest
from schemas import UserCreate, UserUpdate, ResetPasswordSchema
from config import SECRET_KEY, ALGORITHM, FRONTEND_RESET_URL, PASSWORD_RESET_MAX_REQUESTS_PER_HOUR
from utils import send_email
from security import create_reset_token

oauth2_scheme = None  # Defined in main auth.py for dependency injection
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

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
    return user

def get_user_by_email_or_phone(db: Session, identifier: str):
    return db.query(User).filter(or_(User.email == identifier, User.phone == identifier)).first()

def authenticate_user(db: Session, identifier: str, password: str):
    user = get_user_by_email_or_phone(db, identifier)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def register_user(user: UserCreate, db: Session):
    if get_user_by_email_or_phone(db, user.email) or get_user_by_email_or_phone(db, user.phone):
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    hashed = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        birthdate=user.birthdate,
        user_type=user.user_type,
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
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return {"msg": "User updated successfully", "user": update_data}

def login_user(form_data, db: Session):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email/phone or password")
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(days=365))
    return {"access_token": access_token, "token_type": "bearer"}

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
