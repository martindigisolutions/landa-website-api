from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey, JSON, func, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for users created via single-access-token
    first_name = Column(String, nullable=True)  # Nullable for partial registration
    last_name = Column(String, nullable=True)   # Nullable for partial registration
    phone = Column(String, unique=True, index=True, nullable=True)  # Nullable for partial registration
    whatsapp_phone = Column(String, unique=True, index=True, nullable=True)  # WhatsApp phone number
    email = Column(String, unique=True, index=True, nullable=True)  # Nullable for partial registration
    birthdate = Column(Date, nullable=True)
    user_type = Column(String, nullable=False, default="client")  # values: "stylist", "client"
    registration_complete = Column(Boolean, default=True)  # False for partial registrations
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Password management fields
    password_requires_update = Column(Boolean, default=False)  # True if user needs to set/update password
    password_last_updated = Column(DateTime, nullable=True)  # Last time password was changed
    
    # Suspension fields (temporary, reversible)
    is_suspended = Column(Boolean, default=False)
    suspended_at = Column(DateTime, nullable=True)
    suspended_reason = Column(String, nullable=True)
    
    # Block fields (permanent, severe)
    is_blocked = Column(Boolean, default=False)
    blocked_at = Column(DateTime, nullable=True)
    blocked_reason = Column(String, nullable=True)

    # Relationship to password reset requests
    password_reset_requests = relationship("PasswordResetRequest", back_populates="user")
    # Relationship to single access tokens
    single_access_tokens = relationship("SingleAccessToken", back_populates="user")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    seller_sku = Column(String, unique=True, index=True, nullable=True)  # SKU for dashboard linking
    
    # Names (commercial title from dashboard)
    name = Column(String, nullable=False)  # Spanish (default)
    name_en = Column(String, nullable=True)  # English
    
    # Descriptions
    short_description = Column(String, nullable=True)  # Spanish
    short_description_en = Column(String, nullable=True)  # English
    description = Column(String, nullable=True)  # Spanish
    description_en = Column(String, nullable=True)  # English
    
    # Tags for search
    tags = Column(String, nullable=True)  # Spanish (semicolon separated)
    tags_en = Column(String, nullable=True)  # English (semicolon separated)
    
    # Pricing
    regular_price = Column(Float)
    sale_price = Column(Float, nullable=True)
    
    # Inventory
    stock = Column(Integer, default=0)
    is_in_stock = Column(Boolean, default=True)
    restock_date = Column(Date, nullable=True)
    low_stock_threshold = Column(Integer, default=10)
    
    # Display
    is_favorite = Column(Boolean, default=False)
    notify_when_available = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)  # Main image
    gallery = Column(JSON, default=list)  # Array of additional image URLs
    currency = Column(String, default="USD")
    
    # Classification
    has_variants = Column(Boolean, default=False)
    brand = Column(String, nullable=True)
    
    # Shipping
    weight_lbs = Column(Float, default=0.0)  # Weight in pounds for shipping calculation
    
    # Related products (stored as arrays of seller_sku strings)
    similar_products = Column(JSON, default=list)  # Array of seller_sku
    frequently_bought_together = Column(JSON, default=list)  # Array of seller_sku
    
    # Ordering fields for special sections
    bestseller_order = Column(Integer, default=0)  # Order for bestseller section (0 = not featured, >0 = position)
    recommended_order = Column(Integer, default=0)  # Order for recommended section (0 = not featured, >0 = position)
    
    # Soft delete
    active = Column(Boolean, default=True)  # False = soft deleted, won't appear in catalog
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to variant groups
    variant_groups = relationship("ProductVariantGroup", back_populates="product", cascade="all, delete-orphan")
    # Relationship to categories (many-to-many)
    product_categories = relationship("ProductCategory", back_populates="product", cascade="all, delete-orphan")


class ProductVariantGroup(Base):
    """Group/Category of variants (e.g., 'Naturales', 'Fantasías')"""
    __tablename__ = "product_variant_groups"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    variant_type = Column(String, nullable=False)  # e.g., "Color", "Tamaño", "Volumen" - REQUIRED
    name = Column(String, nullable=True)  # Category name e.g., "Naturales", "Fantasías" - OPTIONAL (null = simple variants)
    display_order = Column(Integer, default=0)  # For sorting groups
    
    product = relationship("Product", back_populates="variant_groups")
    variants = relationship("ProductVariant", back_populates="group", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("product_variant_groups.id"), nullable=False)
    seller_sku = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)  # Display name e.g., "Rubio", "Azul", "Vol 10"
    variant_value = Column(String, nullable=True)  # Clean value for filters/search e.g., "Rubio", "Vol 10"
    barcode = Column(String, nullable=True)  # Barcode/UPC for scanning
    attributes = Column(JSON, default=dict)  # Additional attributes if needed
    regular_price = Column(Float, nullable=True)  # Override parent price if set
    sale_price = Column(Float, nullable=True)
    stock = Column(Integer, default=0)
    is_in_stock = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)  # Variant-specific image
    display_order = Column(Integer, default=0)  # For sorting variants
    active = Column(Boolean, default=True)  # Soft delete without removing
    weight_lbs = Column(Float, nullable=True)  # Weight in pounds (overrides product weight if set)
    
    group = relationship("ProductVariantGroup", back_populates="variants")

class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)

    user = relationship("User", back_populates="password_reset_requests")

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    shipping_method = Column(String)  # "pickup" o "delivery"
    payment_method = Column(String)   # "zelle", "stripe", "credit_card", etc.
    address = Column(JSON, nullable=True)  # Guardamos JSON de dirección
    status = Column(String, default="pending")  # pending, processing_payment, paid, payment_failed, pending_verification, canceled, refunded, etc.
    subtotal = Column(Float, nullable=True)  # Sum of all items before taxes and shipping
    tax = Column(Float, nullable=True)  # Tax amount
    shipping_fee = Column(Float, nullable=True)  # Shipping cost
    total = Column(Float)  # Final total (subtotal + tax + shipping_fee)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Stripe payment fields
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    payment_status = Column(String, default="pending")  # pending, processing, completed, failed, refunded
    paid_at = Column(DateTime, nullable=True)
    
    # Order combination fields
    combined_group_id = Column(String, nullable=True, index=True)  # ID del grupo de órdenes combinadas
    combined = Column(Boolean, default=False)  # Flag rápido para saber si está combinada
    
    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")
    shipments = relationship("OrderShipment", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=True)  # For products with variants
    quantity = Column(Integer)
    price = Column(Float)  # Precio congelado en el momento de la compra
    variant_name = Column(String, nullable=True)  # Frozen variant name at purchase time

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")


class OrderShipment(Base):
    """Individual shipment/package within an order. An order can have multiple shipments."""
    __tablename__ = "order_shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    tracking_number = Column(String, nullable=False)  # Tracking number from carrier
    tracking_url = Column(String, nullable=True)  # Full tracking URL (can be auto-generated)
    carrier = Column(String, nullable=True)  # Carrier name (USPS, FedEx, UPS, etc.)
    shipped_at = Column(DateTime, nullable=True)  # When this shipment was sent
    estimated_delivery = Column(DateTime, nullable=True)  # Estimated delivery date
    delivered_at = Column(DateTime, nullable=True)  # When this shipment was actually delivered
    notes = Column(String, nullable=True)  # Additional notes about this shipment
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Order combination field
    combined_group_id = Column(String, nullable=True, index=True)  # ID del grupo si es shipment compartido
    
    order = relationship("Order", back_populates="shipments")


class CombinedOrder(Base):
    """Tracks which orders are combined together for shared shipping."""
    __tablename__ = "combined_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    combined_group_id = Column(String, nullable=False, index=True)  # Unique ID for the group
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    order = relationship("Order")


class Application(Base):
    """OAuth2 Client Application for external dashboards/services"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String, unique=True, index=True, nullable=False)
    client_secret_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    scopes = Column(JSON, default=list)  # ["products:read", "products:write", "orders:read", etc.]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)


class SingleAccessToken(Base):
    """Single-use access token for user authentication via shared links"""
    __tablename__ = "single_access_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    redirect_url = Column(String, nullable=True)  # Where to redirect after validation
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="single_access_tokens")


# ==================== CATEGORY MODELS ====================

class CategoryGroup(Base):
    """Group/parent of categories (e.g., 'Tipo de producto', 'Marca')"""
    __tablename__ = "category_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Spanish name
    name_en = Column(String, nullable=True)  # English name
    slug = Column(String, unique=True, index=True, nullable=False)
    icon = Column(String, nullable=True)  # Icon name (e.g., "package", "tag")
    show_in_filters = Column(Boolean, default=True)  # Show in frontend filters
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to categories
    categories = relationship("Category", back_populates="group", cascade="all, delete-orphan")


class Category(Base):
    """Individual category within a group (e.g., 'Tintes', 'Shampoos')"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("category_groups.id"), nullable=False)
    name = Column(String, nullable=False)  # Spanish name
    name_en = Column(String, nullable=True)  # English name
    slug = Column(String, unique=True, index=True, nullable=False)
    color = Column(String, nullable=True)  # Hex color (e.g., "#007bff")
    icon = Column(String, nullable=True)  # Optional category-specific icon
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("CategoryGroup", back_populates="categories")
    products = relationship("ProductCategory", back_populates="category")


class ProductCategory(Base):
    """Many-to-many relationship between Product and Category"""
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    product = relationship("Product", back_populates="product_categories")
    category = relationship("Category", back_populates="products")


# ==================== SHIPPING RULE MODELS ====================

class UserFavorite(Base):
    """User's favorite products"""
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="favorites")
    product = relationship("Product")


class ShippingRule(Base):
    """
    Shipping rules for calculating shipping costs and free weight thresholds.
    
    Rule Types:
    - "free_weight_per_product": Every X products from selected SKUs → Z lbs free
    - "free_weight_per_category": Every X products from selected categories → Z lbs free
    - "minimum_weight_charge": If total weight < X lbs → charge $Y
    - "base_rate": Rate per lb for remaining billable weight
    """
    __tablename__ = "shipping_rules"

    id = Column(Integer, primary_key=True, index=True)
    
    # Rule type
    rule_type = Column(String, nullable=False, index=True)
    
    # Name/description for admin UI
    name = Column(String, nullable=False)
    
    # For free_weight_per_product: list of seller_sku
    selected_products = Column(JSON, default=list)  # ["sku1", "sku2", ...]
    
    # For free_weight_per_category: list of category slugs
    selected_categories = Column(JSON, default=list)  # ["tintes", "extensiones", ...]
    
    # For free_weight rules: how many products needed to trigger
    product_quantity = Column(Integer, nullable=True)
    
    # For free_weight rules: lbs granted when triggered
    free_weight_lbs = Column(Float, nullable=True)
    
    # For minimum_weight_charge: minimum weight threshold
    minimum_weight_lbs = Column(Float, nullable=True)
    
    # For minimum_weight_charge: amount to charge if under minimum
    charge_amount = Column(Float, nullable=True)
    
    # For base_rate: rate per pound
    rate_per_lb = Column(Float, nullable=True)
    
    # Rule ordering (lower = higher priority, evaluated first)
    priority = Column(Integer, default=0)
    
    # Active flag
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== CART MODELS ====================

class Cart(Base):
    """
    Shopping cart for users (authenticated) and guests (session-based).
    - Authenticated users: identified by user_id
    - Guests: identified by session_id (sent from frontend)
    """
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)  # For guest users
    
    # Shipping address (saved from checkout)
    shipping_first_name = Column(String, nullable=True)
    shipping_last_name = Column(String, nullable=True)
    shipping_phone = Column(String, nullable=True)
    shipping_email = Column(String, nullable=True)
    shipping_street = Column(String, nullable=True)
    shipping_apartment = Column(String, nullable=True)  # Apartment, suite, unit, etc.
    shipping_city = Column(String, nullable=True)
    shipping_state = Column(String, nullable=True)
    shipping_zipcode = Column(String, nullable=True)
    shipping_country = Column(String, nullable=True, default="US")
    is_pickup = Column(Boolean, default=False)  # True if store pickup
    
    # Payment method (saved before lock)
    payment_method = Column(String, nullable=True)  # "stripe" | "zelle"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # For automatic cleanup
    
    # Relationships
    user = relationship("User", backref="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.added_at")


class CartItem(Base):
    """Individual item in a shopping cart"""
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")


# ==================== STORE SETTINGS ====================

class StoreSettings(Base):
    """
    Store-wide configuration settings.
    Uses key-value pattern for flexibility.
    Only one row per key should exist (enforced by unique constraint).
    """
    __tablename__ = "store_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=True)  # Stored as string, parsed based on value_type
    value_type = Column(String, default="string")  # "string", "number", "boolean", "json"
    description = Column(String, nullable=True)  # Human-readable description
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Default settings keys (for reference)
# - min_order_amount: Minimum order amount to checkout (number)
# - max_order_amount: Maximum order amount allowed (number)


class TaxRateCache(Base):
    """
    Cache for GRT tax rates by full address.
    Avoids repeated API calls for the same address.
    Note: Tax rates can vary by street within the same city/zipcode.
    """
    __tablename__ = "tax_rate_cache"

    id = Column(Integer, primary_key=True, index=True)
    street_name = Column(String, nullable=True)  # Street name for precise matching
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zipcode = Column(String, nullable=False)
    tax_rate = Column(Float, nullable=False)
    county = Column(String, nullable=True)
    location_code = Column(String, nullable=True)
    
    # Cache metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # When cache expires
    
    # Index on full address for lookups
    __table_args__ = (
        Index('ix_tax_cache_address', 'street_name', 'city', 'state', 'zipcode'),
    )
# - tax_rate: Tax rate percentage (number, e.g., 8.25 for 8.25%)
# - enable_taxes: Whether taxes are enabled (boolean)
# - free_shipping_threshold: Amount for free shipping (number)
# - shipping_incentive_threshold: % of rule to show incentive (number, default 80)


# ==================== CART LOCK MODELS ====================

# Lock expiration time in minutes
LOCK_EXPIRATION_MINUTES = 5


class CartLock(Base):
    """
    Temporary lock on cart for checkout process.
    Reserves stock for a limited time while user completes payment.
    """
    __tablename__ = "cart_locks"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="active", index=True)  # active, used, expired, cancelled
    
    # Stripe integration
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    
    # Totals frozen at lock time
    subtotal = Column(Float, nullable=True)
    shipping_fee = Column(Float, nullable=True)
    tax = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)  # When lock was used to create order
    
    # Relationships
    cart = relationship("Cart", backref="locks")
    reservations = relationship("StockReservation", back_populates="lock", cascade="all, delete-orphan")


class StockReservation(Base):
    """
    Individual stock reservation within a cart lock.
    Tracks reserved quantity for each product/variant.
    """
    __tablename__ = "stock_reservations"

    id = Column(Integer, primary_key=True, index=True)
    lock_id = Column(Integer, ForeignKey("cart_locks.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    
    # Price frozen at reservation time
    unit_price = Column(Float, nullable=False)
    
    # Relationships
    lock = relationship("CartLock", back_populates="reservations")
    product = relationship("Product")
    variant = relationship("ProductVariant")


# ==================== USER ACTIVITY TRACKING ====================

class UserActivity(Base):
    """
    Tracks all user actions/interactions with the API.
    Captures endpoint calls, search queries, cart actions, checkout steps, etc.
    """
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User identification (nullable for guest users identified only by session_id)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)  # For guest users
    
    # Request information
    method = Column(String, nullable=False)  # GET, POST, PUT, PATCH, DELETE
    endpoint = Column(String, nullable=False, index=True)  # e.g., "/products", "/cart/add"
    action_type = Column(String, nullable=False, index=True)  # e.g., "view_products", "search", "add_to_cart", "checkout", "payment"
    
    # Request metadata (stored as JSON for flexibility)
    activity_metadata = Column("metadata", JSON, default=dict)  # Search terms, filters, product IDs, quantities, etc.
    
    # Request context
    query_params = Column(JSON, default=dict)  # Query parameters (e.g., search, filters, pagination)
    request_body = Column(JSON, nullable=True)  # Request body for POST/PUT/PATCH (sanitized)
    response_status = Column(Integer, nullable=True)  # HTTP status code
    
    # Client information
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", backref="activities")
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_user_activities_user_created', 'user_id', 'created_at'),
        Index('ix_user_activities_session_created', 'session_id', 'created_at'),
        Index('ix_user_activities_action_created', 'action_type', 'created_at'),
    )