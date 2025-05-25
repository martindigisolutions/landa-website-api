from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, Date, or_, asc, desc
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import List, Optional, Any
from pydantic import BaseModel
from mangum import Mangum
import math

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
    hashed_password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)

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
    brand = Column(String)  # ✅ nuevo campo

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
    brand: Optional[str]  # ✅ nuevo campo

    class Config:
        from_attributes = True


class PaginatedProductResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sorted_by: str
    results: List[ProductSchema]

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: str
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

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if not identifier:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email_or_phone(db, identifier)
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

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email/phone or password")
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(days=365))
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/products", response_model=PaginatedProductResponse)
def get_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    order_by: Optional[str] = Query(None, regex="^(price|name|stock)$"),
    direction: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    query = db.query(Product)

    if brand:
        query = query.filter(Product.brand == brand)

    if min_price is not None:
        print("min not none")
        query = query.filter(Product.sale_price != None, Product.sale_price >= min_price)
        filtered_products = query.all()
        for p in filtered_products:
            print(p.id, p.name, p.sale_price)
    if max_price is not None:
        query = query.filter(Product.sale_price != None, Product.sale_price <= max_price)


    if order_by:
        sort_column = {
            "price": Product.sale_price,
            "name": Product.name,
            "stock": Product.stock
        }.get(order_by)
        query = query.order_by(asc(sort_column) if direction == "asc" else desc(sort_column))

    total_items = query.count()
    total_pages = math.ceil(total_items / page_size)
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "sorted_by": f"{order_by}_{direction}" if order_by else "",
        "results": results
    }

# -------------------- Lambda handler --------------------
handler = Mangum(app)
