from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime, date

# ----- Product Schemas -----

class BaseProduct(BaseModel):
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

class ProductSchema(BaseProduct):
    id: int

    class Config:
        from_attributes = True

class PaginatedProductResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sorted_by: str
    results: List[ProductSchema]

# ----- User Schemas -----

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: EmailStr
    birthdate: Optional[date] = None
    user_type: Literal["client", "stylist"]

class UserCreate(BaseUser):
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: Optional[Literal["client", "stylist"]] = None

class UserOut(BaseUser):
    id: int
    created_at: Optional[datetime] = None

# ----- Auth Schemas -----

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginResponse(Token):
    user: UserOut

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
