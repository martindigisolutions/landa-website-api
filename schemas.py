from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime
from datetime import date

class ProductSchema(BaseModel):
    id: int
    name: str
    short_description: Optional[str]
    regular_price: float
    sale_price: float
    stock: Optional[int]
    is_in_stock: bool
    restock_date: Optional[datetime]
    is_favorite: bool
    notify_when_available: bool
    image_url: Optional[str]
    currency: str
    low_stock_threshold: int
    has_variants: bool
    brand: Optional[str]

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
    email: EmailStr
    password: str
    birthdate: date
    user_type: Literal["client", "stylist"]

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: Optional[Literal["client", "stylist"]] = None

class Token(BaseModel):
    access_token: str
    token_type: str
