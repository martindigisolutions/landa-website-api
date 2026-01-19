import logging
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from models import Product, ProductVariant, Order, OrderItem, Cart, CartItem, User, CombinedOrder
from schemas.checkout import (
    CheckoutOptionsRequest, OrderCreate, 
    ConfirmManualPayment, CartValidationIssue, CheckoutValidationResponse
)
from uuid import uuid4
from typing import Optional, List, Tuple

logger = logging.getLogger("landa-api.checkout")


def _get_cart(db: Session, session_id: Optional[str], user_id: Optional[int]) -> Optional[Cart]:
    """
    Get cart by user_id or session_id.
    Priority: user_id first, then fallback to session_id.
    This handles the case where a guest adds items, then logs in without merging.
    """
    from sqlalchemy.orm import joinedload
    
    cart = None
    
    # Try to find by user_id first with eager loading
    if user_id:
        cart = db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.variant)
        ).filter(Cart.user_id == user_id).first()
    
    # If no user cart found, try session_id (for logged-in users with unmerged guest carts)
    if not cart and session_id:
        cart = db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.variant)
        ).filter(
            Cart.session_id == session_id,
            Cart.user_id == None
        ).first()
    
    return cart


def _get_item_stock(product: Product, variant: Optional[ProductVariant]) -> Tuple[int, bool]:
    """Get stock and is_in_stock for product/variant"""
    if variant:
        return variant.stock or 0, variant.is_in_stock
    return product.stock or 0, product.is_in_stock


def _is_item_orphaned(item: CartItem) -> bool:
    """Check if cart item references deleted product or variant"""
    # Product was deleted
    if item.product is None:
        return True
    # Variant was deleted (variant_id exists but variant is None)
    if item.variant_id is not None and item.variant is None:
        return True
    return False


def _validate_cart_items(cart: Cart, db: Session) -> Tuple[List[CartItem], List[CartValidationIssue]]:
    """
    Validate all cart items and return valid items + any issues found.
    Also cleans up orphaned items (deleted products/variants).
    """
    valid_items = []
    issues = []
    items_to_remove = []
    
    for item in cart.items:
        product = item.product
        variant = item.variant
        
        # Product or variant was deleted
        if _is_item_orphaned(item):
            items_to_remove.append(item)
            if product is None:
                issues.append(CartValidationIssue(
                    type="product_removed",
                    product_id=item.product_id,
                    message="This product is no longer available"
                ))
            else:
                # Variant was deleted
                issues.append(CartValidationIssue(
                    type="variant_removed",
                    product_id=item.product_id,
                    product_name=product.name,
                    variant_id=item.variant_id,
                    message=f"The selected variant of {product.name} is no longer available"
                ))
            continue
        
        stock, is_in_stock = _get_item_stock(product, variant)
        
        # Product/variant is out of stock
        if not is_in_stock or stock <= 0:
            issues.append(CartValidationIssue(
                type="out_of_stock",
                product_id=product.id,
                product_name=product.name,
                variant_id=variant.id if variant else None,
                variant_name=variant.name if variant else None,
                message=f"{product.name}{' - ' + variant.name if variant else ''} is out of stock",
                requested_quantity=item.quantity,
                available_stock=0
            ))
            continue
        
        # Insufficient stock
        if item.quantity > stock:
            issues.append(CartValidationIssue(
                type="insufficient_stock",
                product_id=product.id,
                product_name=product.name,
                variant_id=variant.id if variant else None,
                variant_name=variant.name if variant else None,
                message=f"Only {stock} units of {product.name}{' - ' + variant.name if variant else ''} available",
                requested_quantity=item.quantity,
                available_stock=stock
            ))
            continue
        
        # Item is valid
        valid_items.append(item)
    
    # Clean up orphaned items (deleted products or variants)
    if items_to_remove:
        for orphan in items_to_remove:
            db.delete(orphan)
        db.commit()
    
    return valid_items, issues


def start_checkout_session(
    session_id: Optional[str],
    user: Optional[User],
    db: Session
):
    """
    Start a checkout session using the server-side cart.
    Validates all items in the cart and returns issues if any.
    """
    user_id = user.id if user else None
    
    logger.info(f"start_checkout_session - session_id: {session_id}, user_id: {user_id}")
    
    # Get cart from server
    cart = _get_cart(db, session_id, user_id)
    
    logger.info(f"Cart found: {cart is not None}, items count: {len(cart.items) if cart else 0}")
    
    if not cart or not cart.items:
        logger.warning(f"Cart is empty or not found for user_id={user_id}, session_id={session_id}")
        raise HTTPException(
            status_code=400, 
            detail="Cart is empty"
        )
    
    # Validate all items
    valid_items, issues = _validate_cart_items(cart, db)
    
    checkout_id = session_id or str(uuid4())
    
    # If there are issues, return them so frontend can handle
    if issues:
        return CheckoutValidationResponse(
            valid=False,
            checkout_id=checkout_id,
            issues=issues,
            message="Some items in your cart have issues that need to be resolved"
        )
    
    # All items valid
    return CheckoutValidationResponse(
        valid=True,
        checkout_id=checkout_id,
        issues=[],
        message="Cart validated successfully"
    )


def get_checkout_options(data: CheckoutOptionsRequest, db: Session):
    shipping_options = [
        {
            "id": "standard",
            "label": "Envío estándar",
            "fee": 5.99,
            "delivery_days_min": 1,
            "delivery_days_max": 3
        },
        {
            "id": "free_shipping",
            "label": "Envío gratuito (5 días hábiles)",
            "fee": 0,
            "delivery_days_min": 5,
            "delivery_days_max": 5
        }
    ]

    payment_methods = [
        {"id": "stripe", "label": "Credit/Debit Card"},
        {"id": "zelle", "label": "Zelle"},
        {"id": "cashapp", "label": "Cash App"},
        {"id": "venmo", "label": "Venmo"},
    ]

    if data.shipping_method == "pickup":
        shipping_options = [
            {
                "id": "pickup",
                "label": "Recoger en tienda",
                "fee": 0,
                "delivery_days_min": 1,
                "delivery_days_max": 1
            }
        ]
        payment_methods.append({
            "id": "cash", "label": "Pago en efectivo"
        })

    return {
        "shipping_options": shipping_options,
        "payment_methods": payment_methods
    }

def create_order(
    data: OrderCreate,
    session_id: Optional[str],
    user: Optional[User],
    db: Session
):
    """
    Create an order using the server-side cart.
    
    Requires a lock_token from POST /cart/lock to ensure:
    - Stock is reserved and validated
    - Totals are frozen at lock time
    - Safe concurrent order creation
    """
    from services.cart_lock_service import use_lock
    
    # lock_token is required
    if not data.lock_token:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "lock_token_required",
                "message": "lock_token is required. Call POST /cart/lock first to get a lock token."
            }
        )
    
    user_id = user.id if user else None
    
    # Get cart from server
    cart = _get_cart(db, session_id, user_id)
    
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Use lock_token to create order
    success, error, lock, was_expired = use_lock(db, data.lock_token, validate_stock_if_expired=True)
    
    if not success:
        # Before rejecting, check if order already exists for this payment_intent_id
        if lock and lock.stripe_payment_intent_id:
            existing_order = db.query(Order).filter(
                Order.stripe_payment_intent_id == lock.stripe_payment_intent_id
            ).first()
            if existing_order:
                # Order already exists, return success with existing order
                logger.info(f"Order already exists for PaymentIntent {lock.stripe_payment_intent_id}: order #{existing_order.id}")
                return {
                    "success": True,
                    "order_id": str(existing_order.id),
                    "order_number": f"ORD-{existing_order.id:06d}",
                    "status": existing_order.status,
                    "total": existing_order.total,
                    "items_count": len(existing_order.items),
                    "message": "Order already created"
                }
        
        # Special handling for expired lock without stock - payment was successful but stock unavailable
        if error == "lock_expired_no_stock":
            raise HTTPException(
                status_code=409,  # Conflict - payment succeeded but order cannot be created
                detail={
                    "error": "lock_expired_no_stock",
                    "message": "Your payment was processed, but the items are no longer available. A refund will be processed automatically.",
                    "payment_succeeded": True,
                    "requires_refund": True,
                    "success": False
                }
            )
        
        error_messages = {
            "lock_not_found": "Lock not found",
            "lock_already_used": "This lock was already used to create an order",
            "lock_expired": "Lock expired. Please try again.",
            "lock_cancelled": "Lock was cancelled"
        }
        raise HTTPException(
            status_code=400,
            detail={
                "error": error,
                "message": error_messages.get(error, "Lock validation failed"),
                "success": False
            }
        )
    
    # Use frozen totals from lock
    total = lock.total
    payment_method = cart.payment_method or "stripe"
    shipping_method = "pickup" if cart.is_pickup else "delivery"
    
    # Build address from cart (include name, phone, email from checkout form)
    address_data = {
        "first_name": cart.shipping_first_name or None,
        "last_name": cart.shipping_last_name or None,
        "phone": cart.shipping_phone or None,
        "email": cart.shipping_email or None,
        "street": cart.shipping_street or "",
        "apartment": cart.shipping_apartment or "",
        "city": cart.shipping_city or "",
        "state": cart.shipping_state or "",
        "zip": cart.shipping_zipcode or "",
        "country": cart.shipping_country or "US"
    }
    
    # Prepare order items from reservations
    order_items_data = []
    for reservation in lock.reservations:
        product = reservation.product
        variant = reservation.variant
        
        order_items_data.append({
            "product_id": reservation.product_id,
            "variant_id": reservation.variant_id,
            "variant_name": variant.name if variant else None,
            "quantity": reservation.quantity,
            "price": reservation.unit_price
        })
    
    # Determine order status based on payment method
    # IMPORTANT: For Stripe, the frontend already confirmed payment, so we start as "processing_payment"
    # The webhook will change it to "paid" when Stripe confirms
    if payment_method == "stripe":
        if lock.stripe_payment_intent_id:
            # PaymentIntent was created and frontend confirmed payment
            # Order starts as "processing_payment" until webhook confirms payment
            order_status = "processing_payment"
            payment_status = "pending"  # Will be updated to "completed" by webhook
            logger.info(f"Order created with Stripe PaymentIntent {lock.stripe_payment_intent_id}. Status: processing_payment, waiting for webhook confirmation.")
        else:
            # No PaymentIntent - Stripe not configured or failed
            # This should not happen, but handle gracefully
            logger.warning(f"Stripe payment selected but no PaymentIntent found for lock {lock.token}. Marking as processing_payment.")
            order_status = "processing_payment"
            payment_status = "pending"
    else:
        # Non-Stripe payment methods require manual verification
        order_status = "pending_verification"
        payment_status = "pending"
    
    # Create order with frozen totals from lock
    order = Order(
        session_id=session_id,
        user_id=user_id,
        shipping_method=shipping_method,
        payment_method=payment_method,
        address=address_data,
        subtotal=lock.subtotal,
        tax=lock.tax,
        shipping_fee=lock.shipping_fee,
        total=total,  # Use lock.total which matches subtotal + tax + shipping_fee
        status=order_status,
        payment_status=payment_status,
        stripe_payment_intent_id=lock.stripe_payment_intent_id
    )
    db.add(order)
    db.flush()  # Get order.id
    
    # Update PaymentIntent metadata with order_id for webhook lookup
    if lock.stripe_payment_intent_id and payment_method == "stripe":
        try:
            import stripe
            from config import STRIPE_SECRET_KEY
            if STRIPE_SECRET_KEY:
                stripe.api_key = STRIPE_SECRET_KEY
                stripe.PaymentIntent.modify(
                    lock.stripe_payment_intent_id,
                    metadata={
                        "order_id": str(order.id),
                        "lock_token": lock.token,
                        "cart_id": str(lock.cart_id)
                    }
                )
                logger.info(f"Updated PaymentIntent {lock.stripe_payment_intent_id} metadata with order_id {order.id}")
                
                # IMPORTANT: Check if PaymentIntent is already succeeded (webhook may have arrived before order creation)
                # If so, update order status immediately instead of waiting for webhook
                try:
                    import stripe
                    from config import STRIPE_SECRET_KEY
                    if STRIPE_SECRET_KEY:
                        stripe.api_key = STRIPE_SECRET_KEY
                        pi = stripe.PaymentIntent.retrieve(lock.stripe_payment_intent_id)
                        if pi.status == "succeeded" and order.status == "processing_payment":
                            logger.info(f"PaymentIntent {lock.stripe_payment_intent_id} already succeeded, updating order #{order.id} to paid immediately")
                            order.status = "paid"
                            order.payment_status = "completed"
                            from datetime import datetime
                            order.paid_at = datetime.utcnow()
                            db.commit()
                            logger.info(f"Order #{order.id} updated to paid immediately (webhook arrived before order creation)")
                except Exception as e:
                    logger.warning(f"Failed to check PaymentIntent status: {e}")
                    # Non-critical, webhook will handle it
        except Exception as e:
            logger.warning(f"Failed to update PaymentIntent metadata: {e}")
            # Non-critical, webhook can still find order by stripe_payment_intent_id
    
    # Create order items and deduct stock permanently
    # OPTIMIZATION: Batch load all products and variants to avoid N+1 queries
    variant_ids = [item["variant_id"] for item in order_items_data if item["variant_id"]]
    product_ids = [item["product_id"] for item in order_items_data if not item["variant_id"]]
    
    # Load all variants in one query
    variants_dict = {}
    if variant_ids:
        variants = db.query(ProductVariant).filter(ProductVariant.id.in_(variant_ids)).all()
        variants_dict = {v.id: v for v in variants}
    
    # Load all products in one query
    products_dict = {}
    if product_ids:
        products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        products_dict = {p.id: p for p in products}
    
    # Create order items and deduct stock
    for item_data in order_items_data:
        db.add(OrderItem(
            order_id=order.id,
            product_id=item_data["product_id"],
            variant_id=item_data["variant_id"],
            variant_name=item_data["variant_name"],
            quantity=item_data["quantity"],
            price=item_data["price"]
        ))
        
        # Deduct stock (was reserved, now permanent) - using pre-loaded objects
        if item_data["variant_id"]:
            variant = variants_dict.get(item_data["variant_id"])
            if variant:
                variant.stock = max(0, (variant.stock or 0) - item_data["quantity"])
                if variant.stock <= 0:
                    variant.is_in_stock = False
        else:
            product = products_dict.get(item_data["product_id"])
            if product:
                product.stock = max(0, (product.stock or 0) - item_data["quantity"])
                if product.stock <= 0:
                    product.is_in_stock = False
    
    # Clear cart after successful order
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    
    # Clear cart shipping/payment info for next order
    cart.payment_method = None
    
    db.commit()
    
    return {
        "success": True,
        "order_id": str(order.id),
        "order_number": f"ORD-{order.id:06d}",
        "status": order.status,
        "total": total,
        "items_count": len(order_items_data),
        "message": "Order created successfully"
    }


def confirm_manual_payment(data: ConfirmManualPayment, db: Session):
    order_id_str = data.order_id
    try:
        order_id = int(order_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ["pending_payment", "processing_payment"]:
        raise HTTPException(status_code=400, detail="Order cannot be marked as paid in current state")

    order.status = "awaiting_verification"
    db.commit()

    return {"status": "awaiting_verification"}

def get_payment_details(order_id: str, db: Session):
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = db.query(Order).filter(Order.id == order_id_int).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    total = f"${order.total:.2f}"
    if order.payment_method == "zelle":
        html = f"""
        <p>Tu orden <strong>#{order_id}</strong> ha sido creada.<br>
        Envíe su pago de <strong>{total}</strong> a través de <strong>Zelle</strong> al número:<br>
        <strong>555-123-4567</strong><br>
        En las notas, escriba: <strong>Order {order_id}</strong></p>
        """
        return {"payment_type": "zelle", "instructions": html.strip()}

    if order.payment_method == "cashapp":
        html = f"""
        <p>Tu orden <strong>#{order_id}</strong> ha sido creada.<br>
        Envíe su pago de <strong>{total}</strong> a través de <strong>CashApp</strong> al usuario:<br>
        <strong>$beautystore</strong><br>
        En las notas, escriba: <strong>Order {order_id}</strong></p>
        """
        return {"payment_type": "cashapp", "instructions": html.strip()}

    if order.payment_method == "venmo":
        html = f"""
        <p>Tu orden <strong>#{order_id}</strong> ha sido creada.<br>
        Envíe su pago de <strong>{total}</strong> a través de <strong>Venmo</strong> al usuario:<br>
        <strong>@beautystore</strong><br>
        En las notas, escriba: <strong>Order {order_id}</strong></p>
        """
        return {"payment_type": "venmo", "instructions": html.strip()}

    if order.payment_method == "cash":
        return {
            "payment_type": "cash",
            "instructions": "<p>Tu orden ha sido creada.<br>Recoge tu pedido y paga en efectivo en tienda.</p>"
        }

    if order.payment_method == "stripe":
        return {
            "payment_type": "stripe",
            "instructions": None,
            "order_id": str(order.id),
            "total": order.total,
            "requires_payment_intent": True
        }

    raise HTTPException(status_code=400, detail="No instructions available for this method")

def get_order_list(db: Session, user_id: Optional[int] = None):
    """Get list of orders for a user, including shipment information"""
    from schemas.checkout import OrderSummary, ShipmentInfo
    
    query = db.query(Order)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Convert to OrderSummary with shipments
    result = []
    for order in orders:
        shipments = [
            ShipmentInfo(
                id=shipment.id,
                tracking_number=shipment.tracking_number,
                tracking_url=shipment.tracking_url,
                carrier=shipment.carrier,
                shipped_at=shipment.shipped_at,
                delivered_at=shipment.delivered_at,
                status="delivered" if shipment.delivered_at else "in_transit" if shipment.shipped_at else "pending"
            )
            for shipment in sorted(order.shipments, key=lambda s: s.created_at)
        ]
        
        # Get combined orders info
        combined_with = None
        if order.combined_group_id:
            combined_orders = db.query(CombinedOrder).filter(
                CombinedOrder.combined_group_id == order.combined_group_id
            ).all()
            combined_with = [co.order_id for co in combined_orders if co.order_id != order.id]
        
        result.append(OrderSummary(
            id=order.id,
            status=order.status,
            payment_method=order.payment_method,
            shipping_method=order.shipping_method,
            total=order.total,
            created_at=order.created_at,
            combined=order.combined or False,
            combined_with=combined_with,
            shipments=shipments
        ))
    
    return result


def get_order_detail(order_id: str, user_id: str, db: Session):
    """Obtener el detalle completo de una orden específica."""
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = db.query(Order).filter(Order.id == order_id_int).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verificar que el usuario tiene permiso para ver esta orden
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if order.user_id != user_id_int:
        raise HTTPException(status_code=403, detail="You don't have permission to view this order")
    
    # Use stored breakdown values if available, otherwise calculate (for old orders)
    if order.subtotal is not None:
        subtotal = order.subtotal
        tax = order.tax or 0.0
        shipping_cost = order.shipping_fee or 0.0
    else:
        # Fallback calculation for old orders (before breakdown was stored)
        subtotal = sum(item.price * item.quantity for item in order.items)
        
        # Determine shipping cost based on method
        shipping_cost = 0.0
        if order.shipping_method == "standard":
            shipping_cost = 5.99
        elif order.shipping_method in ["free_shipping", "pickup"]:
            shipping_cost = 0.0
        
        # Tax calculation for old orders (default to 0)
        tax = 0.0
    
    # Construir los items con información del producto y variante
    items_detail = []
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first() if item.variant_id else None
        
        # Product name (parent product only)
        product_name = product.name if product else "Unknown Product"
        
        # Variant name (from frozen data or current variant)
        variant_name = item.variant_name or (variant.name if variant else None)
        
        # Use variant image if available, otherwise product image
        image_url = None
        if variant and variant.image_url:
            image_url = variant.image_url
        elif product:
            image_url = product.image_url
        
        items_detail.append({
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "product_name": product_name,
            "variant_name": variant_name,
            "quantity": item.quantity,
            "price": item.price,
            "image_url": image_url
        })
    
    # Construir la dirección
    address_data = order.address if order.address else {}
    address = {
        "city": address_data.get("city", ""),
        "state": address_data.get("state", ""),
        "zip": address_data.get("zip", ""),
        "country": address_data.get("country", ""),
        "street": address_data.get("street"),
        "apartment": address_data.get("apartment") or None  # Convert empty string to None
    } if address_data else None
    
    # Get shipments for this order
    from schemas.checkout import ShipmentDetail
    shipments = []
    for shipment in sorted(order.shipments, key=lambda s: s.created_at):
        shared_with = None
        if shipment.combined_group_id:
            combined_orders_for_shipment = db.query(CombinedOrder).filter(
                CombinedOrder.combined_group_id == shipment.combined_group_id
            ).all()
            shared_with = [co.order_id for co in combined_orders_for_shipment]
        
        shipments.append(ShipmentDetail(
            id=shipment.id,
            tracking_number=shipment.tracking_number,
            tracking_url=shipment.tracking_url,
            carrier=shipment.carrier,
            shipped_at=shipment.shipped_at,
            estimated_delivery=shipment.estimated_delivery,
            delivered_at=shipment.delivered_at,
            notes=shipment.notes,
            shared_with_orders=shared_with
        ))
    
    # Get combined orders info
    combined_with = None
    if order.combined_group_id:
        combined_orders = db.query(CombinedOrder).filter(
            CombinedOrder.combined_group_id == order.combined_group_id
        ).all()
        combined_with = [co.order_id for co in combined_orders if co.order_id != order.id]
    
    return {
        "order_id": str(order.id),
        "status": order.status,
        "payment_status": order.payment_status or "pending",  # Include payment_status
        "total": order.total,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "tax": tax,
        "items": items_detail,
        "combined": order.combined or False,
        "combined_with": combined_with,
        "address": address,
        "shipping_method": order.shipping_method,
        "payment_method": order.payment_method,
        "stripe_payment_intent_id": order.stripe_payment_intent_id,  # Include for Stripe orders
        "tracking_number": getattr(order, 'tracking_number', None),  # Deprecated, kept for backwards compatibility
        "tracking_url": getattr(order, 'tracking_url', None),  # Deprecated, kept for backwards compatibility
        "shipped_at": getattr(order, 'shipped_at', None),  # Deprecated, kept for backwards compatibility
        "shipments": [s.model_dump() for s in shipments],  # New: list of all shipments
        "created_at": order.created_at,
        "paid_at": order.paid_at  # Include paid_at timestamp
    }


def update_order_address(order_id: str, user_id: str, address_data: dict, db: Session):
    """Actualizar la dirección de envío de una orden."""
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    order = db.query(Order).filter(Order.id == order_id_int).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verificar que el usuario tiene permiso
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    if order.user_id != user_id_int:
        raise HTTPException(status_code=403, detail="You don't have permission to modify this order")
    
    # Verificar que el estado permite modificación
    allowed_statuses = ["pending_payment", "processing_payment", "awaiting_verification"]
    if order.status not in allowed_statuses:
        raise HTTPException(
            status_code=409, 
            detail=f"Cannot update address. Order status '{order.status}' does not allow modifications. Address can only be updated when status is 'pending_payment', 'processing_payment', or 'awaiting_verification'."
        )
    
    # Actualizar la dirección
    new_address = {
        "city": address_data["city"],
        "state": address_data["state"],
        "zip": address_data["zip"],
        "country": address_data["country"],
        "street": address_data.get("street"),
        "apartment": address_data.get("apartment")
    }
    
    order.address = new_address
    db.commit()
    
    return {
        "success": True,
        "message": "Address updated successfully",
        "order_id": str(order.id)
    }