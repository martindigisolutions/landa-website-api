from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import checkout_service
from schemas.checkout import CheckoutSessionCreate, CheckoutOptionsRequest, OrderCreate, ConfirmManualPayment, PaymentDetailsResponse
from typing import List, Optional
from schemas.checkout import OrderSummary

router = APIRouter(prefix="/checkout", tags=["Checkout"])

@router.post("/", summary="Iniciar sesión de checkout")
def start_checkout(data: CheckoutSessionCreate, db: Session = Depends(get_db)):
    return checkout_service.start_checkout_session(data, db)

@router.post("/options", summary="Obtener métodos de pago y envío disponibles")
def get_checkout_options(data: CheckoutOptionsRequest, db: Session = Depends(get_db)):
    return checkout_service.get_checkout_options(data, db)

@router.post("/order", summary="Crear orden final")
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    return checkout_service.create_order(data, db)

@router.post("/order/confirm-manual-payment", summary="Confirmar pago manual")
def confirm_manual_payment(data: ConfirmManualPayment, db: Session = Depends(get_db)):
    return checkout_service.confirm_manual_payment(data, db)

@router.get("/order/{order_id}/payment-details", response_model=PaymentDetailsResponse)
def get_payment_details(order_id: str, db: Session = Depends(get_db)):
    return checkout_service.get_payment_details(order_id, db)

@router.get("/orders", response_model=List[OrderSummary])
def list_orders(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    return checkout_service.get_order_list(db, user_id)
