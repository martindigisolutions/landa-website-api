from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=True)  # Nullable for partial registration
    last_name = Column(String, nullable=True)   # Nullable for partial registration
    phone = Column(String, unique=True, index=True, nullable=True)  # Nullable for partial registration
    whatsapp_phone = Column(String, unique=True, index=True, nullable=True)  # WhatsApp phone number
    email = Column(String, unique=True, index=True, nullable=True)  # Nullable for partial registration
    birthdate = Column(Date, nullable=True)
    user_type = Column(String, nullable=False, default="client")  # values: "stylist", "client"
    registration_complete = Column(Boolean, default=True)  # False for partial registrations
    created_at = Column(DateTime, default=datetime.utcnow)
    
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
    low_stock_threshold = Column(Integer, default=5)
    
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
    status = Column(String, default="pending")  # pending, paid, canceled, refunded, etc.
    total = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Stripe payment fields
    stripe_payment_intent_id = Column(String, nullable=True, index=True)
    payment_status = Column(String, default="pending")  # pending, processing, completed, failed, refunded
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User")
    items = relationship("OrderItem", back_populates="order")

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