"""
Cart router for shopping cart endpoints
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User
from services import cart_service, auth_service
from config import get_store_config
from schemas.cart import (
    CartResponse, CartItemCreate, CartItemUpdate,
    AddItemResponse, UpdateItemResponse, DeleteItemResponse,
    ClearCartResponse, MergeCartResponse, RecommendationsResponse,
    UpdateShippingRequest, UpdateShippingResponse,
    UpdatePaymentMethodRequest, UpdatePaymentMethodResponse,
    LockCartResponse, ReleaseLockRequest, ReleaseLockResponse,
    ExtendLockRequest, ExtendLockResponse
)
from services import cart_lock_service
from utils.language import get_language_from_header
from utils.messages import get_message

router = APIRouter(prefix="/cart", tags=["Cart"])


def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Optional[str]:
    """Extract session ID from header"""
    return x_session_id


# ---------- Cart Endpoints ----------

@router.get(
    "",
    response_model=CartResponse,
    summary="Get shopping cart",
    description="""
    Get the current shopping cart with all items.
    
    **Headers:**
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    - `Accept-Language`: `en` for English, `es` for Spanish (default)
    
    **Authentication:**
    - Wholesale mode: Requires authentication
    - Retail mode: Guest users can use X-Session-ID header
    
    Returns cart with items, totals, and any stock warnings.
    """
)
def get_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
):
    # In wholesale mode, user is guaranteed (get_cart_user raises 401 if not)
    # In retail mode, user might be None (guest), so we need session_id
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    
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
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    
    **Body:**
    - `quantity`: New quantity (must be >= 1)
    """
)
def update_item(
    item_id: int,
    data: CartItemUpdate,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    """
)
def remove_item(
    item_id: int,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    """
)
def clear_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    
    **Note:** This endpoint always requires authentication (both modes).
    """
)
def merge_carts(
    session_id: Optional[str] = Depends(get_session_id),
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    """
)
def validate_cart(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    
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
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    
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
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    """
)
def delete_shipping_address(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    
    **Body:**
    - `payment_method`: "stripe" or "zelle" (zelle only available in wholesale mode)
    """
)
def update_payment_method(
    data: UpdatePaymentMethodRequest,
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
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
    - `X-Session-ID`: Required for guest users (retail mode only)
    - `Authorization`: Bearer token (required in wholesale, optional in retail)
    """
)
def create_lock(
    session_id: Optional[str] = Depends(get_session_id),
    user: Optional[User] = Depends(auth_service.get_cart_user),
    db: Session = Depends(get_db)
):
    config = get_store_config()
    if not config["require_auth_for_cart"] and not session_id and not user:
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required for guest users"
        )
    
    try:
        cart = cart_service.get_or_create_cart(db, session_id, user)
        return cart_lock_service.create_lock(db, cart)
    except Exception as e:
        import logging
        logger = logging.getLogger("landa-api.cart")
        logger.error(f"Error creating cart lock: {e}", exc_info=True)
        # Always return valid JSON, even on error
        from schemas.cart import LockCartResponse
        return LockCartResponse(
            success=False,
            error="internal_error",
            message="An error occurred while creating the lock. Please try again."
        )


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
    user: Optional[User] = Depends(auth_service.get_optional_user),
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


@router.post(
    "/lock/extend",
    response_model=ExtendLockResponse,
    summary="Extend cart lock",
    description="""
    Extend a cart lock by 5 minutes. Use this BEFORE processing payment if the user
    took longer than expected to complete the payment form.
    
    **Behavior:**
    - If lock is active: Extends expiration time by 5 minutes
    - If lock expired but stock is available: Re-reserves stock and extends lock
    - If lock expired and stock unavailable: Returns error (409 Conflict)
    - If lock is used/cancelled: Returns error (400 Bad Request)
    
    **When to call:**
    - Right before calling Stripe to process payment
    - If user took >5 minutes to enter payment details
    
    **Localization:** Send `Accept-Language: en` header for English messages, 
    or `Accept-Language: es` for Spanish (default).
    
    **Request Body:**
    - `lock_token`: The token from POST /cart/lock
    
    **Success Response (200):**
    - `success`: true
    - `expires_at`: New expiration datetime
    - `expires_in_seconds`: Seconds until expiration
    
    **Error Responses:**
    - 409 Conflict: Stock no longer available (`insufficient_stock`)
    - 400 Bad Request: Lock invalid (`lock_not_found`, `lock_already_used`, `lock_cancelled`)
    """
)
def extend_lock(
    data: ExtendLockRequest,
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_db)
):
    lang = get_language_from_header(accept_language)
    result = cart_lock_service.extend_lock(db, data.lock_token, lang)
    
    # Convert to HTTP status codes
    if not result.success:
        if result.error == "insufficient_stock":
            # Convert Pydantic models to dicts for JSON serialization
            unavailable_items_dicts = [
                item.model_dump() if hasattr(item, 'model_dump') else (item.dict() if hasattr(item, 'dict') else item)
                for item in (result.unavailable_items or [])
            ]
            
            # Build items list for message
            item_names = []
            for item in (result.unavailable_items or []):
                if item.variant_name:
                    item_names.append(f"{item.product_name} - {item.variant_name}")
                else:
                    item_names.append(item.product_name)
            
            items_text = ", ".join(item_names[:3])  # Show max 3 items
            if len(item_names) > 3:
                items_text += f" y {len(item_names) - 3} más" if lang == "es" else f" and {len(item_names) - 3} more"
            
            user_message = get_message("insufficient_stock", lang, items=items_text)
            
            raise HTTPException(
                status_code=409,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": "insufficient_stock",
                    "message": result.message or user_message,
                    "user_message": user_message,
                    "unavailable_items": unavailable_items_dicts
                }
            )
        elif result.error == "lock_already_used":
            user_message = get_message("lock_already_used", lang)
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": "lock_already_used",
                    "message": result.message or user_message,
                    "user_message": user_message
                }
            )
        elif result.error == "lock_expired":
            user_message = get_message("lock_expired", lang)
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": "lock_expired",
                    "message": result.message or user_message,
                    "user_message": user_message
                }
            )
        elif result.error == "lock_not_found":
            user_message = get_message("lock_not_found", lang)
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": "lock_not_found",
                    "message": result.message or user_message,
                    "user_message": user_message
                }
            )
        elif result.error == "lock_cancelled":
            user_message = get_message("lock_cancelled", lang)
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": "lock_cancelled",
                    "message": result.message or user_message,
                    "user_message": user_message
                }
            )
        else:
            user_message = get_message("generic_error", lang)
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": result.error,
                    "error_code": result.error,
                    "message": result.message or user_message,
                    "user_message": user_message
                }
            )
    
    return result
