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
from models import Application, Product, Order, OrderItem, User
from schemas.admin import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationCreatedResponse,
    ProductCreate, ProductUpdate, ProductAdminResponse,
    OrderAdminResponse, OrderItemResponse, OrderStatusUpdate, PaginatedOrdersResponse,
    AdminStats
)
from config import SECRET_KEY, ALGORITHM

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
    "stats:read",
]


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
            
            if required_scope not in scopes:
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
    # Validate scopes
    for scope in data.scopes:
        if scope not in AVAILABLE_SCOPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {scope}. Available: {AVAILABLE_SCOPES}"
            )
    
    client_id = generate_client_id()
    client_secret = generate_client_secret()
    
    app = Application(
        client_id=client_id,
        client_secret_hash=hash_secret(client_secret),
        name=data.name,
        description=data.description,
        scopes=data.scopes,
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
        for scope in data.scopes:
            if scope not in AVAILABLE_SCOPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid scope: {scope}. Available: {AVAILABLE_SCOPES}"
                )
    
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
    """Create a new product"""
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ProductAdminResponse.model_validate(product)


def update_product(product_id: int, data: ProductUpdate, db: Session) -> ProductAdminResponse:
    """Update an existing product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    return ProductAdminResponse.model_validate(product)


def delete_product(product_id: int, db: Session) -> dict:
    """Delete a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"msg": f"Product '{product.name}' deleted successfully"}


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

