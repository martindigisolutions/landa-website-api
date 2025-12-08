import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt, JWTError

from database import get_db
from models import Application, Product, ProductVariantGroup, ProductVariant, Order, OrderItem, User, SingleAccessToken
from schemas.admin import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationCreatedResponse,
    ProductCreate, ProductUpdate, ProductAdminResponse,
    ProductVariantCreate, ProductVariantResponse,
    ProductVariantGroupCreate, ProductVariantGroupResponse,
    ProductBulkCreate, ProductBulkResponse, ProductBulkError,
    ProductBulkDelete, ProductBulkDeleteResponse, ProductBulkDeleteError,
    ProductBulkUpdate, ProductBulkUpdateItem, ProductBulkUpdateResponse, ProductBulkUpdateError,
    OrderAdminResponse, OrderItemResponse, OrderStatusUpdate, PaginatedOrdersResponse,
    AdminStats,
    UserAdminCreate, UserAdminResponse, UserAdminCreatedResponse, PaginatedUsersResponse,
    SingleAccessTokenCreate, SingleAccessTokenResponse,
    UserSuspendRequest, UserBlockRequest, UserActionResponse
)
from config import SECRET_KEY, ALGORITHM, WHOLESALE_FRONTEND_URL, SINGLE_ACCESS_TOKEN_EXPIRE_HOURS

# Security scheme for OAuth2 Bearer tokens
oauth2_bearer = HTTPBearer()

# Token expiration (2 hours)
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Available scopes
AVAILABLE_SCOPES = [
    "applications:read",
    "applications:write",
    "products:read",
    "products:write",
    "orders:read",
    "orders:write",
    "users:read",
    "users:write",
    "stats:read",
]

# Special scope that grants all permissions
WILDCARD_SCOPE = "*"


def expand_scopes(scopes: list) -> list:
    """Expand wildcard scope to all available scopes"""
    if WILDCARD_SCOPE in scopes:
        return AVAILABLE_SCOPES.copy()
    return scopes


def generate_client_id() -> str:
    """Generate a unique client_id like 'app_xxxxxx'"""
    return f"app_{secrets.token_hex(12)}"


def generate_client_secret() -> str:
    """Generate a secure client_secret like 'sk_live_xxxxxx'"""
    return f"sk_live_{secrets.token_hex(32)}"


def hash_secret(secret: str) -> str:
    """Hash the client_secret for storage"""
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Verify a client_secret against its hash"""
    return hash_secret(plain_secret) == hashed_secret


def create_app_access_token(app: Application) -> tuple[str, int]:
    """Create a JWT access token for an application"""
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": app.client_id,
        "type": "app",
        "scopes": app.scopes or [],
        "exp": expire
    }
    
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60  # return seconds


def get_current_app(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_bearer),
    db: Session = Depends(get_db)
) -> Application:
    """Dependency to get the current authenticated application from token"""
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if client_id is None or token_type != "app":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    app = db.query(Application).filter(
        Application.client_id == client_id,
        Application.is_active == True
    ).first()
    
    if app is None:
        raise credentials_exception
    
    # Update last_used_at
    app.last_used_at = datetime.utcnow()
    db.commit()
    
    return app


def require_scope(required_scope: str):
    """Dependency factory to require a specific scope"""
    def scope_checker(
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_bearer),
        db: Session = Depends(get_db)
    ) -> Application:
        token = credentials.credentials
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            scopes: list = payload.get("scopes", [])
            client_id: str = payload.get("sub")
            
            # Check if has wildcard or specific scope
            has_permission = WILDCARD_SCOPE in scopes or required_scope in scopes
            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient scope. Required: {required_scope}"
                )
                
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        app = db.query(Application).filter(
            Application.client_id == client_id,
            Application.is_active == True
        ).first()
        
        if app is None:
            raise HTTPException(status_code=401, detail="Application not found or inactive")
        
        # Update last_used_at
        app.last_used_at = datetime.utcnow()
        db.commit()
        
        return app
    
    return scope_checker


# ---------- Application Management ----------

def create_application(data: ApplicationCreate, db: Session) -> ApplicationCreatedResponse:
    """Create a new OAuth2 application"""
    # Expand wildcard scope if present
    scopes = expand_scopes(data.scopes)
    
    # Validate scopes
    for scope in scopes:
        if scope not in AVAILABLE_SCOPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {scope}. Available: {AVAILABLE_SCOPES} or use '*' for all"
            )
    
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    
    app = Application(
        client_id=client_id,
        client_secret_hash=hash_secret(client_secret),
        name=data.name,
        description=data.description,
        scopes=scopes,  # Use expanded scopes (handles "*" wildcard)
        is_active=True
    )
    
    db.add(app)
    db.commit()
    db.refresh(app)
    
    # Return with the plain client_secret (only shown once!)
    return ApplicationCreatedResponse(
        id=app.id,
        client_id=app.client_id,
        client_secret=client_secret,  # Only time this is shown!
        name=app.name,
        description=app.description,
        scopes=app.scopes or [],
        is_active=app.is_active,
        created_at=app.created_at,
        last_used_at=app.last_used_at
    )


def list_applications(db: Session) -> List[ApplicationResponse]:
    """List all applications"""
    apps = db.query(Application).all()
    return [ApplicationResponse.model_validate(app) for app in apps]


def get_application(app_id: int, db: Session) -> ApplicationResponse:
    """Get a single application by ID"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(app)


def update_application(app_id: int, data: ApplicationUpdate, db: Session) -> ApplicationResponse:
    """Update an application"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if data.scopes is not None:
        # Expand wildcard scope if present
        expanded_scopes = expand_scopes(data.scopes)
        for scope in expanded_scopes:
            if scope not in AVAILABLE_SCOPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid scope: {scope}. Available: {AVAILABLE_SCOPES} or use '*' for all"
                )
        data.scopes = expanded_scopes  # Replace with expanded scopes
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(app, field, value)
    
    db.commit()
    db.refresh(app)
    return ApplicationResponse.model_validate(app)


def delete_application(app_id: int, db: Session) -> dict:
    """Delete (deactivate) an application"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    app.is_active = False
    db.commit()
    return {"msg": f"Application '{app.name}' has been deactivated"}


def rotate_client_secret(app_id: int, db: Session) -> dict:
    """Generate a new client_secret for an application"""
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    new_secret = generate_client_secret()
    app.client_secret_hash = hash_secret(new_secret)
    db.commit()
    
    return {
        "msg": "Client secret rotated successfully",
        "client_secret": new_secret  # Only time this is shown!
    }


def authenticate_application(client_id: str, client_secret: str, db: Session) -> Application:
    """Authenticate an application by client_id and client_secret"""
    app = db.query(Application).filter(
        Application.client_id == client_id,
        Application.is_active == True
    ).first()
    
    if not app:
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    if not verify_secret(client_secret, app.client_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    
    return app


# ---------- Product Management ----------

def create_product(data: ProductCreate, db: Session) -> ProductAdminResponse:
    """Create a new product with optional variant groups"""
    # Extract variant groups before creating product
    variant_groups_data = data.variant_groups
    product_data = data.model_dump(exclude={'variant_groups'})
    
    # If variant groups provided, set has_variants to True
    if variant_groups_data:
        product_data['has_variants'] = True
    
    product = Product(**product_data)
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Create variant groups and variants if provided
    if variant_groups_data:
        for group_data in variant_groups_data:
            variants_data = group_data.variants
            group = ProductVariantGroup(
                product_id=product.id,
                name=group_data.name,
                display_order=group_data.display_order
            )
            db.add(group)
            db.commit()
            db.refresh(group)
            
            # Create variants for this group
            for variant_data in variants_data:
                variant = ProductVariant(
                    group_id=group.id,
                    **variant_data.model_dump()
                )
                db.add(variant)
        
        db.commit()
        db.refresh(product)
    
    return _product_to_response(product)


def bulk_create_products(data: ProductBulkCreate, db: Session) -> ProductBulkResponse:
    """Create multiple products at once"""
    created_products = []
    errors = []
    
    for index, product_data in enumerate(data.products):
        try:
            product = create_product(product_data, db)
            created_products.append(product)
        except HTTPException as e:
            errors.append(ProductBulkError(
                index=index,
                seller_sku=product_data.seller_sku,
                error=e.detail
            ))
        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg:
                error_msg = "SKU already exists"
            errors.append(ProductBulkError(
                index=index,
                seller_sku=product_data.seller_sku,
                error=error_msg
            ))
    
    return ProductBulkResponse(
        created=len(created_products),
        failed=len(errors),
        errors=errors,
        products=created_products
    )


def update_product(product_id: int, data: ProductUpdate, db: Session) -> ProductAdminResponse:
    """Update an existing product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Force updated_at to update
    product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(product)
    return _product_to_response(product)


def _product_to_response(product: Product) -> ProductAdminResponse:
    """Convert product model to response with variant groups"""
    variant_groups = []
    if product.has_variants and product.variant_groups:
        for group in sorted(product.variant_groups, key=lambda g: g.display_order):
            variants = [ProductVariantResponse.model_validate(v) for v in sorted(group.variants, key=lambda v: v.display_order)]
            variant_groups.append(ProductVariantGroupResponse(
                id=group.id,
                product_id=group.product_id,
                name=group.name,
                display_order=group.display_order,
                variants=variants
            ))
    
    return ProductAdminResponse(
        id=product.id,
        seller_sku=product.seller_sku,
        name=product.name,
        short_description=product.short_description,
        description=product.description,
        regular_price=product.regular_price,
        sale_price=product.sale_price,
        stock=product.stock,
        is_in_stock=product.is_in_stock,
        restock_date=product.restock_date,
        is_favorite=product.is_favorite,
        notify_when_available=product.notify_when_available,
        image_url=product.image_url,
        currency=product.currency,
        low_stock_threshold=product.low_stock_threshold,
        has_variants=product.has_variants,
        brand=product.brand,
        created_at=product.created_at,
        updated_at=product.updated_at,
        variant_groups=variant_groups
    )


def list_products(
    db: Session,
    search: Optional[str] = None,
    brand: Optional[str] = None,
    is_in_stock: Optional[bool] = None
) -> List[ProductAdminResponse]:
    """List all products with optional filters"""
    query = db.query(Product)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_filter)) |
            (Product.brand.ilike(search_filter))
        )
    
    if brand:
        query = query.filter(Product.brand == brand)
    
    if is_in_stock is not None:
        query = query.filter(Product.is_in_stock == is_in_stock)
    
    products = query.order_by(Product.name).all()
    return [_product_to_response(p) for p in products]


def get_product(product_id: int, db: Session) -> ProductAdminResponse:
    """Get a single product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_response(product)


def delete_product(product_id: int, db: Session) -> dict:
    """Delete a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"msg": f"Product '{product.name}' deleted successfully"}


def bulk_delete_products(data: ProductBulkDelete, db: Session) -> ProductBulkDeleteResponse:
    """Delete multiple products at once"""
    deleted_count = 0
    errors = []
    
    for product_id in data.product_ids:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            errors.append(ProductBulkDeleteError(
                id=product_id,
                error="Product not found"
            ))
            continue
        
        try:
            db.delete(product)
            db.commit()
            deleted_count += 1
        except Exception as e:
            db.rollback()
            errors.append(ProductBulkDeleteError(
                id=product_id,
                error=str(e)
            ))
    
    return ProductBulkDeleteResponse(
        deleted=deleted_count,
        failed=len(errors),
        errors=errors
    )


def bulk_update_products(data: ProductBulkUpdate, db: Session) -> ProductBulkUpdateResponse:
    """Update multiple products at once (for inventory, prices, etc.)"""
    updated_products = []
    errors = []
    
    for item in data.products:
        product = db.query(Product).filter(Product.id == item.id).first()
        if not product:
            errors.append(ProductBulkUpdateError(
                id=item.id,
                seller_sku=item.seller_sku,
                error="Product not found"
            ))
            continue
        
        try:
            # Update only provided fields
            update_data = item.model_dump(exclude={'id'}, exclude_unset=True)
            for field, value in update_data.items():
                if value is not None:
                    setattr(product, field, value)
            
            # Force updated_at to update
            product.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(product)
            updated_products.append(_product_to_response(product))
        except Exception as e:
            db.rollback()
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg:
                error_msg = "SKU already exists"
            errors.append(ProductBulkUpdateError(
                id=item.id,
                seller_sku=item.seller_sku,
                error=error_msg
            ))
    
    return ProductBulkUpdateResponse(
        updated=len(updated_products),
        failed=len(errors),
        errors=errors,
        products=updated_products
    )


# ---------- Order Management ----------

def list_orders(
    db: Session,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20
) -> PaginatedOrdersResponse:
    """List orders with filters and pagination"""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    results = []
    for order in orders:
        items = []
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown"
            items.append(OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=product_name,
                quantity=item.quantity,
                price=item.price
            ))
        
        results.append(OrderAdminResponse(
            id=order.id,
            session_id=order.session_id,
            user_id=order.user_id,
            shipping_method=order.shipping_method,
            payment_method=order.payment_method,
            address=order.address,
            status=order.status,
            payment_status=order.payment_status,
            total=order.total,
            created_at=order.created_at,
            paid_at=order.paid_at,
            stripe_payment_intent_id=order.stripe_payment_intent_id,
            items=items
        ))
    
    return PaginatedOrdersResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        results=results
    )


def get_order(order_id: int, db: Session) -> OrderAdminResponse:
    """Get a single order by ID"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items = []
    for item in order.items:
        product_name = item.product.name if item.product else "Unknown"
        items.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            product_name=product_name,
            quantity=item.quantity,
            price=item.price
        ))
    
    return OrderAdminResponse(
        id=order.id,
        session_id=order.session_id,
        user_id=order.user_id,
        shipping_method=order.shipping_method,
        payment_method=order.payment_method,
        address=order.address,
        status=order.status,
        payment_status=order.payment_status,
        total=order.total,
        created_at=order.created_at,
        paid_at=order.paid_at,
        stripe_payment_intent_id=order.stripe_payment_intent_id,
        items=items
    )


def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session) -> OrderAdminResponse:
    """Update order status"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    valid_statuses = ["pending", "processing", "shipped", "delivered", "canceled", "refunded"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid values: {valid_statuses}"
        )
    
    order.status = data.status
    db.commit()
    db.refresh(order)
    
    return get_order(order_id, db)


# ---------- Stats ----------

def get_admin_stats(db: Session) -> AdminStats:
    """Get admin dashboard statistics"""
    total_orders = db.query(Order).count()
    total_revenue = db.query(func.sum(Order.total)).filter(Order.payment_status == "completed").scalar() or 0
    total_products = db.query(Product).count()
    total_users = db.query(User).count()
    
    # Orders by status
    status_counts = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    orders_by_status = {status: count for status, count in status_counts}
    
    # Recent orders (last 10)
    recent = db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
    recent_orders = []
    for order in recent:
        items = []
        for item in order.items:
            product_name = item.product.name if item.product else "Unknown"
            items.append(OrderItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=product_name,
                quantity=item.quantity,
                price=item.price
            ))
        recent_orders.append(OrderAdminResponse(
            id=order.id,
            session_id=order.session_id,
            user_id=order.user_id,
            shipping_method=order.shipping_method,
            payment_method=order.payment_method,
            address=order.address,
            status=order.status,
            payment_status=order.payment_status,
            total=order.total,
            created_at=order.created_at,
            paid_at=order.paid_at,
            stripe_payment_intent_id=order.stripe_payment_intent_id,
            items=items
        ))
    
    return AdminStats(
        total_orders=total_orders,
        total_revenue=float(total_revenue),
        total_products=total_products,
        total_users=total_users,
        orders_by_status=orders_by_status,
        recent_orders=recent_orders
    )


# ---------- User Management ----------

def generate_single_access_token() -> str:
    """Generate a unique single-access token like 'sat_xxxxxx'"""
    return f"sat_{secrets.token_urlsafe(32)}"


def generate_temp_password() -> str:
    """Generate a temporary password for partial registrations"""
    return secrets.token_urlsafe(24)


def get_password_hash(password: str) -> str:
    """Hash a password using SHA256 (for temp passwords only)"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user_admin(data: UserAdminCreate, db: Session) -> UserAdminCreatedResponse:
    """Create a new user from admin panel (partial registration allowed)"""
    # Validate that at least one identifier is provided
    if not data.phone and not data.whatsapp_phone and not data.email:
        raise HTTPException(
            status_code=400,
            detail="At least one of phone, whatsapp_phone, or email must be provided"
        )
    
    # Check for existing user with same phone, whatsapp_phone, or email
    if data.phone:
        existing = db.query(User).filter(User.phone == data.phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone already registered")
    
    if data.whatsapp_phone:
        existing = db.query(User).filter(User.whatsapp_phone == data.whatsapp_phone).first()
        if existing:
            raise HTTPException(status_code=400, detail="WhatsApp phone already registered")
    
    if data.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Determine if this is a complete or partial registration
    is_complete = all([data.first_name, data.last_name, data.phone, data.email])
    
    # Generate temporary password (user will set their own later)
    temp_password = generate_temp_password()
    
    # Create user
    user = User(
        phone=data.phone,
        whatsapp_phone=data.whatsapp_phone,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        birthdate=data.birthdate,
        user_type=data.user_type,
        registration_complete=is_complete,
        hashed_password=get_password_hash(temp_password)  # Temp password
    )
    
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "UNIQUE constraint" in error_msg:
            raise HTTPException(status_code=400, detail="User with this identifier already exists")
        raise HTTPException(status_code=500, detail=f"Error creating user: {error_msg}")
    
    access_link = None
    
    # Generate single-access token if requested
    if data.generate_access_link:
        redirect_url = data.redirect_url or WHOLESALE_FRONTEND_URL
        token_obj = _create_single_access_token(user.id, redirect_url, db)
        access_link = f"{WHOLESALE_FRONTEND_URL}/auth?sat={token_obj.token}"
    
    return UserAdminCreatedResponse(
        id=user.id,
        phone=user.phone,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        birthdate=user.birthdate,
        user_type=user.user_type,
        registration_complete=user.registration_complete,
        created_at=user.created_at,
        access_link=access_link
    )


def _create_single_access_token(user_id: int, redirect_url: str, db: Session) -> SingleAccessToken:
    """Internal function to create a single-access token"""
    token = generate_single_access_token()
    expires_at = datetime.utcnow() + timedelta(hours=SINGLE_ACCESS_TOKEN_EXPIRE_HOURS)
    
    token_obj = SingleAccessToken(
        user_id=user_id,
        token=token,
        redirect_url=redirect_url,
        expires_at=expires_at,
        used=False
    )
    
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)
    
    return token_obj


def create_single_access_token_for_user(
    user_id: int, 
    data: SingleAccessTokenCreate, 
    db: Session
) -> SingleAccessTokenResponse:
    """Create a single-access token for an existing user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    redirect_url = data.redirect_url or WHOLESALE_FRONTEND_URL
    token_obj = _create_single_access_token(user_id, redirect_url, db)
    access_link = f"{WHOLESALE_FRONTEND_URL}/auth?sat={token_obj.token}"
    
    return SingleAccessTokenResponse(
        id=token_obj.id,
        user_id=token_obj.user_id,
        token=token_obj.token,
        access_link=access_link,
        redirect_url=token_obj.redirect_url,
        created_at=token_obj.created_at,
        expires_at=token_obj.expires_at,
        used=token_obj.used
    )


def list_users(
    db: Session,
    search: Optional[str] = None,
    user_type: Optional[str] = None,
    registration_complete: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20
) -> PaginatedUsersResponse:
    """List users with filters and pagination"""
    query = db.query(User)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.phone.ilike(search_filter)) |
            (User.whatsapp_phone.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (User.first_name.ilike(search_filter)) |
            (User.last_name.ilike(search_filter))
        )
    
    if user_type:
        query = query.filter(User.user_type == user_type)
    
    if registration_complete is not None:
        query = query.filter(User.registration_complete == registration_complete)
    
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    results = [UserAdminResponse.model_validate(user) for user in users]
    
    return PaginatedUsersResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        results=results
    )


def get_user_admin(user_id: int, db: Session) -> UserAdminResponse:
    """Get a single user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserAdminResponse.model_validate(user)


def validate_single_access_token(token: str, db: Session) -> dict:
    """
    Validate a single-access token from frontend.
    Returns user info and JWT if valid, marks token as used.
    
    If token was already used but not expired:
      - Returns valid=True, already_used=True, redirect_url (no new JWT)
      - Frontend can redirect user if they're already logged in
    """
    token_obj = db.query(SingleAccessToken).filter(
        SingleAccessToken.token == token
    ).first()
    
    if not token_obj:
        return {
            "valid": False,
            "already_used": False,
            "message": "Token not found"
        }
    
    # Check expiration first (applies to both used and unused tokens)
    if datetime.utcnow() > token_obj.expires_at:
        return {
            "valid": False,
            "already_used": False,
            "message": "Token has expired"
        }
    
    # Get user
    user = db.query(User).filter(User.id == token_obj.user_id).first()
    if not user:
        return {
            "valid": False,
            "already_used": False,
            "message": "User not found"
        }
    
    # Check if user is blocked or suspended
    if user.is_blocked:
        return {
            "valid": False,
            "already_used": False,
            "message": "Your account has been blocked. Please contact support."
        }
    
    if user.is_suspended:
        return {
            "valid": False,
            "already_used": False,
            "message": "Your account has been temporarily suspended. Please contact support."
        }
    
    # If token already used, return success but with already_used=True
    # No new JWT is generated, frontend should check if user is already logged in
    if token_obj.used:
        return {
            "valid": True,
            "already_used": True,
            "access_token": None,
            "token_type": "bearer",
            "redirect_url": token_obj.redirect_url,
            "user": UserAdminResponse.model_validate(user),
            "message": "Token was already used. Redirect if user is logged in."
        }
    
    # First time use - mark as used
    token_obj.used = True
    token_obj.used_at = datetime.utcnow()
    db.commit()
    
    # Get user
    user = db.query(User).filter(User.id == token_obj.user_id).first()
    if not user:
        return {
            "valid": False,
            "message": "User not found"
        }
    
    # Check if user is blocked
    if user.is_blocked:
        return {
            "valid": False,
            "message": "Your account has been blocked. Please contact support."
        }
    
    # Check if user is suspended
    if user.is_suspended:
        return {
            "valid": False,
            "message": "Your account has been temporarily suspended. Please contact support."
        }
    
    # Create JWT access token for the user
    # Use email, phone, or whatsapp_phone as identifier (in order of preference)
    identifier = user.email or user.phone or user.whatsapp_phone
    expires_delta = timedelta(days=365)
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": identifier,
        "exp": expire
    }
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "valid": True,
        "already_used": False,
        "access_token": access_token,
        "token_type": "bearer",
        "redirect_url": token_obj.redirect_url,
        "user": UserAdminResponse.model_validate(user),
        "message": "Token validated successfully"
    }


# ---------- User Suspension/Block Management ----------

def suspend_user(user_id: int, data: UserSuspendRequest, db: Session) -> UserActionResponse:
    """Suspend a user temporarily"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_blocked:
        raise HTTPException(status_code=400, detail="User is blocked. Unblock first before suspending.")
    
    if user.is_suspended:
        raise HTTPException(status_code=400, detail="User is already suspended")
    
    user.is_suspended = True
    user.suspended_at = datetime.utcnow()
    user.suspended_reason = data.reason
    
    db.commit()
    db.refresh(user)
    
    return UserActionResponse(
        success=True,
        message=f"User '{user.first_name or user.email or user.phone}' has been suspended",
        user=UserAdminResponse.model_validate(user)
    )


def unsuspend_user(user_id: int, db: Session) -> UserActionResponse:
    """Remove suspension from a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_suspended:
        raise HTTPException(status_code=400, detail="User is not suspended")
    
    user.is_suspended = False
    user.suspended_at = None
    user.suspended_reason = None
    
    db.commit()
    db.refresh(user)
    
    return UserActionResponse(
        success=True,
        message=f"User '{user.first_name or user.email or user.phone}' suspension has been lifted",
        user=UserAdminResponse.model_validate(user)
    )


def block_user(user_id: int, data: UserBlockRequest, db: Session) -> UserActionResponse:
    """Block a user permanently"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_blocked:
        raise HTTPException(status_code=400, detail="User is already blocked")
    
    # If user was suspended, clear suspension since block is more severe
    user.is_suspended = False
    user.suspended_at = None
    user.suspended_reason = None
    
    user.is_blocked = True
    user.blocked_at = datetime.utcnow()
    user.blocked_reason = data.reason
    
    db.commit()
    db.refresh(user)
    
    return UserActionResponse(
        success=True,
        message=f"User '{user.first_name or user.email or user.phone}' has been blocked",
        user=UserAdminResponse.model_validate(user)
    )


def unblock_user(user_id: int, db: Session) -> UserActionResponse:
    """Remove block from a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_blocked:
        raise HTTPException(status_code=400, detail="User is not blocked")
    
    user.is_blocked = False
    user.blocked_at = None
    user.blocked_reason = None
    
    db.commit()
    db.refresh(user)
    
    return UserActionResponse(
        success=True,
        message=f"User '{user.first_name or user.email or user.phone}' has been unblocked",
        user=UserAdminResponse.model_validate(user)
    )

