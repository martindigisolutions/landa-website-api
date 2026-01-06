"""
Cart Lock Service for checkout stock reservation system
"""
import secrets
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from models import (
    Cart, CartItem, CartLock, StockReservation, 
    Product, ProductVariant, User, LOCK_EXPIRATION_MINUTES
)
from schemas.cart import (
    LockCartResponse, ReleaseLockResponse, UnavailableItem, 
    PaymentIntentInfo, UpdatePaymentMethodResponse
)

logger = logging.getLogger("landa-api.cart-lock")


def _generate_lock_token() -> str:
    """Generate a unique lock token"""
    return f"lock_{secrets.token_urlsafe(16)}"


def _get_available_stock(product: Product, variant: Optional[ProductVariant], db: Session) -> int:
    """
    Get available stock (total - reserved).
    Reserved = sum of quantities in active locks for this product/variant.
    """
    if variant:
        total_stock = variant.stock or 0
        # Get reserved quantity from active locks
        reserved = db.query(StockReservation).join(CartLock).filter(
            StockReservation.variant_id == variant.id,
            CartLock.status == "active",
            CartLock.expires_at > datetime.utcnow()
        ).with_entities(func.sum(StockReservation.quantity)).scalar() or 0
    else:
        total_stock = product.stock or 0
        # Get reserved quantity from active locks (products without variants)
        reserved = db.query(StockReservation).join(CartLock).filter(
            StockReservation.product_id == product.id,
            StockReservation.variant_id == None,
            CartLock.status == "active",
            CartLock.expires_at > datetime.utcnow()
        ).with_entities(func.sum(StockReservation.quantity)).scalar() or 0
    
    return max(0, total_stock - reserved)


def _get_unit_price(product: Product, variant: Optional[ProductVariant]) -> float:
    """Get current unit price"""
    if variant:
        if variant.sale_price is not None:
            return variant.sale_price
        if variant.regular_price is not None:
            return variant.regular_price
    if product.sale_price is not None:
        return product.sale_price
    return product.regular_price or 0


def get_active_lock(db: Session, cart_id: int) -> Optional[CartLock]:
    """Get active lock for a cart if exists and not expired"""
    return db.query(CartLock).filter(
        CartLock.cart_id == cart_id,
        CartLock.status == "active",
        CartLock.expires_at > datetime.utcnow()
    ).first()


def cancel_existing_locks(db: Session, cart_id: int) -> int:
    """Cancel all active locks for a cart and release stock"""
    locks = db.query(CartLock).filter(
        CartLock.cart_id == cart_id,
        CartLock.status == "active"
    ).all()
    
    count = 0
    for lock in locks:
        lock.status = "cancelled"
        count += 1
        logger.info(f"Cancelled lock {lock.token} for cart {cart_id}")
    
    if count > 0:
        db.commit()
    
    return count


def update_payment_method(
    db: Session,
    cart: Cart,
    payment_method: str
) -> UpdatePaymentMethodResponse:
    """Update payment method in cart"""
    valid_methods = ["stripe", "zelle", "cashapp", "venmo"]
    
    if payment_method.lower() not in valid_methods:
        return UpdatePaymentMethodResponse(
            success=False,
            payment_method="",
            message=f"Invalid payment method. Must be one of: {', '.join(valid_methods)}"
        )
    
    cart.payment_method = payment_method.lower()
    cart.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Payment method set to '{payment_method}' for cart {cart.id}")
    
    return UpdatePaymentMethodResponse(
        success=True,
        payment_method=cart.payment_method,
        message="Payment method saved"
    )


def create_lock(
    db: Session,
    cart: Cart,
    create_stripe_intent: bool = False
) -> LockCartResponse:
    """
    Create a lock on the cart, reserving stock for checkout.
    
    Steps:
    1. Validate cart has items and required info
    2. Cancel any existing locks for this cart
    3. Check stock availability for all items
    4. Create lock and stock reservations
    5. Optionally create Stripe PaymentIntent
    """
    # Validate cart has items
    if not cart.items:
        return LockCartResponse(
            success=False,
            error="empty_cart",
            message="Cart is empty"
        )
    
    # Validate shipping address (for delivery) or pickup flag
    if not cart.is_pickup:
        if not cart.shipping_city or not cart.shipping_state or not cart.shipping_zipcode:
            return LockCartResponse(
                success=False,
                error="missing_address",
                message="Shipping address is required for delivery orders"
            )
    
    # Validate payment method
    if not cart.payment_method:
        return LockCartResponse(
            success=False,
            error="missing_payment_method",
            message="Payment method must be selected before checkout"
        )
    
    # Cancel any existing locks
    cancel_existing_locks(db, cart.id)
    
    # Check stock availability
    unavailable_items: List[UnavailableItem] = []
    items_to_reserve: List[Tuple[CartItem, int, float]] = []  # (item, available, price)
    
    for item in cart.items:
        product = item.product
        variant = item.variant
        
        # Skip deleted products/variants
        if product is None or (item.variant_id and variant is None):
            continue
        
        available = _get_available_stock(product, variant, db)
        price = _get_unit_price(product, variant)
        
        if available < item.quantity:
            unavailable_items.append(UnavailableItem(
                product_id=product.id,
                variant_id=variant.id if variant else None,
                product_name=product.name,
                variant_name=variant.name if variant else None,
                requested=item.quantity,
                available=available
            ))
        else:
            items_to_reserve.append((item, available, price))
    
    # If any items unavailable, return error
    if unavailable_items:
        return LockCartResponse(
            success=False,
            error="stock_unavailable",
            message="Some products do not have sufficient stock",
            unavailable_items=unavailable_items
        )
    
    # Calculate totals
    subtotal = sum(price * item.quantity for item, _, price in items_to_reserve)
    
    # Import here to avoid circular imports
    from services.shipping_service import calculate_shipping_cost
    from services.tax_service import TaxService
    from schemas.settings import TaxAddress
    
    # Calculate shipping with error handling
    cart_items_for_shipping = [
        {"product_id": item.product_id, "variant_id": item.variant_id, "quantity": item.quantity}
        for item, _, _ in items_to_reserve
    ]
    try:
        shipping_fee = calculate_shipping_cost(cart_items_for_shipping, db)
    except Exception as e:
        logger.error(f"Error calculating shipping: {e}")
        shipping_fee = 0.0  # Fallback to free shipping on error
    
    # Calculate tax with error handling
    tax_amount = 0.0
    try:
        tax_service = TaxService(db)
        tax_address = None
        if cart.shipping_city and cart.shipping_state and cart.shipping_zipcode:
            tax_address = TaxAddress(
                street_number="",
                street_name=cart.shipping_street or "",
                city=cart.shipping_city,
                state=cart.shipping_state,
                zipcode=cart.shipping_zipcode
            )
        
        tax_result = tax_service.calculate_tax(
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            address=tax_address,
            is_pickup=cart.is_pickup or False
        )
        tax_amount = tax_result.tax_amount if tax_result.success else 0.0
    except Exception as e:
        logger.error(f"Error calculating tax: {e}")
        tax_amount = 0.0  # Fallback to no tax on error
    
    total = round(subtotal + shipping_fee + tax_amount, 2)
    
    # Create lock
    lock_token = _generate_lock_token()
    expires_at = datetime.utcnow() + timedelta(minutes=LOCK_EXPIRATION_MINUTES)
    
    lock = CartLock(
        cart_id=cart.id,
        token=lock_token,
        status="active",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax=tax_amount,
        total=total,
        expires_at=expires_at
    )
    db.add(lock)
    db.flush()  # Get lock.id
    
    # Create stock reservations
    for item, _, price in items_to_reserve:
        reservation = StockReservation(
            lock_id=lock.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_price=price
        )
        db.add(reservation)
    
    # Create Stripe PaymentIntent if needed
    payment_intent_info = None
    if cart.payment_method == "stripe":
        try:
            import stripe
            import os
            
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            
            if stripe.api_key:
                intent = stripe.PaymentIntent.create(
                    amount=int(total * 100),  # Convert to cents
                    currency="usd",
                    metadata={
                        "lock_token": lock_token,
                        "cart_id": str(cart.id)
                    }
                )
                lock.stripe_payment_intent_id = intent.id
                payment_intent_info = PaymentIntentInfo(
                    client_secret=intent.client_secret,
                    amount=int(total * 100),
                    currency="usd"
                )
                logger.info(f"Created Stripe PaymentIntent {intent.id} for lock {lock_token}")
            else:
                logger.warning("STRIPE_SECRET_KEY not configured, skipping PaymentIntent creation")
        except Exception as e:
            logger.error(f"Failed to create Stripe PaymentIntent: {e}")
            # Continue without Stripe intent - can be created later
    
    db.commit()
    
    expires_in_seconds = int((expires_at - datetime.utcnow()).total_seconds())
    
    logger.info(f"Created lock {lock_token} for cart {cart.id}, expires in {expires_in_seconds}s")
    
    return LockCartResponse(
        success=True,
        lock_token=lock_token,
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds,
        payment_intent=payment_intent_info
    )


def release_lock(
    db: Session,
    lock_token: str
) -> ReleaseLockResponse:
    """
    Release/cancel a lock and free reserved stock.
    Always returns success (idempotent for sendBeacon).
    """
    lock = db.query(CartLock).filter(CartLock.token == lock_token).first()
    
    if not lock:
        logger.info(f"Lock {lock_token} not found (already released or invalid)")
        return ReleaseLockResponse(
            success=True,
            message="Lock not found or already released"
        )
    
    if lock.status != "active":
        logger.info(f"Lock {lock_token} already {lock.status}")
        return ReleaseLockResponse(
            success=True,
            message=f"Lock already {lock.status}"
        )
    
    lock.status = "cancelled"
    db.commit()
    
    logger.info(f"Released lock {lock_token}")
    
    return ReleaseLockResponse(
        success=True,
        message="Lock released, stock freed"
    )


def use_lock(
    db: Session,
    lock_token: str
) -> Tuple[bool, str, Optional[CartLock]]:
    """
    Mark a lock as used (when creating order).
    Returns (success, error_message, lock)
    """
    lock = db.query(CartLock).filter(CartLock.token == lock_token).first()
    
    if not lock:
        return False, "lock_not_found", None
    
    if lock.status == "used":
        return False, "lock_already_used", None
    
    if lock.status == "expired" or lock.expires_at < datetime.utcnow():
        lock.status = "expired"
        db.commit()
        return False, "lock_expired", None
    
    if lock.status == "cancelled":
        return False, "lock_cancelled", None
    
    # Mark as used
    lock.status = "used"
    lock.used_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Lock {lock_token} used for order creation")
    
    return True, "", lock


def cleanup_expired_locks(db: Session) -> int:
    """
    Mark expired locks as expired.
    Run this periodically (every 1-5 minutes).
    """
    now = datetime.utcnow()
    
    expired_locks = db.query(CartLock).filter(
        CartLock.status == "active",
        CartLock.expires_at < now
    ).all()
    
    count = 0
    for lock in expired_locks:
        lock.status = "expired"
        count += 1
        logger.info(f"Expired lock {lock.token}")
    
    if count > 0:
        db.commit()
        logger.info(f"Cleaned up {count} expired locks")
    
    return count

