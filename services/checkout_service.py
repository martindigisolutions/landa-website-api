from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Product, Order, OrderItem
from schemas.checkout import CheckoutSessionCreate, CheckoutOptionsRequest, OrderCreate, ConfirmManualPayment
from uuid import uuid4
from typing import Optional

def start_checkout_session(data: CheckoutSessionCreate, db: Session):
    for item in data.products:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product or not product.is_in_stock:
            raise HTTPException(status_code=400, detail=f"Product {item.product_id} not available")

    checkout_id = data.session_id or str(uuid4())

    return {
        "checkout_id": checkout_id,
        "status": "draft"
    }


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
        {"id": "zelle", "label": "Zelle (0% Fee)"},
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

def create_order(data: OrderCreate, db: Session):
    valid_methods = ["stripe", "zelle", "cashapp", "venmo", "credit_card", "cash"]
    if data.payment_method not in valid_methods:
        raise HTTPException(status_code=400, detail="Invalid payment method")

    total = 0.0
    for item in data.products:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        price = product.sale_price or product.regular_price
        total += price * item.quantity

    order = Order(
        session_id=data.session_id,
        user_id=data.user_id,
        shipping_method=data.shipping_method,
        payment_method=data.payment_method,
        address=data.address.dict(),
        total=total,
        status="pending_payment"
    )
    db.add(order)
    db.flush()

    for item in data.products:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        price = product.sale_price or product.regular_price
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=price
        ))

    db.commit()

    return {
        "order_id": f"{order.id}",
        "status": "pending_payment"
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

    if order.status != "pending_payment":
        raise HTTPException(status_code=400, detail="Order cannot be marked as paid in current state")

    order.status = "awaiting_verification"
    db.commit()

    return {"status": "awaiting_verification"}

def get_payment_details(order_id: str, db: Session):
    order = db.query(Order).filter(Order.id == order_id).first()
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
    query = db.query(Order)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    return query.order_by(Order.created_at.desc()).all()


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
    
    # Calcular subtotal, shipping_cost y tax
    subtotal = sum(item.price * item.quantity for item in order.items)
    
    # Determinar el costo de envío basado en el método
    shipping_cost = 0.0
    if order.shipping_method == "standard":
        shipping_cost = 5.99
    elif order.shipping_method in ["free_shipping", "pickup"]:
        shipping_cost = 0.0
    
    # Por ahora, tax = 0 (puede ajustarse según reglas de negocio)
    tax = 0.0
    
    # Construir los items con información del producto
    items_detail = []
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        items_detail.append({
            "product_id": item.product_id,
            "name": product.name if product else "Unknown Product",
            "quantity": item.quantity,
            "price": item.price,
            "image_url": product.image_url if product else None
        })
    
    # Construir la dirección
    address_data = order.address if order.address else {}
    address = {
        "city": address_data.get("city", ""),
        "state": address_data.get("state", ""),
        "zip": address_data.get("zip", ""),
        "country": address_data.get("country", ""),
        "street": address_data.get("street"),
        "apartment": address_data.get("apartment")
    } if address_data else None
    
    return {
        "order_id": str(order.id),
        "status": order.status,
        "total": order.total,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "tax": tax,
        "items": items_detail,
        "address": address,
        "shipping_method": order.shipping_method,
        "payment_method": order.payment_method,
        "created_at": order.created_at
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
    allowed_statuses = ["pending_payment", "awaiting_verification"]
    if order.status not in allowed_statuses:
        raise HTTPException(
            status_code=409, 
            detail=f"Cannot update address. Order status '{order.status}' does not allow modifications. Address can only be updated when status is 'pending_payment' or 'awaiting_verification'."
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