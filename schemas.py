from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
