"""
Cart service for shopping cart operations
"""
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from collections import Counter
from models import Cart, CartItem, Product, ProductVariant, User, CartLock
from schemas.cart import (
    CartResponse, CartItemResponse, CartItemCreate, CartItemUpdate,
    CartProductInfo, CartVariantInfo, CartSummary,
    AddItemResponse, UpdateItemResponse, DeleteItemResponse,
    ClearCartResponse, MergeCartResponse, StockWarning,
    RecommendedProduct, RecommendationsResponse, ShippingIncentive,
    UpdateShippingRequest, UpdateShippingResponse, ShippingAddress,
    ActiveLockInfo
)
from services.settings_service import SettingsService
from services.tax_service import TaxService
from services.shipping_service import calculate_shipping_cost, get_shipping_incentive
from schemas.settings import TaxAddress
from utils.language import localize_field

# Expiration times
GUEST_CART_EXPIRY_DAYS = 30
USER_CART_EXPIRY_DAYS = 90


def _get_expiry_date(is_authenticated: bool) -> datetime:
    """Get expiration date based on user type"""
    days = USER_CART_EXPIRY_DAYS if is_authenticated else GUEST_CART_EXPIRY_DAYS
    return datetime.utcnow() + timedelta(days=days)


def _get_unit_price(product: Product, variant: Optional[ProductVariant] = None) -> float:
    """Get the current unit price (variant price overrides product price)"""
    if variant:
        if variant.sale_price is not None:
            return variant.sale_price
        if variant.regular_price is not None:
            return variant.regular_price
    
    if product.sale_price is not None:
        return product.sale_price
    return product.regular_price or 0


def _get_stock(product: Product, variant: Optional[ProductVariant] = None) -> Tuple[int, bool]:
    """Get current stock and in_stock status"""
    if variant:
        return variant.stock or 0, variant.is_in_stock
    return product.stock or 0, product.is_in_stock


def _check_stock_status(quantity: int, available_stock: int, is_in_stock: bool) -> str:
    """Determine stock status for a cart item"""
    if not is_in_stock or available_stock <= 0:
        return "out_of_stock"
    if quantity > available_stock:
        return "low_stock"
    if available_stock <= 5:  # Low stock warning threshold
        return "low_stock"
    return "available"




def _build_product_info(product: Product, lang: str = "es") -> CartProductInfo:
    """Build product info for cart response"""
    # Localize name based on language
    name = localize_field(product.name, getattr(product, 'name_en', None), lang)
    
    return CartProductInfo(
        id=product.id,
        seller_sku=product.seller_sku,
        name=name or product.name,
        image_url=product.image_url,
        regular_price=product.regular_price,
        sale_price=product.sale_price,
        is_in_stock=product.is_in_stock,
        stock=product.stock or 0
    )


def _build_variant_info(variant: ProductVariant) -> CartVariantInfo:
    """Build variant info for cart response"""
    # Get variant type from the group
    variant_type = None
    if variant.group:
        variant_type = variant.group.variant_type
    
    return CartVariantInfo(
        id=variant.id,
        seller_sku=variant.seller_sku,
        name=variant.name,
        variant_type=variant_type,  # e.g., "Color", "Tamaño", "Volumen"
        variant_value=variant.variant_value,  # Clean value for display
        image_url=variant.image_url,
        regular_price=variant.regular_price,
        sale_price=variant.sale_price,
        is_in_stock=variant.is_in_stock,
        stock=variant.stock or 0
    )


def _is_item_orphaned(item: CartItem) -> bool:
    """Check if cart item references deleted product or variant"""
    # Product was deleted
    if item.product is None:
        return True
    # Variant was deleted (variant_id exists but variant is None)
    if item.variant_id is not None and item.variant is None:
        return True
    return False


def _build_item_response(item: CartItem, db: Session, lang: str = "es") -> Optional[CartItemResponse]:
    """Build full cart item response. Returns None if product/variant was deleted."""
    product = item.product
    variant = item.variant
    
    # Handle deleted product or variant
    if _is_item_orphaned(item):
        return None
    
    unit_price = _get_unit_price(product, variant)
    stock, is_in_stock = _get_stock(product, variant)
    stock_status = _check_stock_status(item.quantity, stock, is_in_stock)
    
    return CartItemResponse(
        id=item.id,
        product_id=item.product_id,
        variant_id=item.variant_id,
        quantity=item.quantity,
        product=_build_product_info(product, lang),
        variant=_build_variant_info(variant) if variant else None,
        unit_price=unit_price,
        line_total=round(unit_price * item.quantity, 2),
        stock_status=stock_status,
        added_at=item.added_at
    )


def _build_cart_summary(cart: Cart, db: Session) -> CartSummary:
    """Build cart summary (excludes deleted products/variants)"""
    items_count = 0
    total_items = 0
    subtotal = 0.0
    
    for item in cart.items:
        # Skip deleted products or variants
        if _is_item_orphaned(item):
            continue
        
        items_count += 1
        total_items += item.quantity
        unit_price = _get_unit_price(item.product, item.variant)
        subtotal += unit_price * item.quantity
    
    return CartSummary(
        items_count=items_count,
        total_items=total_items,
        subtotal=round(subtotal, 2)
    )


def _build_cart_response(cart: Cart, db: Session, lang: str = "es") -> CartResponse:
    """Build full cart response with warnings, totals, and validation"""
    items = []
    warnings = []
    items_to_remove = []
    removed_count = 0
    cart_items_for_shipping = []
    
    for item in cart.items:
        item_response = _build_item_response(item, db, lang)
        
        # Handle deleted products - mark for removal
        if item_response is None:
            items_to_remove.append(item)
            removed_count += 1
            continue
        
        items.append(item_response)
        cart_items_for_shipping.append({
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity
        })
        
        # Add warnings for stock issues
        if item_response.stock_status == "out_of_stock":
            warnings.append(StockWarning(
                type="out_of_stock",
                message=f"{item.product.name} is out of stock",
                available_stock=0
            ))
        elif item_response.stock_status == "low_stock":
            stock, _ = _get_stock(item.product, item.variant)
            if item.quantity > stock:
                warnings.append(StockWarning(
                    type="low_stock",
                    message=f"Only {stock} units of {item.product.name} available",
                    available_stock=stock,
                    requested_quantity=item.quantity
                ))
    
    # Remove orphaned cart items (products that were deleted)
    if items_to_remove:
        for orphan_item in items_to_remove:
            db.delete(orphan_item)
        db.commit()
        
        # Add warning about removed products
        warnings.insert(0, StockWarning(
            type="products_removed",
            message=f"{removed_count} product(s) were removed from your cart because they are no longer available",
            available_stock=0
        ))
    
    summary = _build_cart_summary(cart, db)
    
    # Calculate shipping (0 for pickup)
    shipping_fee = 0.0
    shipping_incentive_data = None
    is_pickup = cart.is_pickup or False
    
    if not is_pickup and cart_items_for_shipping:
        # Only calculate shipping for delivery, not pickup
        try:
            shipping_fee = calculate_shipping_cost(cart_items_for_shipping, db)
            shipping_incentive_data = get_shipping_incentive(cart_items_for_shipping, db)
        except Exception:
            # If shipping calculation fails, continue with 0
            pass
    
    # Get order limits from settings (managed via dashboard)
    # Owner configures min/max from dashboard - same logic for both modes
    settings_service = SettingsService(db)
    min_order_amount = settings_service.get_setting_as_float("min_order_amount", 0)  # Default 0 = no minimum
    max_order_amount = settings_service.get_setting_as_float("max_order_amount", 2000.0)
    
    # Calculate tax using saved shipping address if available
    tax_service = TaxService(db)
    
    # Build tax address from cart's saved shipping address
    tax_address = None
    if cart.shipping_city and cart.shipping_state and cart.shipping_zipcode:
        tax_address = TaxAddress(
            street_number="",  # Not needed for tax calculation
            street_name=cart.shipping_street or "",
            city=cart.shipping_city,
            state=cart.shipping_state,
            zipcode=cart.shipping_zipcode
        )
    
    tax_result = tax_service.calculate_tax(
        subtotal=summary.subtotal,
        shipping_fee=shipping_fee,
        address=tax_address,
        is_pickup=is_pickup
    )
    
    # Calculate total
    total = round(summary.subtotal + shipping_fee + tax_result.tax_amount, 2)
    
    # Validate order amounts
    can_checkout = True
    order_validation_error = None
    
    if summary.subtotal < min_order_amount:
        can_checkout = False
        difference = min_order_amount - summary.subtotal
        if lang == "en":
            order_validation_error = f"Minimum order is ${min_order_amount:.2f}. Add ${difference:.2f} more to continue."
        else:
            order_validation_error = f"El pedido minimo es de ${min_order_amount:.2f}. Agrega ${difference:.2f} mas para continuar."
    elif summary.subtotal > max_order_amount:
        can_checkout = False
        difference = summary.subtotal - max_order_amount
        if lang == "en":
            order_validation_error = f"Maximum order is ${max_order_amount:.2f}. Remove ${difference:.2f} to continue."
        else:
            order_validation_error = f"El pedido maximo es de ${max_order_amount:.2f}. Reduce ${difference:.2f} para continuar."
    
    # Build shipping incentive
    shipping_incentive = None
    if shipping_incentive_data:
        # Select message based on language
        message = localize_field(
            shipping_incentive_data.get("message", ""),
            shipping_incentive_data.get("message_en", ""),
            lang
        )
        shipping_incentive = ShippingIncentive(
            type=shipping_incentive_data.get("type", "free_shipping"),
            message=message or "",
            amount_needed=shipping_incentive_data.get("amount_needed"),
            items_needed=shipping_incentive_data.get("items_needed"),
            category=shipping_incentive_data.get("category"),
            potential_savings=shipping_incentive_data.get("potential_savings", 0.0)
        )
    
    # Build shipping address
    shipping_address = None
    if cart.is_pickup:
        # For pickup, return store address
        store_addr = tax_service.get_store_address()
        shipping_address = ShippingAddress(
            first_name=cart.shipping_first_name,
            last_name=cart.shipping_last_name,
            phone=cart.shipping_phone,
            email=cart.shipping_email,
            street=f"{store_addr.street_number} {store_addr.street_name} {store_addr.street_suffix or ''} {store_addr.street_direction or ''}".strip(),
            apartment=None,  # Store address doesn't have apartment
            city=store_addr.city,
            state=store_addr.state,
            zipcode=store_addr.zipcode,
            country="US"
        )
    elif cart.shipping_city and cart.shipping_state and cart.shipping_zipcode:
        # For delivery, return customer address
        shipping_address = ShippingAddress(
            first_name=cart.shipping_first_name,
            last_name=cart.shipping_last_name,
            phone=cart.shipping_phone,
            email=cart.shipping_email,
            street=cart.shipping_street,
            apartment=cart.shipping_apartment,
            city=cart.shipping_city,
            state=cart.shipping_state,
            zipcode=cart.shipping_zipcode,
            country=cart.shipping_country or "US"
        )
    
    # Check for active lock
    active_lock_info = None
    active_lock = db.query(CartLock).filter(
        CartLock.cart_id == cart.id,
        CartLock.status == "active",
        CartLock.expires_at > datetime.utcnow()
    ).first()
    
    if active_lock:
        expires_in_seconds = int((active_lock.expires_at - datetime.utcnow()).total_seconds())
        active_lock_info = ActiveLockInfo(
            lock_token=active_lock.token,
            expires_at=active_lock.expires_at,
            expires_in_seconds=max(0, expires_in_seconds)
        )
    
    return CartResponse(
        id=cart.id,
        items_count=summary.items_count,
        total_items=summary.total_items,
        subtotal=summary.subtotal,
        items=items,
        warnings=warnings,
        # Order Summary
        shipping_fee=shipping_fee,
        tax=tax_result.tax_amount,
        tax_rate=tax_result.tax_rate,
        tax_source=tax_result.tax_source,
        total=total,
        # Shipping Address
        shipping_address=shipping_address,
        is_pickup=cart.is_pickup or False,
        # Payment method
        payment_method=cart.payment_method,
        # Active lock info
        active_lock=active_lock_info,
        # Checkout Validation
        can_checkout=can_checkout,
        min_order_amount=min_order_amount,
        max_order_amount=max_order_amount,
        order_validation_error=order_validation_error,
        # Shipping Incentive
        shipping_incentive=shipping_incentive
    )


# ---------- Cart Operations ----------

def get_or_create_cart(
    db: Session,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> Cart:
    """
    Get existing cart or create a new one.
    Priority: user_id > session_id
    
    If an authenticated user accesses a guest cart (via session_id),
    the guest cart is automatically merged/assigned to the user.
    This ensures the user always sees the same cart across devices.
    """
    user_cart = None
    guest_cart = None
    
    # Try to find user's cart first
    if user:
        user_cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    
    # Try to find guest cart by session_id
    if session_id:
        guest_cart = db.query(Cart).filter(
            Cart.session_id == session_id,
            Cart.user_id == None
        ).first()
    
    # Handle the different cases
    if user:
        # Authenticated user
        if user_cart and guest_cart:
            # Both carts exist - merge guest into user cart
            _merge_guest_cart_into_user_cart(db, guest_cart, user_cart)
            cart = user_cart
        elif user_cart:
            # Only user cart exists
            cart = user_cart
        elif guest_cart:
            # Only guest cart exists - assign to user
            guest_cart.user_id = user.id
            guest_cart.session_id = None  # Clear session_id
            guest_cart.expires_at = _get_expiry_date(True)
            guest_cart.updated_at = datetime.utcnow()
            db.commit()
            cart = guest_cart
        else:
            # No cart exists - create new user cart
            cart = Cart(
                user_id=user.id,
                expires_at=_get_expiry_date(True)
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)
    else:
        # Guest user
        if guest_cart:
            cart = guest_cart
            cart.expires_at = _get_expiry_date(False)
            cart.updated_at = datetime.utcnow()
            db.commit()
        else:
            # Create new guest cart
            cart = Cart(
                session_id=session_id,
                expires_at=_get_expiry_date(False)
            )
            db.add(cart)
            db.commit()
            db.refresh(cart)
    
    return cart


def _merge_guest_cart_into_user_cart(db: Session, guest_cart: Cart, user_cart: Cart) -> None:
    """
    Merge items from guest cart into user cart.
    Guest quantities take priority on conflicts.
    Guest cart is deleted after merge.
    """
    from datetime import datetime
    
    for guest_item in guest_cart.items:
        # Check if item already exists in user cart
        existing_item = db.query(CartItem).filter(
            CartItem.cart_id == user_cart.id,
            CartItem.product_id == guest_item.product_id,
            CartItem.variant_id == guest_item.variant_id
        ).first()
        
        if existing_item:
            # Update quantity (use max of both)
            existing_item.quantity = max(existing_item.quantity, guest_item.quantity)
            existing_item.updated_at = datetime.utcnow()
        else:
            # Add new item to user cart
            new_item = CartItem(
                cart_id=user_cart.id,
                product_id=guest_item.product_id,
                variant_id=guest_item.variant_id,
                quantity=guest_item.quantity
            )
            db.add(new_item)
    
    # Delete any cart locks associated with the guest cart first
    # (to avoid NOT NULL constraint violation on cart_id)
    db.query(CartLock).filter(CartLock.cart_id == guest_cart.id).delete()
    
    # Delete guest cart (cascade deletes items)
    db.delete(guest_cart)
    
    # Update user cart
    user_cart.expires_at = _get_expiry_date(True)
    user_cart.updated_at = datetime.utcnow()
    
    db.commit()


def get_cart(
    db: Session,
    session_id: Optional[str] = None,
    user: Optional[User] = None,
    lang: str = "es"
) -> CartResponse:
    """Get cart with all items and warnings"""
    cart = get_or_create_cart(db, session_id, user)
    return _build_cart_response(cart, db, lang)


# ---------- Shipping Address Operations ----------

def update_shipping_address(
    db: Session,
    session_id: Optional[str],
    user: Optional[User],
    data: UpdateShippingRequest
) -> UpdateShippingResponse:
    """Update shipping address in cart"""
    cart = get_or_create_cart(db, session_id, user)
    
    # Get pickup status from either field
    is_pickup = data.get_is_pickup()
    
    # For pickup, address is optional (will use store address)
    if not is_pickup:
        # Validate required fields for delivery
        if not data.city:
            raise HTTPException(status_code=400, detail="City is required for delivery")
        if not data.state or len(data.state) != 2:
            raise HTTPException(status_code=400, detail="State must be a 2-letter code (e.g., NM, TX)")
        zipcode = data.get_zipcode()
        if not zipcode:
            raise HTTPException(status_code=400, detail="Zipcode is required for delivery")
    else:
        zipcode = data.get_zipcode()  # Optional for pickup
    
    # Update cart with shipping info
    # For pickup, only update contact info and is_pickup flag (preserve customer address)
    # For delivery, update full address
    if data.first_name:
        cart.shipping_first_name = data.first_name
    if data.last_name:
        cart.shipping_last_name = data.last_name
    if data.phone:
        cart.shipping_phone = data.phone
    if data.email:
        cart.shipping_email = data.email
    
    if not is_pickup:
        # Only update address for delivery
        cart.shipping_street = data.street
        cart.shipping_apartment = data.apartment
        cart.shipping_city = data.city or ""
        cart.shipping_state = (data.state or "").upper()
        cart.shipping_zipcode = zipcode or ""
        cart.shipping_country = data.country or "US"
    
    cart.is_pickup = is_pickup
    cart.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Build response address
    if is_pickup:
        # Return store address for pickup
        tax_service = TaxService(db)
        store_addr = tax_service.get_store_address()
        response_address = ShippingAddress(
            first_name=cart.shipping_first_name,
            last_name=cart.shipping_last_name,
            phone=cart.shipping_phone,
            email=cart.shipping_email,
            street=f"{store_addr.street_number} {store_addr.street_name} {store_addr.street_suffix or ''} {store_addr.street_direction or ''}".strip(),
            apartment=None,  # Store address doesn't have apartment
            city=store_addr.city,
            state=store_addr.state,
            zipcode=store_addr.zipcode,
            country="US"
        )
    else:
        response_address = ShippingAddress(
            first_name=cart.shipping_first_name,
            last_name=cart.shipping_last_name,
            phone=cart.shipping_phone,
            email=cart.shipping_email,
            street=cart.shipping_street,
            apartment=cart.shipping_apartment,
            city=cart.shipping_city,
            state=cart.shipping_state,
            zipcode=cart.shipping_zipcode,
            country=cart.shipping_country
        )
    
    return UpdateShippingResponse(
        success=True,
        message="Shipping address saved",
        shipping_address=response_address,
        is_pickup=is_pickup
    )


def delete_shipping_address(
    db: Session,
    session_id: Optional[str],
    user: Optional[User]
) -> UpdateShippingResponse:
    """Remove shipping address from cart"""
    cart = get_or_create_cart(db, session_id, user)
    
    # Clear shipping info
    cart.shipping_street = None
    cart.shipping_city = None
    cart.shipping_state = None
    cart.shipping_zipcode = None
    cart.is_pickup = False
    cart.updated_at = datetime.utcnow()
    
    db.commit()
    
    return UpdateShippingResponse(
        success=True,
        message="Shipping address removed",
        shipping_address=None,
        is_pickup=False
    )


def add_item(
    db: Session,
    data: CartItemCreate,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> AddItemResponse:
    """Add item to cart with soft stock validation"""
    # Validate product exists
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=400, detail="Product not found")
    
    # Validate variant if provided
    variant = None
    if data.variant_id:
        variant = db.query(ProductVariant).filter(
            ProductVariant.id == data.variant_id
        ).first()
        if not variant:
            raise HTTPException(status_code=400, detail="Variant not found")
        
        # Verify variant belongs to this product (through group)
        if variant.group.product_id != product.id:
            raise HTTPException(status_code=400, detail="Variant does not belong to this product")
    
    # Check if product requires variant
    if product.has_variants and not data.variant_id:
        raise HTTPException(
            status_code=400, 
            detail="This product has variants. Please select a variant."
        )
    
    # Get or create cart
    cart = get_or_create_cart(db, session_id, user)
    
    # Check if item already exists in cart
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == data.product_id,
        CartItem.variant_id == data.variant_id
    ).first()
    
    warning = None
    stock, is_in_stock = _get_stock(product, variant)
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item.quantity + data.quantity
        
        # Soft stock validation (warning, not blocking)
        if new_quantity > stock:
            warning = StockWarning(
                type="low_stock",
                message=f"Only {stock} units available. Added to cart anyway.",
                available_stock=stock,
                requested_quantity=new_quantity
            )
        
        existing_item.quantity = new_quantity
        existing_item.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_item)
        item = existing_item
        message = "Item quantity updated"
    else:
        # Create new item
        # Soft stock validation
        if data.quantity > stock and stock > 0:
            warning = StockWarning(
                type="low_stock",
                message=f"Only {stock} units available. Added to cart anyway.",
                available_stock=stock,
                requested_quantity=data.quantity
            )
        elif not is_in_stock or stock <= 0:
            warning = StockWarning(
                type="out_of_stock",
                message="Product is currently out of stock. Added to cart anyway.",
                available_stock=0,
                requested_quantity=data.quantity
            )
        
        item = CartItem(
            cart_id=cart.id,
            product_id=data.product_id,
            variant_id=data.variant_id,
            quantity=data.quantity
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        message = "Item added to cart"
    
    # Update cart timestamp
    cart.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cart)
    
    return AddItemResponse(
        success=True,
        message=message,
        item=_build_item_response(item, db),
        cart_summary=_build_cart_summary(cart, db),
        warning=warning
    )


def update_item(
    db: Session,
    item_id: int,
    data: CartItemUpdate,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> UpdateItemResponse:
    """Update cart item quantity"""
    cart = get_or_create_cart(db, session_id, user)
    
    # Find item in cart
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    # Soft stock validation
    warning = None
    stock, is_in_stock = _get_stock(item.product, item.variant)
    
    if data.quantity > stock:
        warning = StockWarning(
            type="low_stock",
            message=f"Only {stock} units available",
            available_stock=stock,
            requested_quantity=data.quantity
        )
    
    # Update quantity
    item.quantity = data.quantity
    item.updated_at = datetime.utcnow()
    cart.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(item)
    db.refresh(cart)
    
    return UpdateItemResponse(
        success=True,
        message="Item quantity updated",
        item=_build_item_response(item, db),
        cart_summary=_build_cart_summary(cart, db),
        warning=warning
    )


def remove_item(
    db: Session,
    item_id: int,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> DeleteItemResponse:
    """Remove item from cart"""
    cart = get_or_create_cart(db, session_id, user)
    
    # Find item in cart
    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.cart_id == cart.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    db.delete(item)
    cart.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cart)
    
    return DeleteItemResponse(
        success=True,
        message="Item removed from cart",
        cart_summary=_build_cart_summary(cart, db)
    )


def clear_cart(
    db: Session,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> ClearCartResponse:
    """Remove all items from cart"""
    cart = get_or_create_cart(db, session_id, user)
    
    # Delete all items
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    cart.updated_at = datetime.utcnow()
    db.commit()
    
    return ClearCartResponse(
        success=True,
        message="Cart cleared"
    )


def merge_carts(
    db: Session,
    session_id: str,
    user: User
) -> MergeCartResponse:
    """
    Merge guest cart into user cart on login.
    - If user has no cart, assign guest cart to user
    - If user has cart, merge items (guest quantities win on conflict)
    - Delete guest cart after merge
    """
    # Find guest cart
    guest_cart = db.query(Cart).filter(
        Cart.session_id == session_id,
        Cart.user_id == None
    ).first()
    
    # Find user cart
    user_cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    
    merged_items = 0
    
    if not guest_cart:
        # No guest cart to merge
        if not user_cart:
            # Create empty user cart
            user_cart = Cart(
                user_id=user.id,
                expires_at=_get_expiry_date(True)
            )
            db.add(user_cart)
            db.commit()
            db.refresh(user_cart)
        
        return MergeCartResponse(
            success=True,
            message="No guest cart to merge",
            merged_items=0,
            cart=_build_cart_response(user_cart, db)
        )
    
    if not user_cart:
        # Assign guest cart to user
        guest_cart.user_id = user.id
        guest_cart.session_id = None
        guest_cart.expires_at = _get_expiry_date(True)
        guest_cart.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(guest_cart)
        
        return MergeCartResponse(
            success=True,
            message="Guest cart assigned to user",
            merged_items=len(guest_cart.items),
            cart=_build_cart_response(guest_cart, db)
        )
    
    # Merge items from guest cart into user cart
    for guest_item in guest_cart.items:
        # Check if item exists in user cart
        existing_item = db.query(CartItem).filter(
            CartItem.cart_id == user_cart.id,
            CartItem.product_id == guest_item.product_id,
            CartItem.variant_id == guest_item.variant_id
        ).first()
        
        if existing_item:
            # Take the higher quantity (guest wins on tie)
            existing_item.quantity = max(existing_item.quantity, guest_item.quantity)
            existing_item.updated_at = datetime.utcnow()
        else:
            # Move item to user cart
            new_item = CartItem(
                cart_id=user_cart.id,
                product_id=guest_item.product_id,
                variant_id=guest_item.variant_id,
                quantity=guest_item.quantity
            )
            db.add(new_item)
        
        merged_items += 1
    
    # Delete guest cart (cascade deletes items)
    db.delete(guest_cart)
    
    # Update user cart
    user_cart.expires_at = _get_expiry_date(True)
    user_cart.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user_cart)
    
    return MergeCartResponse(
        success=True,
        message=f"Merged {merged_items} items from guest cart",
        merged_items=merged_items,
        cart=_build_cart_response(user_cart, db)
    )


def validate_cart_for_checkout(
    db: Session,
    session_id: Optional[str] = None,
    user: Optional[User] = None
) -> Tuple[bool, List[StockWarning], Cart]:
    """
    Hard validation for checkout.
    Returns (is_valid, errors, cart)
    If not valid, returns list of stock issues that must be resolved.
    """
    cart = get_or_create_cart(db, session_id, user)
    errors = []
    items_to_remove = []
    
    for item in cart.items:
        # Handle deleted products or variants
        if _is_item_orphaned(item):
            items_to_remove.append(item)
            continue
        
        stock, is_in_stock = _get_stock(item.product, item.variant)
        
        if not is_in_stock or stock <= 0:
            errors.append(StockWarning(
                type="out_of_stock",
                message=f"{item.product.name} is out of stock",
                available_stock=0,
                requested_quantity=item.quantity
            ))
        elif item.quantity > stock:
            errors.append(StockWarning(
                type="insufficient_stock",
                message=f"Only {stock} units of {item.product.name} available",
                available_stock=stock,
                requested_quantity=item.quantity
            ))
    
    # Clean up orphaned items (deleted products or variants)
    if items_to_remove:
        for orphan_item in items_to_remove:
            db.delete(orphan_item)
        db.commit()
        errors.insert(0, StockWarning(
            type="products_removed",
            message=f"{len(items_to_remove)} item(s) were removed because they are no longer available",
            available_stock=0
        ))
    
    return len(errors) == 0, errors, cart


def cleanup_expired_carts(db: Session) -> int:
    """Remove expired carts (run periodically)"""
    now = datetime.utcnow()
    expired = db.query(Cart).filter(Cart.expires_at < now).all()
    count = len(expired)
    
    for cart in expired:
        db.delete(cart)
    
    db.commit()
    return count


def get_cart_recommendations(
    db: Session,
    session_id: Optional[str] = None,
    user: Optional[User] = None,
    limit: int = 10
) -> RecommendationsResponse:
    """
    Get product recommendations based on cart items.
    
    Algorithm:
    1. Get all products currently in the cart
    2. For each product, get its 'frequently_bought_together' SKUs
    3. Count how many times each SKU appears across all cart items
    4. Exclude products already in the cart
    5. Return top products sorted by recommendation score (frequency count)
    """
    cart = get_or_create_cart(db, session_id, user)
    
    if not cart.items:
        return RecommendationsResponse(
            recommendations=[],
            based_on_items=0
        )
    
    # Get all product IDs and seller_skus in cart (skip deleted products/variants)
    cart_product_ids = set()
    cart_skus = set()
    valid_items = []
    
    for item in cart.items:
        if _is_item_orphaned(item):
            continue  # Skip deleted products/variants
        valid_items.append(item)
        cart_product_ids.add(item.product_id)
        if item.product.seller_sku:
            cart_skus.add(item.product.seller_sku)
    
    # Collect all frequently_bought_together SKUs from cart products
    sku_counter = Counter()
    
    for item in valid_items:
        product = item.product
        if product.frequently_bought_together:
            for sku in product.frequently_bought_together:
                # Exclude SKUs already in cart
                if sku and sku not in cart_skus:
                    sku_counter[sku] += 1
    
    if not sku_counter:
        return RecommendationsResponse(
            recommendations=[],
            based_on_items=len(valid_items)
        )
    
    # Get the most common SKUs (sorted by frequency, then limit)
    top_skus = [sku for sku, _ in sku_counter.most_common(limit * 2)]  # Get extra in case some don't exist
    
    # Fetch products by seller_sku (only active products)
    recommended_products = db.query(Product).filter(
        Product.seller_sku.in_(top_skus),
        Product.id.notin_(cart_product_ids),  # Double-check exclusion
        Product.active == True  # Exclude soft-deleted products
    ).all()
    
    # Create a map of sku -> product for sorting
    sku_to_product = {p.seller_sku: p for p in recommended_products}
    
    # Build response sorted by recommendation score
    recommendations = []
    for sku in top_skus:
        if sku in sku_to_product and len(recommendations) < limit:
            product = sku_to_product[sku]
            recommendations.append(RecommendedProduct(
                id=product.id,
                seller_sku=product.seller_sku,
                name=product.name,
                name_en=product.name_en,
                image_url=product.image_url,
                regular_price=product.regular_price,
                sale_price=product.sale_price,
                is_in_stock=product.is_in_stock,
                stock=product.stock or 0,
                brand=product.brand,
                has_variants=product.has_variants,
                recommendation_score=sku_counter[sku]
            ))
    
    return RecommendationsResponse(
        recommendations=recommendations,
        based_on_items=len(valid_items)
    )
