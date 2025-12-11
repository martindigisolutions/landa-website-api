from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProductInCart(BaseModel):
    product_id: int
    quantity: int
    variant_id: Optional[int] = None  # For products with variants

class CheckoutSessionCreate(BaseModel):
    session_id: str
    user_id: Optional[int]
    products: List[ProductInCart]

class Address(BaseModel):
    city: str
    state: str
    zip: str
    country: str

class CheckoutOptionsRequest(BaseModel):
    address: Address
    shipping_method: str

class OrderCreate(BaseModel):
    session_id: str
    user_id: Optional[int]
    products: List[ProductInCart]
    address: Address
    shipping_method: str
    payment_method: str

class ConfirmManualPayment(BaseModel):
    order_id: str

class PaymentDetailsResponse(BaseModel):
    payment_type: str
    instructions: Optional[str] = None
    # Campos adicionales para Stripe
    order_id: Optional[str] = None
    total: Optional[float] = None
    requires_payment_intent: Optional[bool] = None

class OrderSummary(BaseModel):
    id: int
    status: str
    payment_method: str
    shipping_method: str
    total: float
    created_at: datetime

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
    name: str
    quantity: int
    price: float
    image_url: Optional[str] = None


class OrderDetailResponse(BaseModel):
    order_id: str
    status: str
    total: float
    subtotal: float
    shipping_cost: float
    tax: float
    items: List[OrderItemDetail]
    address: Optional[AddressDetail] = None
    shipping_method: str
    payment_method: str
    created_at: datetime


# === Schemas para PUT /checkout/orders/{order_id}/address ===

class AddressUpdate(BaseModel):
    city: str
    state: str
    zip: str
    country: str
    street: Optional[str] = None
    apartment: Optional[str] = None


class UpdateAddressRequest(BaseModel):
    user_id: str
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