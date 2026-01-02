import logging
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_
from jose import jwt, JWTError
from database import get_db
from models import User
from config import SECRET_KEY, ALGORITHM
from services import checkout_service, auth_service
from services import shipping_service

logger = logging.getLogger("landa-api.checkout")
from schemas.checkout import (
    CheckoutSessionCreate, 
    CheckoutOptionsRequest, 
    OrderCreate, 
    ConfirmManualPayment, 
    PaymentDetailsResponse,
    OrderSummary,
    OrderDetailResponse,
    UpdateAddressRequest,
    UpdateAddressResponse,
    CalculateShippingRequest,
    CalculateShippingResponse,
    CheckoutValidationResponse
)
from typing import List, Optional

router = APIRouter(prefix="/checkout", tags=["Checkout"], redirect_slashes=False)

# Optional OAuth2 scheme (doesn't auto-raise 401)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Optional[str]:
    """Extract session ID from header"""
    return x_session_id


def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """Get user if authenticated, None otherwise"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get("sub")
        if not identifier:
            return None
        
        user = db.query(User).filter(
            or_(
                User.email == identifier,
                User.phone == identifier,
                User.whatsapp_phone == identifier
            )
        ).first()
        
        if not user or user.is_blocked or user.is_suspended:
            return None
        
        return user
    except JWTError:
        return None

@router.post("", response_model=CheckoutValidationResponse, summary="Iniciar sesión de checkout")
def start_checkout(
    data: CheckoutSessionCreate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Start a checkout session using the server-side cart.
    
    **Important:** Products are NOT sent by the frontend. The API reads 
    directly from the cart stored on the server.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (for authenticated users)
    
    **Response:**
    - `valid`: Whether the cart is ready for checkout
    - `checkout_id`: ID to use for subsequent checkout steps
    - `issues`: List of problems that need to be resolved (if any)
    
    **Possible issues:**
    - `product_removed`: Product no longer exists
    - `out_of_stock`: Product/variant is out of stock
    - `insufficient_stock`: Requested quantity exceeds available stock
    """
    logger.info(f"POST /checkout/ - session_id: {session_id}, user: {user.id if user else None}")
    
    if not session_id and not user:
        logger.warning("Checkout failed: Missing X-Session-ID header for guest user")
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return checkout_service.start_checkout_session(session_id, user, db)

@router.post("/options", summary="Obtener métodos de pago y envío disponibles")
def get_checkout_options(data: CheckoutOptionsRequest, db: Session = Depends(get_db)):
    return checkout_service.get_checkout_options(data, db)

@router.post("/order", summary="Crear orden final")
def create_order(
    data: OrderCreate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Create a final order using the server-side cart.
    
    **Important:** Products are NOT sent by the frontend. The API reads 
    directly from the cart stored on the server.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (for authenticated users)
    
    **Body:**
    - `address`: Shipping address
    - `shipping_method`: Selected shipping method
    - `payment_method`: Selected payment method
    
    **What happens:**
    1. Validates all cart items (stock, availability)
    2. Creates the order with current prices from DB
    3. Deducts stock from products/variants
    4. Clears the cart
    
    **Response:**
    - `order_id`: The created order ID
    - `status`: Order status (pending_payment)
    - `total`: Order total
    - `items_count`: Number of items in the order
    
    **Errors:**
    - 400: Cart is empty or invalid request
    - 409: Cart validation failed (stock issues, removed products)
    """
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return checkout_service.create_order(data, session_id, user, db)

@router.post("/order/confirm-manual-payment", summary="Confirmar pago manual")
def confirm_manual_payment(data: ConfirmManualPayment, db: Session = Depends(get_db)):
    return checkout_service.confirm_manual_payment(data, db)

@router.get("/order/{order_id}/payment-details", response_model=PaymentDetailsResponse)
def get_payment_details(order_id: str, db: Session = Depends(get_db)):
    return checkout_service.get_payment_details(order_id, db)

@router.get("/orders", response_model=List[OrderSummary])
def list_orders(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """Get orders for the authenticated user. User ID is extracted from the token for security."""
    return checkout_service.get_order_list(db, current_user.id)


@router.get("/orders/{order_id}", response_model=OrderDetailResponse, summary="Obtener detalle de una orden")
def get_order_detail(
    order_id: str, 
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener el detalle completo de una orden específica.
    
    - **order_id**: ID de la orden (path parameter)
    - User ID is extracted from the authentication token for security.
    
    Retorna 404 si la orden no existe.
    Retorna 403 si el usuario no tiene permiso para ver la orden.
    """
    return checkout_service.get_order_detail(order_id, str(current_user.id), db)


@router.put("/orders/{order_id}/address", response_model=UpdateAddressResponse, summary="Actualizar dirección de envío")
def update_order_address(
    order_id: str, 
    data: UpdateAddressRequest, 
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar la dirección de envío de una orden.
    
    Solo se permite actualizar si el status es "pending_payment" o "awaiting_verification".
    
    - **order_id**: ID de la orden (path parameter)
    - **address**: Nueva dirección de envío
    - User ID is extracted from the authentication token for security.
    
    Retorna 404 si la orden no existe.
    Retorna 403 si el usuario no tiene permiso.
    Retorna 409 si la orden ya no permite modificaciones.
    """
    return checkout_service.update_order_address(order_id, str(current_user.id), data.address.model_dump(), db)


@router.post("/calculate-shipping", response_model=CalculateShippingResponse, summary="Calcular costo de envío")
def calculate_shipping(data: CalculateShippingRequest, db: Session = Depends(get_db)):
    """
    Calcular el costo de envío basado en el contenido del carrito y las reglas configuradas.
    
    El cálculo considera:
    - Peso total de los productos
    - Reglas de libras gratis por productos específicos o categorías
    - Cargos mínimos por peso bajo
    - Tarifas base por libra
    
    Además, retorna **sugerencias** cuando el cliente está cerca (80%+) de:
    - Completar una regla de libras gratis (ej: "agrega 2 productos más para envío gratis")
    - Llenar capacidad de peso gratis (ej: "puedes agregar 0.5 lbs más por el mismo costo")
    
    **Request:**
    - `products`: Lista de productos con product_id, quantity y variant_id opcional
    - `address`: Dirección de envío (city, state, zip, country)
    
    **Response:**
    - `total_weight_lbs`: Peso total del carrito
    - `free_weight_lbs`: Libras cubiertas por envío gratis
    - `billable_weight_lbs`: Libras a cobrar
    - `shipping_cost`: Costo final de envío en USD
    - `applied_rules`: Lista de reglas aplicadas
    - `suggestions`: Sugerencias para ahorrar en envío
    - `summary`: Mensaje resumen (ej: "Envío: $5.99" o "¡Envío gratis!")
    """
    return shipping_service.calculate_shipping(data, db)
