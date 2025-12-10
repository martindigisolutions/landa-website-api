from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# ---------- Category Schemas ----------

class CategoryInput(BaseModel):
    """Input schema for category when creating/updating products.
    Flattened structure that includes both group and category info."""
    # Group fields
    group: str  # Spanish name (required)
    group_en: Optional[str] = None  # English name
    group_slug: str  # URL-friendly slug (required)
    group_icon: Optional[str] = None  # Icon name (e.g., "package")
    group_show_in_filters: bool = True  # Show in frontend filters
    group_display_order: int = 0  # Display order for the group
    # Category fields
    name: str  # Spanish name (required)
    name_en: Optional[str] = None  # English name
    slug: str  # URL-friendly slug (required)
    color: Optional[str] = None  # Hex color (e.g., "#007bff")
    icon: Optional[str] = None  # Category-specific icon
    display_order: int = 0  # Display order for the category


class CategoryResponse(BaseModel):
    """Response schema for a single category"""
    id: int
    name: str
    name_en: Optional[str] = None
    slug: str
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    # Include group info
    group_id: int
    group_name: str
    group_name_en: Optional[str] = None
    group_slug: str
    group_icon: Optional[str] = None
    group_show_in_filters: bool = True

    class Config:
        from_attributes = True


class CategoryGroupResponse(BaseModel):
    """Response schema for a category group with its categories"""
    id: int
    name: str
    name_en: Optional[str] = None
    slug: str
    icon: Optional[str] = None
    show_in_filters: bool = True
    display_order: int = 0
    categories: List["CategoryItemResponse"] = []

    class Config:
        from_attributes = True


class CategoryItemResponse(BaseModel):
    """Response schema for a category within a group"""
    id: int
    name: str
    name_en: Optional[str] = None
    slug: str
    color: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0

    class Config:
        from_attributes = True


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

# ---------- Product Variant Schemas ----------

class ProductVariantCreate(BaseModel):
    seller_sku: Optional[str] = None
    name: str  # Display name e.g., "Rubio", "Azul", "Vol 10"
    variant_value: Optional[str] = None  # Clean value for filters (defaults to name if not provided)
    barcode: Optional[str] = None  # Barcode/UPC for scanning
    attributes: dict = {}  # Additional attributes if needed
    regular_price: Optional[float] = None  # Override parent price
    sale_price: Optional[float] = None
    stock: int = 0
    is_in_stock: bool = True
    image_url: Optional[str] = None
    display_order: int = 0
    active: bool = True  # Soft delete without removing


class ProductVariantResponse(BaseModel):
    id: int
    group_id: int
    seller_sku: Optional[str] = None
    name: str
    variant_value: Optional[str] = None
    barcode: Optional[str] = None
    attributes: dict = {}
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    image_url: Optional[str] = None
    display_order: int = 0
    active: bool = True

    class Config:
        from_attributes = True


class ProductVariantGroupCreate(BaseModel):
    variant_type: str  # REQUIRED: e.g., "Color", "Tamaño", "Volumen"
    name: Optional[str] = None  # OPTIONAL: Category name e.g., "Naturales", "Fantasías" (null = simple variants)
    display_order: int = 0
    variants: List[ProductVariantCreate] = []


class ProductVariantUpdate(BaseModel):
    seller_sku: Optional[str] = None
    name: Optional[str] = None
    variant_value: Optional[str] = None
    barcode: Optional[str] = None
    attributes: Optional[dict] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    image_url: Optional[str] = None
    display_order: Optional[int] = None
    active: Optional[bool] = None


class VariantBulkDelete(BaseModel):
    variant_ids: List[int]


class VariantBulkDeleteError(BaseModel):
    id: int
    error: str


class VariantBulkDeleteResponse(BaseModel):
    deleted: int
    failed: int
    errors: List[VariantBulkDeleteError] = []


class ProductVariantGroupResponse(BaseModel):
    """Used internally and for individual group endpoints"""
    id: int
    product_id: int
    variant_type: str  # e.g., "Color", "Tamaño", "Volumen"
    name: Optional[str] = None  # Category name (null = simple variants)
    display_order: int = 0
    variants: List[ProductVariantResponse] = []

    class Config:
        from_attributes = True


# ---------- Grouped Variant Response (for product detail) ----------

class VariantCategoryResponse(BaseModel):
    """Category within a variant type (e.g., 'Naturales' within 'Color')"""
    id: int
    name: str
    display_order: int = 0
    variants: List[ProductVariantResponse] = []


class VariantTypeResponse(BaseModel):
    """
    Grouped variant type response.
    - If categories is not None: variants are organized by category
    - If categories is None: variants are direct (simple variants)
    """
    type: str  # e.g., "Color", "Tamaño", "Volumen"
    categories: Optional[List[VariantCategoryResponse]] = None  # null = simple variants
    variants: Optional[List[ProductVariantResponse]] = None  # Only when categories is null


# ---------- Product Schemas ----------

class ProductCreate(BaseModel):
    seller_sku: Optional[str] = None  # SKU for dashboard linking
    # Names (commercial title from dashboard)
    name: str  # Spanish (required)
    name_en: Optional[str] = None  # English
    # Descriptions
    short_description: Optional[str] = None  # Spanish
    short_description_en: Optional[str] = None  # English
    description: Optional[str] = None  # Spanish
    description_en: Optional[str] = None  # English
    # Tags
    tags: Optional[str] = None  # Spanish (semicolon separated)
    tags_en: Optional[str] = None  # English (semicolon separated)
    # Pricing & Inventory
    regular_price: float
    sale_price: Optional[float] = None
    stock: Optional[int] = 0
    is_in_stock: bool = True
    restock_date: Optional[date] = None
    is_favorite: bool = False
    notify_when_available: bool = False
    image_url: Optional[str] = None  # Main image
    gallery: List[str] = []  # Additional images
    currency: str = "USD"
    low_stock_threshold: int = 5
    has_variants: bool = False
    brand: Optional[str] = None
    variant_groups: List[ProductVariantGroupCreate] = []  # Include variant groups on creation
    categories: List[CategoryInput] = []  # Categories for the product
    # Related products (arrays of seller_sku strings)
    similar_products: List[str] = []  # Array of seller_sku
    frequently_bought_together: List[str] = []  # Array of seller_sku


class ProductBulkCreate(BaseModel):
    products: List[ProductCreate]


class ProductBulkError(BaseModel):
    index: int
    seller_sku: Optional[str] = None
    error: str


class ProductUpdate(BaseModel):
    seller_sku: Optional[str] = None
    # Names
    name: Optional[str] = None
    name_en: Optional[str] = None
    # Descriptions
    short_description: Optional[str] = None
    short_description_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    # Tags
    tags: Optional[str] = None
    tags_en: Optional[str] = None
    # Pricing & Inventory
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    restock_date: Optional[date] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None  # Additional images
    currency: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None
    # Variants (if provided, replaces all existing variants)
    variant_groups: Optional[List[ProductVariantGroupCreate]] = None
    # Categories (if provided, replaces all existing categories)
    categories: Optional[List[CategoryInput]] = None
    # Related products (arrays of seller_sku strings)
    similar_products: Optional[List[str]] = None
    frequently_bought_together: Optional[List[str]] = None


class ProductAdminResponse(BaseModel):
    """Full product response for admin dashboard (includes all language fields)"""
    id: int
    seller_sku: Optional[str] = None
    # Names
    name: str
    name_en: Optional[str] = None
    # Descriptions
    short_description: Optional[str] = None
    short_description_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    # Tags
    tags: Optional[str] = None
    tags_en: Optional[str] = None
    # Pricing & Inventory
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    restock_date: Optional[date] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    gallery: List[str] = []  # Additional images
    currency: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Variants grouped by type (new structure)
    variant_types: List[VariantTypeResponse] = []  # Grouped by variant_type
    # Categories
    categories: List[CategoryResponse] = []
    # Related products (raw arrays of seller_sku)
    similar_products: List[str] = []
    frequently_bought_together: List[str] = []

    class Config:
        from_attributes = True


class ProductBulkResponse(BaseModel):
    created: int
    failed: int
    errors: List[ProductBulkError] = []
    products: List[ProductAdminResponse] = []


# Bulk Delete
class ProductBulkDelete(BaseModel):
    product_ids: List[int]


class ProductBulkDeleteError(BaseModel):
    id: int
    error: str


class ProductBulkDeleteResponse(BaseModel):
    deleted: int
    failed: int
    errors: List[ProductBulkDeleteError] = []


# Bulk Update
class ProductBulkUpdateItem(BaseModel):
    id: int  # Product ID to update
    seller_sku: Optional[str] = None
    # Names
    name: Optional[str] = None
    name_en: Optional[str] = None
    # Descriptions
    short_description: Optional[str] = None
    short_description_en: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    # Tags
    tags: Optional[str] = None
    tags_en: Optional[str] = None
    # Pricing & Inventory
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    is_in_stock: Optional[bool] = None
    low_stock_threshold: Optional[int] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None  # Additional images
    brand: Optional[str] = None
    # Variants (if provided, replaces all existing variants for this product)
    variant_groups: Optional[List[ProductVariantGroupCreate]] = None
    # Categories (if provided, replaces all existing categories for this product)
    categories: Optional[List[CategoryInput]] = None
    # Related products
    similar_products: Optional[List[str]] = None
    frequently_bought_together: Optional[List[str]] = None


class ProductBulkUpdate(BaseModel):
    products: List[ProductBulkUpdateItem]


class ProductBulkUpdateError(BaseModel):
    id: int
    seller_sku: Optional[str] = None
    error: str


class ProductBulkUpdateResponse(BaseModel):
    updated: int
    failed: int
    errors: List[ProductBulkUpdateError] = []
    products: List[ProductAdminResponse] = []


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


# ---------- User Management Schemas ----------

class UserAdminCreate(BaseModel):
    """Schema for admin to create a user (partial registration allowed)
    At least one of phone, whatsapp_phone, or email must be provided.
    """
    phone: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: str = "client"  # "stylist" or "client"
    generate_access_link: bool = False  # If true, generates a single-access token link
    redirect_url: Optional[str] = None  # Custom redirect URL for the access link


class UserAdminResponse(BaseModel):
    id: int
    phone: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birthdate: Optional[date] = None
    user_type: str
    registration_complete: Optional[bool] = True
    created_at: Optional[datetime] = None
    # Suspension/Block status
    is_suspended: Optional[bool] = False
    suspended_at: Optional[datetime] = None
    suspended_reason: Optional[str] = None
    is_blocked: Optional[bool] = False
    blocked_at: Optional[datetime] = None
    blocked_reason: Optional[str] = None

    class Config:
        from_attributes = True


class UserAdminCreatedResponse(UserAdminResponse):
    """Response when creating a user - may include access_link if requested"""
    access_link: Optional[str] = None


class PaginatedUsersResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    results: List[UserAdminResponse]


# ---------- Single Access Token Schemas ----------

class SingleAccessTokenCreate(BaseModel):
    """Schema for generating a single-access token for an existing user"""
    redirect_url: Optional[str] = None  # Custom redirect URL, defaults to WHOLESALE_FRONTEND_URL


class SingleAccessTokenResponse(BaseModel):
    id: int
    user_id: int
    token: str
    access_link: str  # Full URL with token
    redirect_url: str
    created_at: datetime
    expires_at: datetime
    used: bool

    class Config:
        from_attributes = True


class ValidateAccessTokenRequest(BaseModel):
    """Request to validate a single-access token from frontend"""
    token: str


class ValidateAccessTokenResponse(BaseModel):
    """Response after validating a single-access token"""
    valid: bool
    already_used: bool = False  # True if token was already used before
    access_token: Optional[str] = None  # JWT token for the user (None if already_used)
    token_type: str = "bearer"
    redirect_url: Optional[str] = None
    user: Optional[UserAdminResponse] = None
    message: Optional[str] = None


# ---------- User Suspension/Block Schemas ----------

class UserSuspendRequest(BaseModel):
    """Request to suspend a user temporarily"""
    reason: Optional[str] = None


class UserBlockRequest(BaseModel):
    """Request to block a user permanently"""
    reason: Optional[str] = None


class UserActionResponse(BaseModel):
    """Response for user suspension/block actions"""
    success: bool
    message: str
    user: UserAdminResponse