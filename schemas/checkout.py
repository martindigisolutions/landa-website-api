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