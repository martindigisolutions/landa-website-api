from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class BaseProduct(BaseModel):
    seller_sku: Optional[str] = None
    name: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    restock_date: Optional[datetime] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    currency: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None

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
