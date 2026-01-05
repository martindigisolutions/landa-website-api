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
    weight_lbs: Optional[float] = None  # Weight in pounds (overrides product weight if set)


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
    weight_lbs: Optional[float] = None  # Weight in pounds (overrides product weight if set)

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
    weight_lbs: Optional[float] = None  # Weight in pounds (overrides product weight if set)


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
    # Pricing (stock is managed separately via inventory endpoints)
    regular_price: float
    sale_price: Optional[float] = None
    restock_date: Optional[date] = None
    is_favorite: bool = False
    notify_when_available: bool = False
    image_url: Optional[str] = None  # Main image
    gallery: List[str] = []  # Additional images
    currency: str = "USD"
    low_stock_threshold: int = 5
    has_variants: bool = False
    brand: Optional[str] = None
    weight_lbs: float = 0.0  # Weight in pounds for shipping calculation
    variant_groups: List[ProductVariantGroupCreate] = []  # Include variant groups on creation
    categories: List[CategoryInput] = []  # Categories for the product
    # Related products (arrays of seller_sku strings)
    similar_products: List[str] = []  # Array of seller_sku
    frequently_bought_together: List[str] = []  # Array of seller_sku
    # Ordering fields for special sections
    bestseller_order: int = 0  # Order for bestseller section (0 = not featured, >0 = position)
    recommended_order: int = 0  # Order for recommended section (0 = not featured, >0 = position)


class ProductBulkCreate(BaseModel):
    products: List[ProductCreate]


class ProductBulkError(BaseModel):
    index: int
    seller_sku: Optional[str] = None
    error: str


class ProductUpdate(BaseModel):
    """Update product catalog info. Stock is managed via inventory endpoints."""
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
    # Pricing (stock is managed separately via inventory endpoints)
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    restock_date: Optional[date] = None
    is_favorite: Optional[bool] = None
    notify_when_available: Optional[bool] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None  # Additional images
    currency: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    has_variants: Optional[bool] = None
    brand: Optional[str] = None
    weight_lbs: Optional[float] = None  # Weight in pounds for shipping calculation
    # Variants (if provided, replaces all existing variants)
    variant_groups: Optional[List[ProductVariantGroupCreate]] = None
    # Categories (if provided, replaces all existing categories)
    categories: Optional[List[CategoryInput]] = None
    # Related products (arrays of seller_sku strings)
    similar_products: Optional[List[str]] = None
    frequently_bought_together: Optional[List[str]] = None
    # Ordering fields for special sections
    bestseller_order: Optional[int] = None  # Order for bestseller section (0 = not featured, >0 = position)
    recommended_order: Optional[int] = None  # Order for recommended section (0 = not featured, >0 = position)


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
    weight_lbs: Optional[float] = None  # Weight in pounds for shipping calculation
    # Ordering fields for special sections
    bestseller_order: int = 0  # Order for bestseller section (0 = not featured, >0 = position)
    recommended_order: int = 0  # Order for recommended section (0 = not featured, >0 = position)
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


# Bulk Update (catalog info only - stock is managed via inventory endpoints)
class ProductBulkUpdateItem(BaseModel):
    """Update product catalog info. Stock is managed via inventory endpoints."""
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
    # Pricing (stock is managed separately via inventory endpoints)
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    low_stock_threshold: Optional[int] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None  # Additional images
    brand: Optional[str] = None
    weight_lbs: Optional[float] = None  # Weight in pounds for shipping calculation
    # Variants (if provided, replaces all existing variants for this product)
    variant_groups: Optional[List[ProductVariantGroupCreate]] = None
    # Categories (if provided, replaces all existing categories for this product)
    categories: Optional[List[CategoryInput]] = None
    # Related products
    similar_products: Optional[List[str]] = None
    frequently_bought_together: Optional[List[str]] = None
    # Ordering fields for special sections
    bestseller_order: Optional[int] = None  # Order for bestseller section (0 = not featured, >0 = position)
    recommended_order: Optional[int] = None  # Order for recommended section (0 = not featured, >0 = position)


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
    variant_id: Optional[int] = None
    product_name: str
    variant_name: Optional[str] = None
    seller_sku: Optional[str] = None  # SKU of variant if exists, otherwise product SKU
    quantity: int
    price: float
    image_url: Optional[str] = None  # Variant image if available, otherwise product image

    class Config:
        from_attributes = True


class RecipientAddressDistrictInfo(BaseModel):
    address_name: str
    address_level: str  # L0 (Country), L1 (State), L2 (County), L3 (City)
    address_level_name: str  # Country, State, County, City


class RecipientAddress(BaseModel):
    name: Optional[str] = None  # Full name
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    postal_code: Optional[str] = None
    region_code: Optional[str] = None  # Country code (US, MX, etc)
    full_address: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: str = ""  # Always string, never None (empty string if not available)
    address_line2: str = ""  # Always string, never None (empty string if not available)
    address_line3: str = ""  # Always string, never None (empty string if not available)
    address_line4: str = ""  # Always string, never None (empty string if not available)
    district_info: List[RecipientAddressDistrictInfo] = []
    address_detail: Optional[str] = None


class OrderShipmentResponse(BaseModel):
    id: int
    order_id: int
    tracking_number: str
    tracking_url: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    shared_with_orders: Optional[List[int]] = None  # List of order IDs sharing this shipment

    class Config:
        from_attributes = True


class OrderShipmentCreate(BaseModel):
    tracking_number: str
    tracking_url: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None


class OrderShipmentBulkCreate(BaseModel):
    """Create multiple shipments for an order in a single request"""
    shipments: List[OrderShipmentCreate]  # List of shipments to create


class OrderShipmentUpdate(BaseModel):
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


class OrderAdminResponse(BaseModel):
    id: int
    session_id: Optional[str]
    user_id: Optional[int]
    shipping_method: Optional[str]
    payment_method: Optional[str]
    address: Optional[RecipientAddress] = None  # Formato TikTok
    status: str
    payment_status: str
    subtotal: Optional[float] = None  # Sum of all items before taxes and shipping
    tax: Optional[float] = None  # Tax amount
    shipping_fee: Optional[float] = None  # Shipping cost
    total: float  # Final total (subtotal + tax + shipping_fee)
    created_at: datetime
    paid_at: Optional[datetime]
    stripe_payment_intent_id: Optional[str]
    combined: bool = False  # True if order is combined with others
    combined_group_id: Optional[str] = None  # ID of the combined group
    combined_with: Optional[List[int]] = None  # List of order IDs in the same group
    shipments: List[OrderShipmentResponse] = []  # List of shipments/packages for this order
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str  # pending, pending_payment, pending_verification, awaiting_verification, paid, processing, shipped, delivered, canceled, refunded


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


# ---------- Shipping Rule Schemas ----------

class ShippingRuleInput(BaseModel):
    """
    Input for a shipping rule (used in sync and create).
    
    Rule Types:
    - "free_weight_per_product": Every X products from selected SKUs → Z lbs free
      - Requires: product_quantity, selected_products, free_weight_lbs
    - "free_weight_per_category": Every X products from selected categories → Z lbs free
      - Requires: product_quantity, selected_categories, free_weight_lbs
    - "minimum_weight_charge": If total weight < X lbs → charge $Y
      - Requires: minimum_weight_lbs, charge_amount
    - "base_rate": Rate per lb for remaining billable weight
      - Requires: rate_per_lb
    """
    id: Optional[int] = None  # Optional - used when syncing from dashboard
    rule_type: str  # "free_weight_per_product", "free_weight_per_category", "minimum_weight_charge", "base_rate"
    name: str
    
    # For free_weight_per_product
    selected_products: List[str] = []  # Array of seller_sku
    
    # For free_weight_per_category
    selected_categories: List[str] = []  # Array of category slugs
    
    # For free_weight rules
    product_quantity: Optional[int] = None  # X products needed to trigger
    free_weight_lbs: Optional[float] = None  # Z lbs granted
    
    # For minimum_weight_charge
    minimum_weight_lbs: Optional[float] = None  # Minimum weight threshold
    charge_amount: Optional[float] = None  # Amount to charge if under minimum
    
    # For base_rate
    rate_per_lb: Optional[float] = None  # Rate per pound
    
    priority: int = 0  # Lower = higher priority (evaluated first)
    is_active: bool = True


class ShippingRuleCreate(ShippingRuleInput):
    """Create a single shipping rule"""
    pass


class ShippingRuleUpdate(BaseModel):
    """Update a shipping rule (all fields optional)"""
    rule_type: Optional[str] = None
    name: Optional[str] = None
    selected_products: Optional[List[str]] = None
    selected_categories: Optional[List[str]] = None
    product_quantity: Optional[int] = None
    free_weight_lbs: Optional[float] = None
    minimum_weight_lbs: Optional[float] = None
    charge_amount: Optional[float] = None
    rate_per_lb: Optional[float] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ShippingRuleResponse(BaseModel):
    """Response for a shipping rule"""
    id: int
    rule_type: str
    name: str
    selected_products: List[str] = []
    selected_categories: List[str] = []
    product_quantity: Optional[int] = None
    free_weight_lbs: Optional[float] = None
    minimum_weight_lbs: Optional[float] = None
    charge_amount: Optional[float] = None
    rate_per_lb: Optional[float] = None
    priority: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ShippingRulesSyncRequest(BaseModel):
    """Request to sync all shipping rules from dashboard (replaces all existing)"""
    rules: List[ShippingRuleInput]


class ShippingRulesSyncResponse(BaseModel):
    """Response after syncing shipping rules"""
    success: bool
    synced: int
    message: str
    warnings: List[str] = []  # Non-blocking warnings (e.g., SKU not found)


# ---------- Inventory Schemas ----------

class InventoryUpdateSingle(BaseModel):
    """Update inventory for a single product"""
    stock: int  # New stock quantity
    is_in_stock: Optional[bool] = None  # If not provided, auto-calculated from stock > 0


class InventoryUpdateItem(BaseModel):
    """Item in bulk inventory update"""
    seller_sku: str  # Product SKU
    stock: int  # New stock quantity
    is_in_stock: Optional[bool] = None  # If not provided, auto-calculated from stock > 0


class InventoryBulkUpdate(BaseModel):
    """Bulk update inventory for multiple products"""
    products: List[InventoryUpdateItem]


class InventoryUpdateResponse(BaseModel):
    """Response for single inventory update"""
    seller_sku: str
    product_id: int
    stock: int
    is_in_stock: bool
    message: str


class InventoryBulkUpdateError(BaseModel):
    """Error for a single item in bulk update"""
    seller_sku: str
    error: str


class InventoryBulkUpdateResponse(BaseModel):
    """Response for bulk inventory update"""
    updated: int
    failed: int
    errors: List[InventoryBulkUpdateError] = []
    results: List[InventoryUpdateResponse] = []


# ---------- Variant Inventory Schemas ----------

class VariantInventoryUpdateSingle(BaseModel):
    """Update inventory for a single variant"""
    stock: int  # New stock quantity
    is_in_stock: Optional[bool] = None  # If not provided, auto-calculated from stock > 0


class VariantInventoryUpdateItem(BaseModel):
    """Item in bulk variant inventory update"""
    seller_sku: str  # Variant SKU
    stock: int  # New stock quantity
    is_in_stock: Optional[bool] = None  # If not provided, auto-calculated from stock > 0


class VariantInventoryBulkUpdate(BaseModel):
    """Bulk update inventory for multiple variants"""
    variants: List[VariantInventoryUpdateItem]


class VariantInventoryUpdateResponse(BaseModel):
    """Response for single variant inventory update"""
    variant_id: int
    seller_sku: Optional[str] = None
    variant_name: str
    product_id: int
    product_name: str
    stock: int
    is_in_stock: bool
    message: str


class VariantInventoryBulkUpdateError(BaseModel):
    """Error for a single variant in bulk update"""
    seller_sku: str
    error: str


class VariantInventoryBulkUpdateResponse(BaseModel):
    """Response for bulk variant inventory update"""
    updated: int
    failed: int
    errors: List[VariantInventoryBulkUpdateError] = []
    results: List[VariantInventoryUpdateResponse] = []


# ---------- Inventory List Schemas ----------

class InventoryItem(BaseModel):
    """Single item in inventory list (product or variant)"""
    id: int
    seller_sku: Optional[str] = None
    name: str
    stock: int
    is_in_stock: bool
    is_variant: bool
    image_url: Optional[str] = None
    # Only for variants
    parent_id: Optional[int] = None
    parent_sku: Optional[str] = None
    parent_name: Optional[str] = None
    variant_type: Optional[str] = None
    group_name: Optional[str] = None  # Category within variant type (e.g., "Naturales")


class InventoryListResponse(BaseModel):
    """Response for inventory list endpoint"""
    total_items: int
    total_products: int  # Count of simple products
    total_variants: int  # Count of variants
    items: List[InventoryItem]


# ---------- Unified Inventory Update Schemas ----------

class InventoryUpdateItem(BaseModel):
    """Update item for unified inventory endpoint (works for products and variants)"""
    seller_sku: str  # SKU of product or variant
    stock: int
    is_in_stock: Optional[bool] = None  # Auto-calculated if not provided


class InventoryUnifiedUpdate(BaseModel):
    """Unified bulk update for products and variants"""
    items: List[InventoryUpdateItem]


class InventoryUnifiedUpdateResult(BaseModel):
    """Result for a single item update"""
    seller_sku: str
    id: int
    name: str
    stock: int
    is_in_stock: bool
    is_variant: bool
    parent_sku: Optional[str] = None
    message: str


class InventoryUnifiedUpdateError(BaseModel):
    """Error for a single item"""
    seller_sku: str
    error: str


class InventoryUnifiedUpdateResponse(BaseModel):
    """Response for unified inventory update"""
    updated: int
    failed: int
    errors: List[InventoryUnifiedUpdateError] = []
    results: List[InventoryUnifiedUpdateResult] = []


# ---------- Order Combination Schemas ----------

class OrderCombineRequest(BaseModel):
    """Request to combine multiple orders"""
    order_ids: List[int]
    notes: Optional[str] = None


class OrderCombineResponse(BaseModel):
    """Response when orders are combined"""
    success: bool
    message: str
    combined_group_id: str
    orders: List[OrderAdminResponse]


class OrderUncombineRequest(BaseModel):
    """Request to uncombine orders"""
    order_ids: List[int]


class OrderUncombineResponse(BaseModel):
    """Response when orders are uncombined"""
    success: bool
    message: str
    uncombined_orders: List[int]


class CombinedOrdersResponse(BaseModel):
    """Response for getting combined orders group"""
    combined_group_id: str
    orders: List[OrderAdminResponse]
    shared_shipments: List[OrderShipmentResponse]