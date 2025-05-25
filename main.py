from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from mangum import Mangum

# -------------------- Config --------------------
DATABASE_URL = "sqlite:///./api_db.sqlite3"
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# -------------------- DB setup --------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- Security --------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# -------------------- Models --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    short_description = Column(String)
    regular_price = Column(Float)
    sale_price = Column(Float)
    stock = Column(Integer)
    is_in_stock = Column(Boolean)
    restock_date = Column(Date, nullable=True)
    is_favorite = Column(Boolean)
    notify_when_available = Column(Boolean)
    image_url = Column(String)
    currency = Column(String)
    low_stock_threshold = Column(Integer)
    has_variants = Column(Boolean, default=False)



Base.metadata.create_all(bind=engine)

# -------------------- Schemas --------------------
class ProductSchema(BaseModel):
    id: int
    name: str
    short_description: Optional[str]
    regular_price: float
    sale_price: float
    stock: int
    is_in_stock: bool
    restock_date: Optional[datetime]
    is_favorite: bool
    notify_when_available: bool
    image_url: Optional[str]
    currency: str
    low_stock_threshold: int
    has_variants: bool

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# -------------------- Auth helpers --------------------
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if not user:
        raise credentials_exception
    return user

# -------------------- FastAPI App --------------------
app = FastAPI()

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    return {"msg": "User created successfully"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username}, expires_delta = timedelta(days=365))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/products", response_model=List[ProductSchema])
def get_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Product).all()

# -------------------- Lambda handler --------------------
handler = Mangum(app)
