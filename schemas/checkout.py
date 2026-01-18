from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductInCart(BaseModel):
    """Used for shipping calculation (not for checkout)"""
    product_id: int
    quantity: int
    variant_id: Optional[int] = None  # For products with variants


class CheckoutSessionCreate(BaseModel):
    """
    Start a checkout session using the server-side cart.
    Products are read from the cart, not sent by the frontend.
    For authenticated users, user is extracted from JWT token.
    """
    session_id: Optional[str] = None  # Required for guest users only

class Address(BaseModel):
    city: str
    state: str
    zip: str
    country: str

class CheckoutOptionsRequest(BaseModel):
    address: Address
    shipping_method: str

class OrderCreate(BaseModel):
    """
    Create an order using the server-side cart.
    Products are read from the cart, not sent by the frontend.
    For authenticated users, user is extracted from JWT token.
    
    **Required:**
    - lock_token: Token from POST /cart/lock (required)
    - payment_id: Optional - Stripe payment ID (for confirmation)
    """
    session_id: Optional[str] = None  # Required for guest users only
    
    lock_token: str  # Required - Token from POST /cart/lock
    payment_id: Optional[str] = None  # Stripe payment ID (optional)

class ConfirmManualPayment(BaseModel):
    order_id: str


# === Checkout validation responses ===

class CartValidationIssue(BaseModel):
    """Issue found during cart validation"""
    type: str  # "product_removed", "out_of_stock", "insufficient_stock", "price_changed"
    product_id: int
    product_name: Optional[str] = None
    variant_id: Optional[int] = None
    variant_name: Optional[str] = None
    message: str
    requested_quantity: Optional[int] = None
    available_stock: Optional[int] = None


class CheckoutValidationResponse(BaseModel):
    """Response when checkout validation fails"""
    valid: bool
    checkout_id: Optional[str] = None
    issues: List[CartValidationIssue] = []
    message: str

class PaymentDetailsResponse(BaseModel):
    payment_type: str
    instructions: Optional[str] = None
    # Campos adicionales para Stripe
    order_id: Optional[str] = None
    total: Optional[float] = None
    requires_payment_intent: Optional[bool] = None

class ShipmentInfo(BaseModel):
    """Basic shipment information for order list"""
    id: int
    tracking_number: str
    tracking_url: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    status: Optional[str] = None  # pending, in_transit, delivered, exception (derived from delivered_at)

    class Config:
        from_attributes = True


class OrderSummary(BaseModel):
    id: int
    status: str
    payment_method: str
    shipping_method: str
    total: float
    created_at: datetime
    combined: bool = False  # True if order is combined with others
    combined_with: Optional[List[int]] = None  # List of order IDs in the same group
    shipments: List[ShipmentInfo] = []  # List of shipments for this order

    class Config:
        from_attributes = True


# === Schemas para GET /checkout/orders/{order_id} ===

class AddressDetail(BaseModel):
    city: str
    state: str
    zip: str
    country: str
    street: Optional[str] = None
    apartment: Optional[str] = None


class OrderItemDetail(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    product_name: str  # Parent product name only
    variant_name: Optional[str] = None  # Variant name (null if no variant)
    quantity: int
    price: float
    image_url: Optional[str] = None  # Variant image if available, otherwise product image


class ShipmentDetail(BaseModel):
    """Detailed shipment information for order detail"""
    id: int
    tracking_number: str
    tracking_url: Optional[str] = None
    carrier: Optional[str] = None
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    shared_with_orders: Optional[List[int]] = None  # List of order IDs sharing this shipment

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    order_id: str
    status: str
    payment_status: Optional[str] = "pending"  # pending, processing, completed, failed, refunded
    total: float
    subtotal: float
    shipping_cost: float
    tax: float
    items: List[OrderItemDetail]
    address: Optional[AddressDetail] = None
    shipping_method: str
    payment_method: str
    stripe_payment_intent_id: Optional[str] = None  # Stripe PaymentIntent ID if using Stripe
    combined: bool = False  # True if order is combined with others
    combined_with: Optional[List[int]] = None  # List of order IDs in the same group
    tracking_number: Optional[str] = None  # DEPRECATED: Use shipments array instead
    tracking_url: Optional[str] = None  # DEPRECATED: Use shipments array instead
    shipped_at: Optional[datetime] = None  # DEPRECATED: Use shipments array instead
    shipments: List[ShipmentDetail] = []  # List of all shipments/packages for this order
    created_at: datetime
    paid_at: Optional[datetime] = None  # Timestamp when payment was completed


# === Schemas para PUT /checkout/orders/{order_id}/address ===

class AddressUpdate(BaseModel):
    city: str
    state: str
    zip: str
    country: str
    street: Optional[str] = None
    apartment: Optional[str] = None


class UpdateAddressRequest(BaseModel):
    user_id: Optional[str] = None  # Deprecated: user_id is now extracted from auth token
    address: AddressUpdate


class UpdateAddressResponse(BaseModel):
    success: bool
    message: str
    order_id: str


# === Schemas para cálculo de shipping ===

class CalculateShippingRequest(BaseModel):
    """Request to calculate shipping cost based on cart contents"""
    products: List[ProductInCart]
    address: Address


class ShippingSuggestion(BaseModel):
    """Suggestion to help customer save on shipping"""
    suggestion_type: str  # "add_products_for_free_weight", "fill_remaining_weight"
    message: str  # Human-readable suggestion in Spanish
    message_en: Optional[str] = None  # English version
    
    # For add_products_for_free_weight
    products_needed: Optional[int] = None  # How many more products needed
    brand: Optional[str] = None  # Brand to buy (for product_type rules)
    category_id: Optional[int] = None  # Category to buy (for category rules)
    category_name: Optional[str] = None  # Category name for display
    potential_savings: Optional[float] = None  # How much they could save
    
    # For fill_remaining_weight
    remaining_lbs: Optional[float] = None  # How many more lbs fit in free tier


class AppliedShippingRule(BaseModel):
    """Information about a rule that was applied"""
    rule_name: str
    rule_type: str
    free_weight_granted: float  # How many lbs were made free by this rule
    quantity_matched: Optional[int] = None  # How many products matched


class CalculateShippingResponse(BaseModel):
    """Response with shipping cost calculation and suggestions"""
    # Calculated costs
    total_weight_lbs: float
    free_weight_lbs: float  # Weight covered by free shipping rules
    billable_weight_lbs: float  # Weight to charge for
    shipping_cost: float  # Final shipping cost in USD
    
    # Breakdown
    applied_rules: List[AppliedShippingRule] = []
    
    # Suggestions for saving money (only shown if >= 80% progress toward a rule)
    suggestions: List[ShippingSuggestion] = []
    
    # Summary message
    summary: str  # e.g., "Shipping: $5.99" or "Free shipping!"
    summary_en: Optional[str] = None