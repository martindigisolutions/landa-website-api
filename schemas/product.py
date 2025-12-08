from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductVariantPublic(BaseModel):
    """Localized variant for public frontend"""
    id: int
    seller_sku: Optional[str] = None
    name: str  # Localized name
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ProductVariantGroupPublic(BaseModel):
    """Localized variant group for public frontend"""
    id: int
    name: str  # Localized name
    variants: List[ProductVariantPublic] = []

    class Config:
        from_attributes = True


class ProductPublic(BaseModel):
    """
    Localized product response for public frontend.
    Fields are returned in the language specified by Accept-Language header.
    Falls back to Spanish if translation not available.
    """
    id: int
    seller_sku: Optional[str] = None
    name: str  # Localized (name or name_en)
    short_description: Optional[str] = None  # Localized
    description: Optional[str] = None  # Localized
    tags: Optional[str] = None  # Localized
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    restock_date: Optional[datetime] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    gallery: List[str] = []  # Additional images
    currency: Optional[str] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None
    variant_groups: List[ProductVariantGroupPublic] = []

    class Config:
        from_attributes = True


class PaginatedProductResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    sorted_by: str
    results: List[ProductPublic]


# Legacy schemas for backwards compatibility
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
