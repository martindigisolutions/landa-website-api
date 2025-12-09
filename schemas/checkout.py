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
