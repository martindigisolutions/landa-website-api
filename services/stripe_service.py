import stripe
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from typing import Optional

from models import Order
from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

# Configure Stripe
stripe.api_key = STRIPE_SECRET_KEY


def create_payment_intent(order_id: str, session_id: str, db: Session) -> dict:
    """
    Crea un Payment Intent en Stripe para una orden existente.
    Retorna el client_secret y payment_intent_id necesarios para el frontend.
    """
    # 1. Obtener la orden de la base de datos
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = db.query(Order).filter(Order.id == order_id_int).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 2. Verificar que la orden pertenece al usuario/sesión
    if order.session_id != session_id:
        raise HTTPException(status_code=403, detail="Unauthorized - session mismatch")
    
    # 3. Verificar que la orden está en estado válido para pago
    if order.payment_status == "completed":
        raise HTTPException(status_code=400, detail="Order already paid")
    
    # 4. Si ya tiene un payment_intent_id, reutilizarlo
    if order.stripe_payment_intent_id:
        try:
            existing_intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
            if existing_intent.status in ["requires_payment_method", "requires_confirmation", "requires_action"]:
                return {
                    "client_secret": existing_intent.client_secret,
                    "payment_intent_id": existing_intent.id
                }
        except stripe.error.StripeError:
            # Si hay error, crear uno nuevo
            pass
    
    # 5. Calcular el monto total (en centavos) - SIEMPRE calcular desde el backend
    amount_in_cents = int(order.total * 100)
    
    if amount_in_cents < 50:  # Stripe requiere mínimo $0.50 USD
        raise HTTPException(status_code=400, detail="Order total is too low for payment")
    
    try:
        # 6. Crear el Payment Intent
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="usd",
            metadata={
                "order_id": str(order.id),
                "session_id": session_id,
            },
            automatic_payment_methods={"enabled": True},
        )
        
        # 7. Guardar el payment_intent_id en la orden
        order.stripe_payment_intent_id = payment_intent.id
        order.payment_status = "pending"
        db.commit()
        
        return {
            "client_secret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


def confirm_payment(order_id: str, payment_intent_id: str, session_id: str, db: Session) -> dict:
    """
    Confirma el estado del pago después de que Stripe redirige al usuario.
    Verifica el Payment Intent con Stripe y actualiza el estado de la orden.
    """
    # 1. Obtener la orden
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = db.query(Order).filter(Order.id == order_id_int).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 2. Verificar que la orden pertenece al usuario/sesión
    if order.session_id != session_id:
        raise HTTPException(status_code=403, detail="Unauthorized - session mismatch")
    
    # 3. Verificar idempotencia - si ya está pagada, retornar OK
    if order.stripe_payment_intent_id == payment_intent_id and order.payment_status == "completed":
        return {
            "status": "paid",
            "order_id": str(order.id)
        }
    
    # 4. Verificar el Payment Intent con Stripe
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # 5. Verificar que el payment_intent corresponde a esta orden
        if payment_intent.metadata.get("order_id") != str(order.id):
            raise HTTPException(status_code=400, detail="Payment intent does not match order")
        
        # 6. Verificar el estado del pago
        if payment_intent.status == "succeeded":
            order.status = "paid"
            order.payment_status = "completed"
            order.paid_at = datetime.utcnow()
            db.commit()
            
            return {
                "status": "paid",
                "order_id": str(order.id)
            }
        
        elif payment_intent.status == "processing":
            order.payment_status = "processing"
            db.commit()
            
            return {
                "status": "processing",
                "order_id": str(order.id)
            }
        
        elif payment_intent.status == "requires_action":
            return {
                "status": "requires_action",
                "order_id": str(order.id)
            }
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Payment not completed: {payment_intent.status}"
            )
            
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict:
    """
    Maneja los webhooks de Stripe para actualizar el estado de las órdenes.
    Este es el método más confiable para confirmar pagos.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Manejar los eventos
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        order_id = payment_intent.metadata.get("order_id")
        
        if order_id:
            order = db.query(Order).filter(Order.id == int(order_id)).first()
            if order:
                # Verificar idempotencia
                if order.payment_status != "completed":
                    order.status = "paid"
                    order.payment_status = "completed"
                    order.paid_at = datetime.utcnow()
                    order.stripe_payment_intent_id = payment_intent.id
                    db.commit()
                    
                    # TODO: Enviar email de confirmación
                    # await send_confirmation_email(order)
    
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        order_id = payment_intent.metadata.get("order_id")
        
        if order_id:
            order = db.query(Order).filter(Order.id == int(order_id)).first()
            if order and order.payment_status != "completed":
                order.payment_status = "failed"
                db.commit()
    
    elif event.type == "charge.refunded":
        charge = event.data.object
        payment_intent_id = charge.payment_intent
        
        if payment_intent_id:
            order = db.query(Order).filter(
                Order.stripe_payment_intent_id == payment_intent_id
            ).first()
            if order:
                order.status = "refunded"
                order.payment_status = "refunded"
                db.commit()
    
    return {"status": "success"}


def get_order_by_payment_intent(payment_intent_id: str, db: Session) -> Optional[Order]:
    """
    Busca una orden por su payment_intent_id de Stripe.
    """
    return db.query(Order).filter(
        Order.stripe_payment_intent_id == payment_intent_id
    ).first()

