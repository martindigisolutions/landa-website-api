from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Category Schemas (Public) ----------

class CategoryPublic(BaseModel):
    """Category for public frontend (localized)"""
    id: int
    name: str  # Localized
    slug: str
    color: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        from_attributes = True


class CategoryGroupPublic(BaseModel):
    """Category group for public frontend (localized)"""
    id: int
    name: str  # Localized
    slug: str
    icon: Optional[str] = None
    show_in_filters: bool = True
    categories: List[CategoryPublic] = []

    class Config:
        from_attributes = True


# ---------- Product Variant Schemas ----------

class ProductVariantPublic(BaseModel):
    """Localized variant for public frontend"""
    id: int
    seller_sku: Optional[str] = None
    name: str  # Display name
    variant_value: Optional[str] = None  # Clean value for filters
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class VariantCategoryPublic(BaseModel):
    """Category within a variant type for public frontend"""
    id: int
    name: str
    variants: List[ProductVariantPublic] = []


class VariantTypePublic(BaseModel):
    """
    Grouped variant type for public frontend.
    - If categories is not None: variants are organized by category
    - If categories is None: variants are direct (simple variants)
    """
    type: str  # e.g., "Color", "Tamaño", "Volumen"
    categories: Optional[List[VariantCategoryPublic]] = None  # null = simple variants
    variants: Optional[List[ProductVariantPublic]] = None  # Only when categories is null


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
    variant_types: List[VariantTypePublic] = []  # Grouped by variant_type

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
