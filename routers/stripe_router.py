from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services import stripe_service
from schemas.stripe import (
    CreatePaymentIntentRequest,
    CreatePaymentIntentResponse,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse
)

router = APIRouter(prefix="/stripe", tags=["Stripe Payments"])


@router.post(
    "/create-payment-intent",
    response_model=CreatePaymentIntentResponse,
    summary="Crear Payment Intent para una orden"
)
def create_payment_intent(
    data: CreatePaymentIntentRequest,
    db: Session = Depends(get_db)
):
    """
    Crea un Payment Intent en Stripe para procesar el pago de una orden.
    
    Este endpoint debe llamarse cuando el usuario selecciona "Credit/Debit Card"
    como método de pago. Retorna el `client_secret` necesario para el frontend
    de Stripe Elements.
    
    - **order_id**: ID de la orden en el sistema
    - **session_id**: Session ID del usuario para validación
    """
    result = stripe_service.create_payment_intent(
        order_id=data.order_id,
        session_id=data.session_id,
        db=db
    )
    return result


@router.post(
    "/confirm-payment",
    response_model=ConfirmPaymentResponse,
    summary="Confirmar pago de Stripe"
)
def confirm_payment(
    data: ConfirmPaymentRequest,
    db: Session = Depends(get_db)
):
    """
    Confirma el estado del pago después de que Stripe redirige al usuario.
    
    Este endpoint verifica el Payment Intent con Stripe y actualiza el estado
    de la orden correspondiente.
    
    - **order_id**: ID de la orden en el sistema
    - **payment_intent_id**: ID del Payment Intent de Stripe
    - **session_id**: Session ID del usuario para validación
    """
    result = stripe_service.confirm_payment(
        order_id=data.order_id,
        payment_intent_id=data.payment_intent_id,
        session_id=data.session_id,
        db=db
    )
    return result


@router.post("/webhook", summary="Webhook de Stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Endpoint para recibir webhooks de Stripe.
    
    Stripe envía eventos automáticamente a este endpoint cuando ocurren
    cambios en los pagos. Es la forma más confiable de saber cuándo
    un pago fue exitoso.
    
    **Eventos soportados:**
    - `payment_intent.succeeded`: Pago exitoso
    - `payment_intent.payment_failed`: Pago fallido
    - `charge.refunded`: Reembolso procesado
    
    **Configuración:**
    1. Ir a Stripe Dashboard → Developers → Webhooks
    2. Añadir endpoint: `https://tudominio.com/stripe/webhook`
    3. Seleccionar los eventos mencionados
    4. Configurar `STRIPE_WEBHOOK_SECRET` con el secret proporcionado
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    result = stripe_service.handle_webhook(
        payload=payload,
        sig_header=sig_header,
        db=db
    )
    return result

