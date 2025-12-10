from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import checkout_service
from schemas.checkout import (
    CheckoutSessionCreate, 
    CheckoutOptionsRequest, 
    OrderCreate, 
    ConfirmManualPayment, 
    PaymentDetailsResponse,
    OrderSummary,
    OrderDetailResponse,
    UpdateAddressRequest,
    UpdateAddressResponse
)
from typing import List, Optional

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


@router.get("/orders/{order_id}", response_model=OrderDetailResponse, summary="Obtener detalle de una orden")
def get_order_detail(order_id: str, user_id: str, db: Session = Depends(get_db)):
    """
    Obtener el detalle completo de una orden específica.
    
    - **order_id**: ID de la orden (path parameter)
    - **user_id**: ID del usuario para verificar permisos (query parameter)
    
    Retorna 404 si la orden no existe.
    Retorna 403 si el usuario no tiene permiso para ver la orden.
    """
    return checkout_service.get_order_detail(order_id, user_id, db)


@router.put("/orders/{order_id}/address", response_model=UpdateAddressResponse, summary="Actualizar dirección de envío")
def update_order_address(order_id: str, data: UpdateAddressRequest, db: Session = Depends(get_db)):
    """
    Actualizar la dirección de envío de una orden.
    
    Solo se permite actualizar si el status es "pending_payment" o "awaiting_verification".
    
    - **order_id**: ID de la orden (path parameter)
    - **user_id**: ID del usuario para verificar permisos (en el body)
    - **address**: Nueva dirección de envío
    
    Retorna 404 si la orden no existe.
    Retorna 403 si el usuario no tiene permiso.
    Retorna 409 si la orden ya no permite modificaciones.
    """
    return checkout_service.update_order_address(order_id, data.user_id, data.address.model_dump(), db)
