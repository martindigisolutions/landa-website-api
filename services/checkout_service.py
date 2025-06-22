from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Product, Order, OrderItem
from schemas.checkout import CheckoutSessionCreate, CheckoutOptionsRequest, OrderCreate, ConfirmManualPayment
from uuid import uuid4

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
        {"id": "zelle", "label": "Zelle (0% Fee)"},
        {"id": "credit_card", "label": "Tarjeta de crédito (2% Fee)"}
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
    valid_methods = ["zelle", "cashapp", "venmo", "credit_card", "cash"]
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
        "order_id": f"ORD{order.id}",
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