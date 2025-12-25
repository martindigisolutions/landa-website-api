"""
Cart schemas for shopping cart operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- Product/Variant Info in Cart ----------

class CartProductInfo(BaseModel):
    """Product information for cart display"""
    id: int
    seller_sku: Optional[str] = None
    name: str
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0

    class Config:
        from_attributes = True


class CartVariantInfo(BaseModel):
    """Variant information for cart display"""
    id: int
    seller_sku: Optional[str] = None
    name: str  # Display name e.g., "Rubio", "1 Kg", "Vol 30"
    variant_type: Optional[str] = None  # Type e.g., "Color", "Tamaño", "Volumen"
    variant_value: Optional[str] = None  # Clean value for display
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0

    class Config:
        from_attributes = True


# ---------- Cart Item Schemas ----------

class CartItemBase(BaseModel):
    """Base schema for cart item"""
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(ge=1, default=1)


class CartItemCreate(CartItemBase):
    """Schema for adding item to cart"""
    pass


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    """Full cart item response with product details"""
    id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    product: CartProductInfo
    variant: Optional[CartVariantInfo] = None
    unit_price: float  # Current price (sale_price or regular_price)
    line_total: float  # unit_price * quantity
    stock_status: str  # "available", "low_stock", "out_of_stock", "reduced"
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Stock Warning ----------

class StockWarning(BaseModel):
    """Warning about stock issues"""
    type: str  # "low_stock", "out_of_stock", "quantity_reduced"
    message: str
    available_stock: int
    requested_quantity: Optional[int] = None


# ---------- Cart Summary ----------

class CartSummary(BaseModel):
    """Summary of cart totals"""
    items_count: int  # Number of distinct items
    total_items: int  # Total quantity of all items
    subtotal: float  # Sum of all line_totals


# ---------- Shipping Incentive ----------

class ShippingIncentive(BaseModel):
    """Incentive to encourage adding more items for better shipping"""
    type: str  # "free_shipping", "reduced_shipping", "category_discount"
    message: str  # Message ready for display (in requested language)
    amount_needed: Optional[float] = None  # Additional amount needed
    items_needed: Optional[int] = None  # Additional items needed
    category: Optional[str] = None  # Specific category if applicable
    potential_savings: float  # How much they would save on shipping


# ---------- Shipping Address ----------

class ShippingAddress(BaseModel):
    """Shipping address saved in cart"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: str
    state: str
    zipcode: str
    country: Optional[str] = "US"


class UpdateShippingRequest(BaseModel):
    """Request to update shipping address"""
    street: Optional[str] = None
    city: Optional[str] = None  # Optional for pickup
    state: Optional[str] = None  # Optional for pickup
    zipcode: Optional[str] = Field(None, alias="zipcode")
    zip: Optional[str] = Field(None)  # Alias for zipcode (frontend compatibility)
    is_pickup: bool = False
    delivery_method: Optional[str] = None  # "delivery" or "pickup" (frontend compatibility)
    # Extra fields from frontend
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None
    
    def get_zipcode(self) -> str:
        """Get zipcode from either field"""
        return self.zipcode or self.zip or ""
    
    def get_is_pickup(self) -> bool:
        """Get pickup status from either field"""
        if self.delivery_method:
            return self.delivery_method.lower() == "pickup"
        return self.is_pickup


class UpdateShippingResponse(BaseModel):
    """Response after updating shipping address"""
    success: bool
    message: str
    shipping_address: Optional[ShippingAddress] = None
    is_pickup: bool = False


# ---------- Payment Methods ----------

class PaymentMethod(BaseModel):
    """Available payment method"""
    id: str  # "stripe", "cash", "zelle"
    name: str  # Display name in requested language
    enabled: bool = True
    icon: Optional[str] = None  # Icon identifier


# ---------- Active Lock Info (for GET /cart) ----------

class ActiveLockInfo(BaseModel):
    """Information about an active lock for GET /cart"""
    lock_token: str
    expires_at: datetime
    expires_in_seconds: int


# ---------- Cart Response ----------

class CartResponse(BaseModel):
    """Full cart response with order summary and validation"""
    id: int
    items_count: int
    total_items: int
    subtotal: float
    items: List[CartItemResponse] = []
    warnings: List[StockWarning] = []
    
    # Order Summary - Totals
    shipping_fee: float = 0.0
    tax: float = 0.0
    tax_rate: float = 0.0  # Tax rate percentage applied
    tax_source: str = "none"  # "grt_api", "fixed_rate", "store_rate", "none"
    total: float = 0.0  # subtotal + shipping_fee + tax
    
    # Shipping Address (saved from checkout)
    shipping_address: Optional[ShippingAddress] = None
    is_pickup: bool = False
    
    # Payment method selected
    payment_method: Optional[str] = None  # "stripe" | "zelle"
    
    # Active lock info (if exists)
    active_lock: Optional[ActiveLockInfo] = None
    
    # Checkout Validation
    can_checkout: bool = True
    min_order_amount: float = 0.0
    max_order_amount: float = 0.0
    order_validation_error: Optional[str] = None
    
    # Shipping Incentive (optional)
    shipping_incentive: Optional[ShippingIncentive] = None

    class Config:
        from_attributes = True


# ---------- Add Item Response ----------

class AddItemResponse(BaseModel):
    """Response when adding item to cart"""
    success: bool
    message: str
    item: Optional[CartItemResponse] = None
    cart_summary: CartSummary
    warning: Optional[StockWarning] = None


# ---------- Update Item Response ----------

class UpdateItemResponse(BaseModel):
    """Response when updating cart item"""
    success: bool
    message: str
    item: Optional[CartItemResponse] = None
    cart_summary: CartSummary
    warning: Optional[StockWarning] = None


# ---------- Delete Item Response ----------

class DeleteItemResponse(BaseModel):
    """Response when deleting cart item"""
    success: bool
    message: str
    cart_summary: CartSummary


# ---------- Clear Cart Response ----------

class ClearCartResponse(BaseModel):
    """Response when clearing cart"""
    success: bool
    message: str


# ---------- Merge Cart Response ----------

class MergeCartResponse(BaseModel):
    """Response when merging carts (on login)"""
    success: bool
    message: str
    merged_items: int
    cart: CartResponse


# ---------- Recommendations ----------

class RecommendedProduct(BaseModel):
    """Recommended product info"""
    id: int
    seller_sku: Optional[str] = None
    name: str
    name_en: Optional[str] = None
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0
    brand: Optional[str] = None
    has_variants: bool = False
    recommendation_score: int  # How many cart items recommend this product

    class Config:
        from_attributes = True


class RecommendationsResponse(BaseModel):
    """Response for cart-based recommendations ('Te puede interesar')"""
    recommendations: List[RecommendedProduct] = []
    based_on_items: int  # Number of cart items used for recommendations


# ---------- Payment Method Update ----------

class UpdatePaymentMethodRequest(BaseModel):
    """Request to update payment method"""
    payment_method: str  # "stripe" | "zelle"


class UpdatePaymentMethodResponse(BaseModel):
    """Response after updating payment method"""
    success: bool
    payment_method: str
    message: str


# ---------- Cart Lock System ----------

class UnavailableItem(BaseModel):
    """Item with insufficient stock"""
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    variant_name: Optional[str] = None
    requested: int
    available: int


class PaymentIntentInfo(BaseModel):
    """Stripe payment intent info"""
    client_secret: str
    amount: int  # In cents
    currency: str = "usd"


class LockCartRequest(BaseModel):
    """Request to lock cart (empty body, uses current cart)"""
    pass


class LockCartResponse(BaseModel):
    """Response from POST /cart/lock"""
    success: bool
    lock_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    expires_in_seconds: Optional[int] = None
    payment_intent: Optional[PaymentIntentInfo] = None
    # Error fields
    error: Optional[str] = None  # "stock_unavailable"
    message: Optional[str] = None
    unavailable_items: Optional[List[UnavailableItem]] = None


class ReleaseLockRequest(BaseModel):
    """Request to release/cancel a lock"""
    lock_token: str


class ReleaseLockResponse(BaseModel):
    """Response from DELETE /cart/lock or POST /cart/lock/release"""
    success: bool
    message: str
