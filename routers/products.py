from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import asc, desc
from schemas import ProductSchema, PaginatedProductResponse
from models import Product, User
from database import get_db
from routers.auth import get_user_by_email_or_phone
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import math

router = APIRouter()

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
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

@router.get("/products", response_model=PaginatedProductResponse)
def get_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    order_by: Optional[str] = Query(None, pattern="^(price|name|stock)$"),
    direction: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    query = db.query(Product)

    if brand:
        query = query.filter(Product.brand == brand)
    if min_price is not None:
        query = query.filter(Product.sale_price != None, Product.sale_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.sale_price != None, Product.sale_price <= max_price)

    if order_by:
        sort_column = {
            "price": Product.sale_price,
            "name": Product.name,
            "stock": Product.stock
        }.get(order_by)
        if sort_column is not None:
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
