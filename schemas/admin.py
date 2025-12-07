from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# ---------- Application Schemas ----------

class ApplicationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    scopes: List[str] = []


class ApplicationResponse(BaseModel):
    id: int
    client_id: str
    name: str
    description: Optional[str]
    scopes: List[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApplicationCreatedResponse(ApplicationResponse):
    """Response when creating a new application - includes client_secret (shown only once)"""
    client_secret: str


class ApplicationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ---------- OAuth Token Schemas ----------

class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


# ---------- Product Admin Schemas ----------

class ProductCreate(BaseModel):
    name: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    regular_price: float
    sale_price: Optional[float] = None
    stock: Optional[int] = 0
    is_in_stock: bool = True
    restock_date: Optional[date] = None
    is_favorite: bool = False
    notify_when_available: bool = False
    image_url: Optional[str] = None
    currency: str = "USD"
    low_stock_threshold: int = 5
    has_variants: bool = False
    brand: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    restock_date: Optional[date] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    currency: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None


class ProductAdminResponse(BaseModel):
    id: int
    name: str
    short_description: Optional[str]
    description: Optional[str]
    regular_price: float
    sale_price: Optional[float]
    stock: Optional[int]
    is_in_stock: bool
    restock_date: Optional[date]
    is_favorite: bool
    notify_when_available: bool
    image_url: Optional[str]
    currency: str
    low_stock_threshold: int
    has_variants: bool
    brand: Optional[str]

    class Config:
        from_attributes = True


# ---------- Order Admin Schemas ----------

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: float

    class Config:
        from_attributes = True


class OrderAdminResponse(BaseModel):
    id: int
    session_id: Optional[str]
    user_id: Optional[int]
    shipping_method: Optional[str]
    payment_method: Optional[str]
    address: Optional[dict]
    status: str
    payment_status: str
    total: float
    created_at: datetime
    paid_at: Optional[datetime]
    stripe_payment_intent_id: Optional[str]
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str  # pending, processing, shipped, delivered, canceled, refunded


class OrdersFilterParams(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    user_id: Optional[int] = None
    page: int = 1
    page_size: int = 20


class PaginatedOrdersResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    results: List[OrderAdminResponse]


# ---------- Stats Schemas ----------

class AdminStats(BaseModel):
    total_orders: int
    total_revenue: float
    total_products: int
    total_users: int
    orders_by_status: dict
    recent_orders: List[OrderAdminResponse]

