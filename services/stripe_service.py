import stripe
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
from typing import Optional

from models import Order
from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET

# Configure Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Logger for webhook events
logger = logging.getLogger("landa-api.stripe-webhook")


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
    import logging
    logger = logging.getLogger("landa-api.stripe-webhook")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Webhook event received: {event.type} [id: {event.id}]")
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Manejar los eventos
    if event.type == "payment_intent.succeeded":
        logger.info(f"Processing payment_intent.succeeded event")
        try:
            payment_intent = event.data.object
            payment_intent_id = payment_intent.id
            
            # Try to find order by PaymentIntent ID (most reliable)
            logger.debug(f"Looking for order with PaymentIntent ID: {payment_intent_id}")
            order = db.query(Order).filter(Order.stripe_payment_intent_id == payment_intent_id).first()
            
            if order:
                logger.info(f"Found order #{order.id} by PaymentIntent ID")
            else:
                logger.debug(f"Order not found by PaymentIntent ID, trying metadata...")
            
            # Fallback: try to find by order_id in metadata (for legacy orders)
            if not order:
                order_id = payment_intent.metadata.get("order_id")
                if order_id:
                    logger.debug(f"Trying to find order by order_id from metadata: {order_id}")
                    try:
                        order = db.query(Order).filter(Order.id == int(order_id)).first()
                        if order:
                            logger.info(f"Found order #{order.id} by order_id from metadata")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid order_id in metadata: {order_id}, error: {e}")
            
            # Fallback: try to find by lock_token in metadata (for new flow)
            # Note: This only works if the order was already created (order_id would be in lock or metadata)
            if not order:
                lock_token = payment_intent.metadata.get("lock_token")
                if lock_token:
                    logger.debug(f"Trying to find order by lock_token from metadata: {lock_token}")
                    try:
                        from models import CartLock
                        lock = db.query(CartLock).filter(CartLock.token == lock_token).first()
                        if lock:
                            # CartLock doesn't have order_id directly, but we can check if order exists
                            # by searching for orders with this PaymentIntent ID (which should be set when order is created)
                            # Or wait for order_id to be added to PaymentIntent metadata
                            logger.debug(f"Found lock {lock_token}, but order may not be created yet")
                            # The order will be created later and PaymentIntent metadata will be updated with order_id
                            # So we'll catch it on the next webhook or when order_id is in metadata
                        else:
                            logger.debug(f"Lock not found for token: {lock_token}")
                    except Exception as e:
                        logger.error(f"Error finding order by lock_token {lock_token}: {e}")
            
            if order:
                # Verificar idempotencia - solo actualizar si no está ya pagada
                if order.status != "paid":
                    logger.info(f"Updating order #{order.id} from {order.status} to paid")
                    order.status = "paid"
                    order.payment_status = "completed"
                    order.paid_at = datetime.utcnow()
                    order.stripe_payment_intent_id = payment_intent_id  # Ensure it's set
                    db.commit()
                    logger.info(f"Order #{order.id} updated successfully: status=paid, payment_status=completed, paid_at={order.paid_at}")
                    
                    # TODO: Enviar email de confirmación
                    # await send_confirmation_email(order)
                else:
                    logger.info(f"Order #{order.id} already has status=paid, skipping update (idempotent)")
            else:
                logger.warning(f"Order not found for PaymentIntent {payment_intent_id}. Metadata: {payment_intent.metadata}")
        except Exception as e:
            logger.error(f"Error processing payment_intent.succeeded: {e}", exc_info=True)
            # No re-raise - we don't want to return 500 for webhook processing errors
            # Stripe will retry if needed
    
    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object
        payment_intent_id = payment_intent.id
        
        # Try to find order by PaymentIntent ID (most reliable)
        order = db.query(Order).filter(Order.stripe_payment_intent_id == payment_intent_id).first()
        
        # Fallback: try to find by order_id in metadata
        if not order:
            order_id = payment_intent.metadata.get("order_id")
            if order_id:
                order = db.query(Order).filter(Order.id == int(order_id)).first()
        
        # Fallback: try to find by lock_token in metadata
        if not order:
            lock_token = payment_intent.metadata.get("lock_token")
            if lock_token:
                from models import CartLock
                lock = db.query(CartLock).filter(CartLock.token == lock_token).first()
                if lock and lock.order_id:
                    order = db.query(Order).filter(Order.id == lock.order_id).first()
        
        if order and order.status != "paid":
            # Only update if not already paid (idempotent)
            logger.info(f"Updating order #{order.id} to payment_failed")
            order.status = "payment_failed"
            order.payment_status = "failed"
            
            # IMPORTANT: Restore stock when payment fails
            # Stock was deducted when order was created, so we need to return it
            try:
                from models import OrderItem, Product, ProductVariant
                for order_item in order.items:
                    if order_item.variant_id:
                        variant = db.query(ProductVariant).filter(ProductVariant.id == order_item.variant_id).first()
                        if variant:
                            variant.stock = (variant.stock or 0) + order_item.quantity
                            if variant.stock > 0:
                                variant.is_in_stock = True
                            logger.debug(f"Restored {order_item.quantity} units to variant {variant.id} (product: {variant.product_id})")
                    else:
                        product = db.query(Product).filter(Product.id == order_item.product_id).first()
                        if product:
                            product.stock = (product.stock or 0) + order_item.quantity
                            if product.stock > 0:
                                product.is_in_stock = True
                            logger.debug(f"Restored {order_item.quantity} units to product {product.id}")
                logger.info(f"Stock restored for order #{order.id}")
            except Exception as e:
                logger.error(f"Error restoring stock for order #{order.id}: {e}", exc_info=True)
                # Continue anyway - stock restoration failure shouldn't block order status update
            
            db.commit()
            logger.info(f"Order #{order.id} marked as payment_failed and stock restored")
    
    elif event.type == "charge.succeeded":
        # charge.succeeded is also a valid indicator of successful payment
        # This can arrive before or instead of payment_intent.succeeded
        logger.info(f"Processing charge.succeeded event")
        charge = event.data.object
        payment_intent_id = charge.payment_intent
        
        if payment_intent_id:
            # Try to find order by PaymentIntent ID
            order = db.query(Order).filter(
                Order.stripe_payment_intent_id == payment_intent_id
            ).first()
            
            if order:
                # Only update if not already paid (idempotent)
                if order.status != "paid":
                    logger.info(f"Updating order #{order.id} from {order.status} to paid via charge.succeeded")
                    order.status = "paid"
                    order.payment_status = "completed"
                    order.paid_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Order #{order.id} updated successfully via charge.succeeded: status=paid")
                else:
                    logger.info(f"Order #{order.id} already has status=paid, skipping update (idempotent)")
            else:
                logger.warning(f"Order not found for PaymentIntent {payment_intent_id} in charge.succeeded")
    
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

