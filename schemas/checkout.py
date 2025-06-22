from pydantic import BaseModel
from typing import List, Optional

class ProductInCart(BaseModel):
    product_id: int
    quantity: int

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
    instructions: str