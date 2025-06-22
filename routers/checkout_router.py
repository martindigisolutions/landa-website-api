from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import checkout_service
from schemas.checkout import CheckoutSessionCreate, CheckoutOptionsRequest, OrderCreate, ConfirmManualPayment

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