"""
Cart router for shopping cart endpoints
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from jose import jwt, JWTError

from database import get_db
from models import User
from services import cart_service
from config import SECRET_KEY, ALGORITHM
from schemas.cart import (
    CartResponse, CartItemCreate, CartItemUpdate,
    AddItemResponse, UpdateItemResponse, DeleteItemResponse,
    ClearCartResponse, MergeCartResponse, RecommendationsResponse,
    UpdateShippingRequest, UpdateShippingResponse,
    UpdatePaymentMethodRequest, UpdatePaymentMethodResponse,
    LockCartResponse, ReleaseLockRequest, ReleaseLockResponse
)
from services import cart_lock_service
from utils.language import get_language_from_header

router = APIRouter(prefix="/cart", tags=["Cart"])

# Optional OAuth2 scheme (doesn't auto-raise 401)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Optional[str]:
    """Extract session ID from header"""
    return x_session_id


def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional)
) -> Optional[User]:
    """Get user if authenticated, None otherwise (no error if not authenticated)"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier = payload.get("sub")
        if not identifier:
            return None
        
        # Find user by email, phone, or whatsapp_phone
        user = db.query(User).filter(
            or_(
                User.email == identifier,
                User.phone == identifier,
                User.whatsapp_phone == identifier
            )
        ).first()
        
        if not user:
            return None
        
        if user.is_blocked or user.is_suspended:
            return None
        
        return user
    except JWTError:
        return None
    except Exception:
        return None


# ---------- Cart Endpoints ----------

@router.get(
    "",
    response_model=CartResponse,
    summary="Get shopping cart",
    description="""
    Get the current shopping cart with all items.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users, optional for authenticated users
    - `Authorization`: Bearer token (optional)
    - `Accept-Language`: `en` for English, `es` for Spanish (default)
    
    Returns cart with items, totals, and any stock warnings.
    """
)
def get_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    lang = get_language_from_header(accept_language)
    return cart_service.get_cart(db, session_id, user, lang)


@router.post(
    "/items",
    response_model=AddItemResponse,
    summary="Add item to cart",
    description="""
    Add a product to the shopping cart.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Body:**
    - `product_id`: ID of the product to add
    - `variant_id`: ID of the variant (required if product has variants)
    - `quantity`: Number of units to add (default: 1)
    
    **Stock Validation (Soft):**
    - If stock is low, item is added with a warning
    - If out of stock, item is added with a warning
    - Hard validation happens at checkout
    """
)
def add_item(
    data: CartItemCreate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.add_item(db, data, session_id, user)


@router.put(
    "/items/{item_id}",
    response_model=UpdateItemResponse,
    summary="Update item quantity",
    description="""
    Update the quantity of an item in the cart.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Body:**
    - `quantity`: New quantity (must be >= 1)
    """
)
def update_item(
    item_id: int,
    data: CartItemUpdate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.update_item(db, item_id, data, session_id, user)


@router.delete(
    "/items/{item_id}",
    response_model=DeleteItemResponse,
    summary="Remove item from cart",
    description="""
    Remove an item from the shopping cart.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    """
)
def remove_item(
    item_id: int,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.remove_item(db, item_id, session_id, user)


@router.delete(
    "",
    response_model=ClearCartResponse,
    summary="Clear cart",
    description="""
    Remove all items from the shopping cart.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    """
)
def clear_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.clear_cart(db, session_id, user)


@router.post(
    "/merge",
    response_model=MergeCartResponse,
    summary="Merge guest cart with user cart",
    description="""
    Merge a guest cart into the authenticated user's cart.
    Call this after login if the user had items in their guest cart.
    
    **Headers:**
    - `X-Session-ID`: Required (the guest session to merge)
    - `Authorization`: Bearer token (required - must be authenticated)
    
    **Merge Logic:**
    - If user has no cart, guest cart is assigned to user
    - If user has cart, items are merged (higher quantity wins)
    - Guest cart is deleted after merge
    """
)
def merge_carts(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required to merge carts"
        )
    
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required to merge guest cart"
        )
    
    return cart_service.merge_carts(db, session_id, user)


@router.get(
    "/validate",
    summary="Validate cart for checkout",
    description="""
    Perform hard validation on cart for checkout.
    Returns validation result and any stock errors that must be resolved.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    """
)
def validate_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    is_valid, errors, cart = cart_service.validate_cart_for_checkout(db, session_id, user)
    
    return {
        "valid": is_valid,
        "errors": [e.model_dump() for e in errors],
        "cart_id": cart.id
    }


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Get product recommendations based on cart",
    description="""
    Get personalized product recommendations based on items in the cart.
    
    **Algorithm:**
    - Analyzes all products in the cart
    - Finds products frequently bought together with cart items
    - Ranks by how many cart items recommend each product
    - Excludes products already in the cart
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Query Parameters:**
    - `limit`: Maximum number of recommendations (default: 10, max: 20)
    
    **Response:**
    - `recommendations`: List of recommended products with scores
    - `based_on_items`: Number of cart items used for analysis
    """
)
def get_recommendations(
    limit: int = 10,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    # Cap limit at 20
    limit = min(limit, 20)
    
    return cart_service.get_cart_recommendations(db, session_id, user, limit)


# ==================== SHIPPING ADDRESS ====================

@router.put(
    "/shipping",
    response_model=UpdateShippingResponse,
    summary="Update shipping address",
    description="""
    Save or update the shipping address for the cart.
    Once saved, tax will be calculated automatically on GET /cart.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Fields:**
    - `street`: Street address (optional)
    - `city`: City (required)
    - `state`: State code, e.g., "NM", "TX" (required)
    - `zipcode`: ZIP code (required)
    - `is_pickup`: If true, uses store address for tax calculation
    """
)
def update_shipping_address(
    data: UpdateShippingRequest,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.update_shipping_address(db, session_id, user, data)


@router.delete(
    "/shipping",
    response_model=UpdateShippingResponse,
    summary="Remove shipping address",
    description="""
    Remove the saved shipping address from the cart.
    Tax will return to 0 on subsequent GET /cart calls.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    """
)
def delete_shipping_address(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    return cart_service.delete_shipping_address(db, session_id, user)


# ==================== PAYMENT METHOD ====================

@router.put(
    "/payment-method",
    response_model=UpdatePaymentMethodResponse,
    summary="Set payment method",
    description="""
    Save the selected payment method for the cart.
    Must be called before creating a lock.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Body:**
    - `payment_method`: "stripe" or "zelle"
    """
)
def update_payment_method(
    data: UpdatePaymentMethodRequest,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    cart = cart_service.get_or_create_cart(db, session_id, user)
    return cart_lock_service.update_payment_method(db, cart, data.payment_method)


# ==================== CART LOCK SYSTEM ====================

@router.post(
    "/lock",
    response_model=LockCartResponse,
    summary="Lock cart and reserve stock",
    description="""
    Create a temporary lock on the cart, reserving stock for checkout.
    Lock expires after 5 minutes.
    
    **Prerequisites:**
    - Cart must have items
    - Shipping address must be set (for delivery) or is_pickup must be true
    - Payment method must be selected
    
    **Behavior:**
    - Validates stock availability for all items
    - Creates stock reservation (prevents overselling)
    - If payment_method is "stripe", creates PaymentIntent
    - Cancels any previous active lock for this cart
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    """
)
def create_lock(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    cart = cart_service.get_or_create_cart(db, session_id, user)
    return cart_lock_service.create_lock(db, cart)


@router.delete(
    "/lock",
    response_model=ReleaseLockResponse,
    summary="Release cart lock",
    description="""
    Cancel an active lock and release reserved stock.
    Call this when user cancels checkout or payment fails.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users
    - `Authorization`: Bearer token (optional)
    
    **Body:**
    - `lock_token`: The token returned from POST /cart/lock
    """
)
def release_lock(
    data: ReleaseLockRequest,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    return cart_lock_service.release_lock(db, data.lock_token)


@router.post(
    "/lock/release",
    response_model=ReleaseLockResponse,
    summary="Release cart lock (sendBeacon compatible)",
    description="""
    Alternative endpoint to release a lock, compatible with navigator.sendBeacon().
    Accepts both JSON and plain text body.
    
    **Usage with sendBeacon:**
    ```javascript
    navigator.sendBeacon('/cart/lock/release', lock_token);
    ```
    
    **Note:** This endpoint always returns 200 OK (idempotent).
    """
)
async def release_lock_beacon(
    request: Request,
    db: Session = Depends(get_db)
):
    # Try to get lock_token from body
    content_type = request.headers.get("content-type", "")
    
    try:
        if "application/json" in content_type:
            body = await request.json()
            lock_token = body.get("lock_token", "")
        else:
            # Plain text (sendBeacon)
            body = await request.body()
            lock_token = body.decode("utf-8").strip()
    except Exception:
        lock_token = ""
    
    if not lock_token:
        return ReleaseLockResponse(
            success=True,
            message="No lock token provided"
        )
    
    return cart_lock_service.release_lock(db, lock_token)
