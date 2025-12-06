from pydantic import BaseModel
from typing import Optional


class CreatePaymentIntentRequest(BaseModel):
    order_id: str
    session_id: str


class CreatePaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


class ConfirmPaymentRequest(BaseModel):
    order_id: str
    payment_intent_id: str
    session_id: str


class ConfirmPaymentResponse(BaseModel):
    status: str
    order_id: str

