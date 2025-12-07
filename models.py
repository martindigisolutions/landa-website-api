from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, ForeignKey, func
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
    name = Column(String, nullable=False)
    short_description = Column(String)
    description = Column(String)
    regular_price = Column(Float)
    sale_price = Column(Float)
    stock = Column(Integer)
    is_in_stock = Column(Boolean)
    restock_date = Column(Date, nullable=True)
    is_favorite = Column(Boolean)
    notify_when_available = Column(Boolean)
    image_url = Column(String)
    currency = Column(String)
    low_stock_threshold = Column(Integer)
    has_variants = Column(Boolean, default=False)
    brand = Column(String)

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
    quantity = Column(Integer)
    price = Column(Float)  # Precio congelado en el momento de la compra

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


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