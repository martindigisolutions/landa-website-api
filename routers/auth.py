from fastapi import Depends, HTTPException, APIRouter, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from models import User
from schemas import UserCreate, Token
from database import get_db
from sqlalchemy import or_
from config import SECRET_KEY, ALGORITHM

router = APIRouter()

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

def get_user_by_email_or_phone(db: Session, identifier: str):
    return db.query(User).filter(or_(User.email == identifier, User.phone == identifier)).first()

def authenticate_user(db: Session, identifier: str, password: str):
    user = get_user_by_email_or_phone(db, identifier)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

@router.post("/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email_or_phone(db, user.email) or get_user_by_email_or_phone(db, user.phone):
        raise HTTPException(status_code=400, detail="Email or phone already registered")
    hashed = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        hashed_password=hashed
    )
    db.add(new_user)
    db.commit()
    return {"msg": "User created successfully"}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email/phone or password")
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(days=365))
    return {"access_token": access_token, "token_type": "bearer"}
