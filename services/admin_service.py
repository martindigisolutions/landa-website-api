from __future__ import annotations

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
from models import (
    Application, Product, ProductVariantGroup, ProductVariant, 
    Order, OrderItem, User, SingleAccessToken,
    CategoryGroup, Category, ProductCategory, ShippingRule
)
from schemas.admin import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationCreatedResponse,
    ProductCreate, ProductUpdate, ProductAdminResponse,
    ProductVariantCreate, ProductVariantUpdate, ProductVariantResponse,
    ProductVariantGroupCreate, ProductVariantGroupResponse,
    VariantTypeResponse, VariantCategoryResponse,
    ProductBulkCreate, ProductBulkResponse, ProductBulkError,
    ProductBulkDelete, ProductBulkDeleteResponse, ProductBulkDeleteError,
    ProductBulkUpdate, ProductBulkUpdateItem, ProductBulkUpdateResponse, ProductBulkUpdateError,
    VariantBulkDelete, VariantBulkDeleteResponse, VariantBulkDeleteError,
    OrderAdminResponse, OrderItemResponse, OrderStatusUpdate, PaginatedOrdersResponse,
    AdminStats,
    UserAdminCreate, UserAdminResponse, UserAdminCreatedResponse, PaginatedUsersResponse,
    SingleAccessTokenCreate, SingleAccessTokenResponse,
    UserSuspendRequest, UserBlockRequest, UserActionResponse,
    CategoryInput, CategoryResponse, CategoryGroupResponse, CategoryItemResponse,
    ShippingRuleCreate, ShippingRuleUpdate, ShippingRuleResponse,
    ShippingRulesSyncRequest, ShippingRulesSyncResponse,
    InventoryUpdateSingle, InventoryBulkUpdate, InventoryUpdateResponse,
    InventoryBulkUpdateResponse, InventoryBulkUpdateError,
    VariantInventoryUpdateSingle, VariantInventoryBulkUpdate,
    VariantInventoryUpdateResponse, VariantInventoryBulkUpdateResponse, VariantInventoryBulkUpdateError,
    InventoryItem, InventoryListResponse,
    InventoryUnifiedUpdate, InventoryUnifiedUpdateResponse,
    InventoryUnifiedUpdateResult, InventoryUnifiedUpdateError
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
    "shipping:read",
    "shipping:write",
    "settings:read",
    "settings:write",
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


# ---------- Category Management ----------

def _process_categories(product_id: int, categories_data: List[CategoryInput], db: Session) -> None:
    """Process categories input and create/link categories to product.
    Creates category groups and categories if they don't exist (by slug).
    """
    for cat_input in categories_data:
        # Find or create CategoryGroup
        group = db.query(CategoryGroup).filter(CategoryGroup.slug == cat_input.group_slug).first()
        if not group:
            group = CategoryGroup(
                name=cat_input.group,
                name_en=cat_input.group_en,
                slug=cat_input.group_slug,
                icon=cat_input.group_icon,
                show_in_filters=cat_input.group_show_in_filters,
                display_order=cat_input.group_display_order
            )
            db.add(group)
            db.flush()
        else:
            # Update group info if provided (in case it changed)
            group.name = cat_input.group
            if cat_input.group_en:
                group.name_en = cat_input.group_en
            if cat_input.group_icon:
                group.icon = cat_input.group_icon
            group.show_in_filters = cat_input.group_show_in_filters
            group.display_order = cat_input.group_display_order
        
        # Find or create Category
        category = db.query(Category).filter(Category.slug == cat_input.slug).first()
        if not category:
            category = Category(
                group_id=group.id,
                name=cat_input.name,
                name_en=cat_input.name_en,
                slug=cat_input.slug,
                color=cat_input.color,
                icon=cat_input.icon,
                display_order=cat_input.display_order
            )
            db.add(category)
            db.flush()
        else:
            # Update category info if provided (in case it changed)
            category.name = cat_input.name
            if cat_input.name_en:
                category.name_en = cat_input.name_en
            if cat_input.color:
                category.color = cat_input.color
            if cat_input.icon:
                category.icon = cat_input.icon
            category.display_order = cat_input.display_order
            # Update group_id in case it moved to a different group
            category.group_id = group.id
        
        # Link product to category (if not already linked)
        existing_link = db.query(ProductCategory).filter(
            ProductCategory.product_id == product_id,
            ProductCategory.category_id == category.id
        ).first()
        
        if not existing_link:
            product_category = ProductCategory(
                product_id=product_id,
                category_id=category.id
            )
            db.add(product_category)


def list_categories(db: Session) -> List[CategoryGroupResponse]:
    """List all category groups with their categories"""
    groups = db.query(CategoryGroup).order_by(CategoryGroup.display_order, CategoryGroup.name).all()
    
    result = []
    for group in groups:
        categories = [
            CategoryItemResponse(
                id=cat.id,
                name=cat.name,
                name_en=cat.name_en,
                slug=cat.slug,
                color=cat.color,
                icon=cat.icon,
                display_order=cat.display_order
            )
            for cat in sorted(group.categories, key=lambda c: (c.display_order, c.name))
        ]
        
        result.append(CategoryGroupResponse(
            id=group.id,
            name=group.name,
            name_en=group.name_en,
            slug=group.slug,
            icon=group.icon,
            show_in_filters=group.show_in_filters,
            display_order=group.display_order,
            categories=categories
        ))
    
    return result


# ---------- Product Management ----------

def create_product(data: ProductCreate, db: Session) -> ProductAdminResponse:
    """Create a new product with optional variant groups and categories.
    Products are created with stock=0 and is_in_stock=False.
    Use inventory endpoints to update stock."""
    # Extract variant groups and categories before creating product
    variant_groups_data = data.variant_groups
    categories_data = data.categories
    product_data = data.model_dump(exclude={'variant_groups', 'categories'})
    
    # Force stock=0 and is_in_stock=False for new products
    # Stock is managed via inventory endpoints
    product_data['stock'] = 0
    product_data['is_in_stock'] = False
    
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
                variant_type=group_data.variant_type,  # REQUIRED
                name=group_data.name,  # OPTIONAL (category)
                display_order=group_data.display_order
            )
            db.add(group)
            db.commit()
            db.refresh(group)
            
            # Create variants for this group
            for variant_data in variants_data:
                variant_dict = variant_data.model_dump()
                # Default variant_value to name if not provided
                if not variant_dict.get('variant_value'):
                    variant_dict['variant_value'] = variant_dict['name']
                variant = ProductVariant(
                    group_id=group.id,
                    **variant_dict
                )
                db.add(variant)
        
        db.commit()
        db.refresh(product)
    
    # Process categories if provided
    if categories_data:
        _process_categories(product.id, categories_data, db)
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
    """Update an existing product. If variant_groups is provided, replaces all variants.
    If categories is provided, replaces all categories."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Extract variant_groups and categories before processing other fields
    variant_groups_data = data.variant_groups
    categories_data = data.categories
    update_data = data.model_dump(exclude_unset=True, exclude={'variant_groups', 'categories'})
    
    # Update simple fields
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Handle variant_groups if provided (replace all)
    if variant_groups_data is not None:
        # Delete existing variant groups (cascade deletes variants)
        for group in product.variant_groups:
            db.delete(group)
        db.flush()
        
        # Create new variant groups and variants
        if variant_groups_data:
            product.has_variants = True
            for group_data in variant_groups_data:
                variants_data = group_data.variants
                group = ProductVariantGroup(
                    product_id=product.id,
                    variant_type=group_data.variant_type,  # REQUIRED
                    name=group_data.name,  # OPTIONAL (category)
                    display_order=group_data.display_order
                )
                db.add(group)
                db.flush()
                
                # Create variants for this group
                for variant_data in variants_data:
                    variant_dict = variant_data.model_dump()
                    # Default variant_value to name if not provided
                    if not variant_dict.get('variant_value'):
                        variant_dict['variant_value'] = variant_dict['name']
                    variant = ProductVariant(
                        group_id=group.id,
                        **variant_dict
                    )
                    db.add(variant)
        else:
            # Empty array = remove all variants
            product.has_variants = False
    
    # Handle categories if provided (replace all)
    if categories_data is not None:
        # Delete existing product-category links
        db.query(ProductCategory).filter(ProductCategory.product_id == product.id).delete()
        db.flush()
        
        # Process new categories
        if categories_data:
            _process_categories(product.id, categories_data, db)
    
    # Force updated_at to update
    product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(product)
    return _product_to_response(product)


def _product_to_response(product: Product) -> ProductAdminResponse:
    """Convert product model to admin response with all language fields"""
    variant_types = []
    
    if product.has_variants and product.variant_groups:
        # Group by variant_type
        grouped_by_type = {}
        for group in sorted(product.variant_groups, key=lambda g: g.display_order):
            vtype = group.variant_type or "General"
            if vtype not in grouped_by_type:
                grouped_by_type[vtype] = []
            grouped_by_type[vtype].append(group)
        
        # Build variant_types response
        for vtype, groups in grouped_by_type.items():
            # Check if this type has categories or is simple
            # Simple = single group with name=null OR name equals variant_type
            is_simple = (
                len(groups) == 1 and 
                (not groups[0].name or groups[0].name == vtype)
            )
            
            if not is_simple:
                # Has categories - build categories list
                categories = []
                for group in groups:
                    variants = [ProductVariantResponse.model_validate(v) for v in sorted(group.variants, key=lambda v: v.display_order)]
                    categories.append(VariantCategoryResponse(
                        id=group.id,
                        name=group.name or vtype,  # Use variant_type as fallback name
                        display_order=group.display_order,
                        variants=variants
                    ))
                variant_types.append(VariantTypeResponse(
                    type=vtype,
                    categories=categories,
                    variants=None
                ))
            else:
                # Simple variants (single group with name=null)
                group = groups[0]
                variants = [ProductVariantResponse.model_validate(v) for v in sorted(group.variants, key=lambda v: v.display_order)]
                variant_types.append(VariantTypeResponse(
                    type=vtype,
                    categories=None,
                    variants=variants
                ))
    
    # Build categories response
    categories_response = []
    if product.product_categories:
        for pc in product.product_categories:
            cat = pc.category
            group = cat.group
            categories_response.append(CategoryResponse(
                id=cat.id,
                name=cat.name,
                name_en=cat.name_en,
                slug=cat.slug,
                color=cat.color,
                icon=cat.icon,
                display_order=cat.display_order,
                group_id=group.id,
                group_name=group.name,
                group_name_en=group.name_en,
                group_slug=group.slug,
                group_icon=group.icon,
                group_show_in_filters=group.show_in_filters
            ))
    
    return ProductAdminResponse(
        id=product.id,
        seller_sku=product.seller_sku,
        # Names
        name=product.name,
        name_en=product.name_en,
        # Descriptions
        short_description=product.short_description,
        short_description_en=product.short_description_en,
        description=product.description,
        description_en=product.description_en,
        # Tags
        tags=product.tags,
        tags_en=product.tags_en,
        # Pricing & Inventory
        regular_price=product.regular_price,
        sale_price=product.sale_price,
        stock=product.stock,
        is_in_stock=product.is_in_stock,
        restock_date=product.restock_date,
        is_favorite=product.is_favorite,
        notify_when_available=product.notify_when_available,
        image_url=product.image_url,
        gallery=product.gallery or [],
        currency=product.currency,
        low_stock_threshold=product.low_stock_threshold,
        has_variants=product.has_variants,
        brand=product.brand,
        weight_lbs=product.weight_lbs or 0.0,
        # Ordering fields for special sections
        bestseller_order=product.bestseller_order or 0,
        recommended_order=product.recommended_order or 0,
        # Timestamps
        created_at=product.created_at,
        updated_at=product.updated_at,
        variant_types=variant_types,
        categories=categories_response,
        # Related products
        similar_products=product.similar_products or [],
        frequently_bought_together=product.frequently_bought_together or []
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
    """
    Delete a product.
    - If product or its variants are in any order: soft delete (active=False)
    - If product has no orders: hard delete
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product.active:
        raise HTTPException(status_code=400, detail="Product already deleted")
    
    # Check if product is in any order (directly or via variants)
    has_direct_orders = db.query(OrderItem).filter(
        OrderItem.product_id == product_id
    ).first() is not None
    
    if has_direct_orders:
        # Soft delete: product is in orders, keep for history
        product.active = False
        # Also soft delete all variants
        for group in product.variant_groups:
            for variant in group.variants:
                variant.active = False
        db.commit()
        return {"msg": f"Product '{product.name}' deactivated (has order history)"}
    else:
        # Hard delete: no orders, safe to remove
        db.delete(product)
        db.commit()
        return {"msg": f"Product '{product.name}' deleted successfully"}


def bulk_delete_products(data: ProductBulkDelete, db: Session) -> ProductBulkDeleteResponse:
    """
    Delete multiple products at once.
    - If product is in any order: soft delete (active=False)
    - If product has no orders: hard delete
    """
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
        
        if not product.active:
            errors.append(ProductBulkDeleteError(
                id=product_id,
                error="Product already deleted"
            ))
            continue
        
        try:
            # Check if product is in any order
            has_orders = db.query(OrderItem).filter(
                OrderItem.product_id == product_id
            ).first() is not None
            
            if has_orders:
                # Soft delete
                product.active = False
                for group in product.variant_groups:
                    for variant in group.variants:
                        variant.active = False
            else:
                # Hard delete
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
    """Update multiple products at once (for inventory, prices, variants, categories, etc.)"""
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
            # Extract variant_groups and categories before processing other fields
            variant_groups_data = item.variant_groups
            categories_data = item.categories
            update_data = item.model_dump(exclude={'id', 'variant_groups', 'categories'}, exclude_unset=True)
            
            # Update simple fields
            for field, value in update_data.items():
                if value is not None:
                    setattr(product, field, value)
            
            # Handle variant_groups if provided (replace all)
            if variant_groups_data is not None:
                # Delete existing variant groups (cascade deletes variants)
                for group in product.variant_groups:
                    db.delete(group)
                db.flush()
                
                # Create new variant groups and variants
                if variant_groups_data:
                    product.has_variants = True
                    for group_data in variant_groups_data:
                        variants_data = group_data.variants
                        group = ProductVariantGroup(
                            product_id=product.id,
                            variant_type=group_data.variant_type,  # REQUIRED
                            name=group_data.name,  # OPTIONAL (category)
                            display_order=group_data.display_order
                        )
                        db.add(group)
                        db.flush()
                        
                        # Create variants for this group
                        for variant_data in variants_data:
                            variant_dict = variant_data.model_dump()
                            # Default variant_value to name if not provided
                            if not variant_dict.get('variant_value'):
                                variant_dict['variant_value'] = variant_dict['name']
                            variant = ProductVariant(
                                group_id=group.id,
                                **variant_dict
                            )
                            db.add(variant)
                else:
                    # Empty array = remove all variants
                    product.has_variants = False
            
            # Handle categories if provided (replace all)
            if categories_data is not None:
                # Delete existing product-category links
                db.query(ProductCategory).filter(ProductCategory.product_id == product.id).delete()
                db.flush()
                
                # Process new categories
                if categories_data:
                    _process_categories(product.id, categories_data, db)
            
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


# ---------- Variant Management ----------

def add_variant_group(product_id: int, data: ProductVariantGroupCreate, db: Session) -> ProductVariantGroupResponse:
    """Add a variant group with variants to an existing product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create the group
    group = ProductVariantGroup(
        product_id=product.id,
        variant_type=data.variant_type,  # REQUIRED
        name=data.name,  # OPTIONAL (category)
        display_order=data.display_order
    )
    db.add(group)
    db.flush()
    
    # Create variants
    for variant_data in data.variants:
        variant_dict = variant_data.model_dump()
        # Default variant_value to name if not provided
        if not variant_dict.get('variant_value'):
            variant_dict['variant_value'] = variant_dict['name']
        variant = ProductVariant(
            group_id=group.id,
            **variant_dict
        )
        db.add(variant)
    
    # Update product
    product.has_variants = True
    product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(group)
    
    variants = [ProductVariantResponse.model_validate(v) for v in group.variants]
    return ProductVariantGroupResponse(
        id=group.id,
        product_id=group.product_id,
        variant_type=group.variant_type,  # REQUIRED
        name=group.name,  # OPTIONAL (category)
        display_order=group.display_order,
        variants=variants
    )


def add_variant_to_group(group_id: int, data: ProductVariantCreate, db: Session) -> ProductVariantResponse:
    """Add a single variant to an existing group"""
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Variant group not found")
    
    variant_dict = data.model_dump()
    # Default variant_value to name if not provided
    if not variant_dict.get('variant_value'):
        variant_dict['variant_value'] = variant_dict['name']
    
    variant = ProductVariant(
        group_id=group.id,
        **variant_dict
    )
    db.add(variant)
    
    # Update product timestamp
    product = db.query(Product).filter(Product.id == group.product_id).first()
    if product:
        product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(variant)
    
    return ProductVariantResponse.model_validate(variant)


def update_variant(variant_id: int, data: ProductVariantUpdate, db: Session) -> ProductVariantResponse:
    """Update a single variant"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(variant, field, value)
    
    # Update product timestamp
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
    if group:
        product = db.query(Product).filter(Product.id == group.product_id).first()
        if product:
            product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(variant)
    
    return ProductVariantResponse.model_validate(variant)


def delete_variant(variant_id: int, db: Session) -> dict:
    """Delete a single variant"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    variant_name = variant.name
    group_id = variant.group_id
    
    db.delete(variant)
    
    # Update product timestamp
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == group_id).first()
    if group:
        product = db.query(Product).filter(Product.id == group.product_id).first()
        if product:
            product.updated_at = datetime.utcnow()
            # Check if product still has variants
            remaining_variants = db.query(ProductVariant).join(ProductVariantGroup).filter(
                ProductVariantGroup.product_id == product.id
            ).count()
            if remaining_variants == 0:
                product.has_variants = False
    
    db.commit()
    return {"msg": f"Variant '{variant_name}' deleted successfully"}


def delete_variant_group(group_id: int, db: Session) -> dict:
    """Delete a variant group and all its variants"""
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Variant group not found")
    
    group_name = group.name
    product_id = group.product_id
    
    db.delete(group)  # Cascade deletes variants
    
    # Update product
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.updated_at = datetime.utcnow()
        # Check if product still has variant groups
        remaining_groups = db.query(ProductVariantGroup).filter(
            ProductVariantGroup.product_id == product.id
        ).count()
        if remaining_groups == 0:
            product.has_variants = False
    
    db.commit()
    return {"msg": f"Variant group '{group_name}' deleted successfully"}


def bulk_delete_variants(data: VariantBulkDelete, db: Session) -> VariantBulkDeleteResponse:
    """
    Delete multiple variants at once.
    - If variant is in any order: soft delete (active=False) to preserve history
    - If variant has no orders: hard delete (remove completely)
    """
    deleted_count = 0
    errors = []
    affected_products = set()
    
    for variant_id in data.variant_ids:
        variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
        if not variant:
            errors.append(VariantBulkDeleteError(
                id=variant_id,
                error="Variant not found"
            ))
            continue
        
        if not variant.active:
            errors.append(VariantBulkDeleteError(
                id=variant_id,
                error="Variant already deleted"
            ))
            continue
        
        try:
            # Track affected product
            group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
            if group:
                affected_products.add(group.product_id)
            
            # Check if variant is referenced in any order
            has_orders = db.query(OrderItem).filter(OrderItem.variant_id == variant_id).first() is not None
            
            if has_orders:
                # Soft delete: variant is in orders, keep for history
                variant.active = False
            else:
                # Hard delete: no orders, safe to remove completely
                db.delete(variant)
            
            db.flush()
            deleted_count += 1
        except Exception as e:
            db.rollback()
            errors.append(VariantBulkDeleteError(
                id=variant_id,
                error=str(e)
            ))
    
    # Update affected products
    for product_id in affected_products:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.updated_at = datetime.utcnow()
            # Check if product still has ACTIVE variants
            remaining_active_variants = db.query(ProductVariant).join(ProductVariantGroup).filter(
                ProductVariantGroup.product_id == product.id,
                ProductVariant.active == True
            ).count()
            if remaining_active_variants == 0:
                product.has_variants = False
            # Recalculate stock based on active variants only
            _recalculate_product_stock(product, db)
    
    db.commit()
    
    return VariantBulkDeleteResponse(
        deleted=deleted_count,
        failed=len(errors),
        errors=errors
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
        product = item.product
        variant = item.variant
        
        product_name = product.name if product else "Unknown"
        variant_name = item.variant_name or (variant.name if variant else None)
        
        # Use variant image if available, otherwise product image
        image_url = None
        if variant and variant.image_url:
            image_url = variant.image_url
        elif product:
            image_url = product.image_url
        
        items.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=product_name,
            variant_name=variant_name,
            quantity=item.quantity,
            price=item.price,
            image_url=image_url
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
    """Hash a password using bcrypt directly"""
    import bcrypt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


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
    # Return redirect_url so frontend can redirect, but don't expose user data
    if datetime.utcnow() > token_obj.expires_at:
        return {
            "valid": True,
            "already_used": True,
            "access_token": None,
            "token_type": "bearer",
            "redirect_url": token_obj.redirect_url or WHOLESALE_FRONTEND_URL,
            "user": None,
            "message": "Token has expired. Please request a new access link."
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
    # No new JWT is generated, frontend should redirect if user is logged in
    # Don't return user data for security - anyone with the link could see it
    if token_obj.used:
        return {
            "valid": True,
            "already_used": True,
            "access_token": None,
            "token_type": "bearer",
            "redirect_url": token_obj.redirect_url or WHOLESALE_FRONTEND_URL,
            "user": None,
            "message": "Token validated successfully. User already authenticated."
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


# ---------- Shipping Rule Management ----------

VALID_RULE_TYPES = ["free_weight_per_product", "free_weight_per_category", "minimum_weight_charge", "base_rate"]


def _validate_shipping_rule(data: dict, rule_type: str) -> List[str]:
    """
    Validate shipping rule data based on rule type.
    Returns list of warning messages (non-blocking).
    Raises HTTPException for blocking errors.
    """
    warnings = []
    
    if rule_type not in VALID_RULE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rule_type '{rule_type}'. Valid values: {VALID_RULE_TYPES}"
        )
    
    if rule_type == "free_weight_per_product":
        if not data.get("selected_products"):
            raise HTTPException(status_code=400, detail="free_weight_per_product rule requires selected_products (array of seller_sku)")
        if not data.get("product_quantity"):
            raise HTTPException(status_code=400, detail="free_weight_per_product rule requires product_quantity")
        if not data.get("free_weight_lbs"):
            raise HTTPException(status_code=400, detail="free_weight_per_product rule requires free_weight_lbs")
    
    elif rule_type == "free_weight_per_category":
        if not data.get("selected_categories"):
            raise HTTPException(status_code=400, detail="free_weight_per_category rule requires selected_categories (array of category slugs)")
        if not data.get("product_quantity"):
            raise HTTPException(status_code=400, detail="free_weight_per_category rule requires product_quantity")
        if not data.get("free_weight_lbs"):
            raise HTTPException(status_code=400, detail="free_weight_per_category rule requires free_weight_lbs")
    
    elif rule_type == "minimum_weight_charge":
        if data.get("minimum_weight_lbs") is None:
            raise HTTPException(status_code=400, detail="minimum_weight_charge rule requires minimum_weight_lbs")
        if data.get("charge_amount") is None:
            raise HTTPException(status_code=400, detail="minimum_weight_charge rule requires charge_amount")
    
    elif rule_type == "base_rate":
        if data.get("rate_per_lb") is None:
            raise HTTPException(status_code=400, detail="base_rate rule requires rate_per_lb")
    
    return warnings


def _validate_skus_exist(selected_products: List[str], db: Session) -> List[str]:
    """Check if SKUs exist in database. Returns list of warnings for missing SKUs."""
    warnings = []
    if selected_products:
        existing_skus = set(
            sku for (sku,) in db.query(Product.seller_sku)
            .filter(Product.seller_sku.in_(selected_products))
            .all()
        )
        missing_skus = set(selected_products) - existing_skus
        if missing_skus:
            warnings.append(f"SKUs not found in database (rule will still apply): {', '.join(missing_skus)}")
    return warnings


def _validate_categories_exist(selected_categories: List[str], db: Session) -> List[str]:
    """Check if category slugs exist in database. Returns list of warnings for missing categories."""
    warnings = []
    if selected_categories:
        existing_slugs = set(
            slug for (slug,) in db.query(Category.slug)
            .filter(Category.slug.in_(selected_categories))
            .all()
        )
        missing_slugs = set(selected_categories) - existing_slugs
        if missing_slugs:
            warnings.append(f"Category slugs not found in database (rule will still apply): {', '.join(missing_slugs)}")
    return warnings


def sync_shipping_rules(data: ShippingRulesSyncRequest, db: Session) -> ShippingRulesSyncResponse:
    """
    Sync all shipping rules from dashboard.
    This REPLACES all existing rules with the new ones.
    """
    warnings = []
    
    # Validate all rules first
    for rule_input in data.rules:
        rule_data = rule_input.model_dump()
        _validate_shipping_rule(rule_data, rule_input.rule_type)
        
        # Validate SKUs and categories exist (non-blocking warnings)
        if rule_input.selected_products:
            warnings.extend(_validate_skus_exist(rule_input.selected_products, db))
        if rule_input.selected_categories:
            warnings.extend(_validate_categories_exist(rule_input.selected_categories, db))
    
    # Delete all existing rules
    db.query(ShippingRule).delete()
    db.flush()
    
    # Create new rules
    for rule_input in data.rules:
        rule_data = rule_input.model_dump(exclude={'id'})  # Exclude dashboard ID, we use our own
        rule = ShippingRule(**rule_data)
        db.add(rule)
    
    db.commit()
    
    return ShippingRulesSyncResponse(
        success=True,
        synced=len(data.rules),
        message=f"Successfully synced {len(data.rules)} shipping rules",
        warnings=warnings
    )


def create_shipping_rule(data: ShippingRuleCreate, db: Session) -> ShippingRuleResponse:
    """Create a new shipping rule"""
    rule_data = data.model_dump(exclude={'id'})
    _validate_shipping_rule(rule_data, data.rule_type)
    
    rule = ShippingRule(**rule_data)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return ShippingRuleResponse.model_validate(rule)


def list_shipping_rules(db: Session, rule_type: Optional[str] = None, is_active: Optional[bool] = None) -> List[ShippingRuleResponse]:
    """List all shipping rules with optional filters"""
    query = db.query(ShippingRule)
    
    if rule_type:
        query = query.filter(ShippingRule.rule_type == rule_type)
    
    if is_active is not None:
        query = query.filter(ShippingRule.is_active == is_active)
    
    rules = query.order_by(ShippingRule.priority, ShippingRule.id).all()
    return [ShippingRuleResponse.model_validate(r) for r in rules]


def get_shipping_rule(rule_id: int, db: Session) -> ShippingRuleResponse:
    """Get a single shipping rule by ID"""
    rule = db.query(ShippingRule).filter(ShippingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Shipping rule not found")
    return ShippingRuleResponse.model_validate(rule)


def update_shipping_rule(rule_id: int, data: ShippingRuleUpdate, db: Session) -> ShippingRuleResponse:
    """Update a shipping rule"""
    rule = db.query(ShippingRule).filter(ShippingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Shipping rule not found")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Build validation data with current values as defaults
    new_rule_type = update_data.get("rule_type", rule.rule_type)
    validation_data = {
        "selected_products": update_data.get("selected_products", rule.selected_products),
        "selected_categories": update_data.get("selected_categories", rule.selected_categories),
        "product_quantity": update_data.get("product_quantity", rule.product_quantity),
        "free_weight_lbs": update_data.get("free_weight_lbs", rule.free_weight_lbs),
        "minimum_weight_lbs": update_data.get("minimum_weight_lbs", rule.minimum_weight_lbs),
        "charge_amount": update_data.get("charge_amount", rule.charge_amount),
        "rate_per_lb": update_data.get("rate_per_lb", rule.rate_per_lb),
    }
    _validate_shipping_rule(validation_data, new_rule_type)
    
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    
    return ShippingRuleResponse.model_validate(rule)


def delete_shipping_rule(rule_id: int, db: Session) -> dict:
    """Delete a shipping rule"""
    rule = db.query(ShippingRule).filter(ShippingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Shipping rule not found")
    
    rule_name = rule.name
    db.delete(rule)
    db.commit()
    
    return {"msg": f"Shipping rule '{rule_name}' deleted successfully"}


# ---------- Inventory Management ----------

def _get_variant_inventory_list(product: Product) -> list:
    """Get list of variants with their current inventory"""
    variants = []
    for group in product.variant_groups:
        for variant in group.variants:
            if getattr(variant, 'active', True):
                variants.append({
                    "variant_id": variant.id,
                    "seller_sku": variant.seller_sku,
                    "name": variant.name,
                    "group_name": group.name or group.variant_type,
                    "stock": variant.stock or 0,
                    "is_in_stock": variant.is_in_stock
                })
    return variants


def update_inventory_by_sku(
    seller_sku: str, 
    data: InventoryUpdateSingle, 
    db: Session
) -> InventoryUpdateResponse:
    """Update inventory for a single product by SKU (only for products WITHOUT variants)"""
    product = db.query(Product).filter(Product.seller_sku == seller_sku).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with SKU '{seller_sku}' not found")
    
    # Reject if product has variants - return list of variants with their stock
    if product.has_variants:
        variants = _get_variant_inventory_list(product)
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Product has variants",
                "message": f"Product '{seller_sku}' has variants. Use /admin/inventory/variants/bulk to update variant stock. "
                          f"Product stock is automatically calculated as the sum of all variant stocks.",
                "product_id": product.id,
                "product_name": product.name,
                "product_stock": product.stock,
                "product_is_in_stock": product.is_in_stock,
                "variants": variants,
                "hint": "Update the variants listed above using /admin/inventory/variants/bulk"
            }
        )
    
    product.stock = data.stock
    
    # Auto-calculate is_in_stock if not provided
    if data.is_in_stock is not None:
        product.is_in_stock = data.is_in_stock
    else:
        product.is_in_stock = data.stock > 0
    
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    
    return InventoryUpdateResponse(
        seller_sku=product.seller_sku,
        product_id=product.id,
        stock=product.stock,
        is_in_stock=product.is_in_stock,
        message="Inventory updated successfully"
    )


def update_inventory_by_id(
    product_id: int, 
    data: InventoryUpdateSingle, 
    db: Session
) -> InventoryUpdateResponse:
    """Update inventory for a single product by ID (only for products WITHOUT variants)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    
    # Reject if product has variants - return list of variants with their stock
    if product.has_variants:
        variants = _get_variant_inventory_list(product)
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Product has variants",
                "message": f"Product ID {product_id} has variants. Use /admin/inventory/variants/bulk to update variant stock. "
                          f"Product stock is automatically calculated as the sum of all variant stocks.",
                "product_id": product.id,
                "product_sku": product.seller_sku,
                "product_name": product.name,
                "product_stock": product.stock,
                "product_is_in_stock": product.is_in_stock,
                "variants": variants,
                "hint": "Update the variants listed above using /admin/inventory/variants/bulk"
            }
        )
    
    product.stock = data.stock
    
    # Auto-calculate is_in_stock if not provided
    if data.is_in_stock is not None:
        product.is_in_stock = data.is_in_stock
    else:
        product.is_in_stock = data.stock > 0
    
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    
    return InventoryUpdateResponse(
        seller_sku=product.seller_sku or "",
        product_id=product.id,
        stock=product.stock,
        is_in_stock=product.is_in_stock,
        message="Inventory updated successfully"
    )


def bulk_update_inventory(
    data: InventoryBulkUpdate, 
    db: Session
) -> InventoryBulkUpdateResponse:
    """Update inventory for multiple products at once by SKU (only for products WITHOUT variants)"""
    results = []
    errors = []
    
    for item in data.products:
        product = db.query(Product).filter(Product.seller_sku == item.seller_sku).first()
        
        if not product:
            errors.append(InventoryBulkUpdateError(
                seller_sku=item.seller_sku,
                error="Product not found"
            ))
            continue
        
        # Skip products with variants - they must use variant endpoints
        if product.has_variants:
            variants = _get_variant_inventory_list(product)
            variant_skus = [v["seller_sku"] for v in variants if v["seller_sku"]]
            errors.append(InventoryBulkUpdateError(
                seller_sku=item.seller_sku,
                error=f"Product has variants. Use /admin/inventory/variants/bulk with SKUs: {', '.join(variant_skus)}"
            ))
            continue
        
        try:
            product.stock = item.stock
            
            # Auto-calculate is_in_stock if not provided
            if item.is_in_stock is not None:
                product.is_in_stock = item.is_in_stock
            else:
                product.is_in_stock = item.stock > 0
            
            product.updated_at = datetime.utcnow()
            db.flush()
            
            results.append(InventoryUpdateResponse(
                seller_sku=product.seller_sku,
                product_id=product.id,
                stock=product.stock,
                is_in_stock=product.is_in_stock,
                message="Updated"
            ))
        except Exception as e:
            errors.append(InventoryBulkUpdateError(
                seller_sku=item.seller_sku,
                error=str(e)
            ))
    
    db.commit()
    
    return InventoryBulkUpdateResponse(
        updated=len(results),
        failed=len(errors),
        errors=errors,
        results=results
    )


# ---------- Variant Inventory Management ----------

def _recalculate_product_stock(product: Product, db: Session) -> None:
    """
    Recalculate product stock based on sum of all variant stocks.
    Product is_in_stock = true if any variant is in stock.
    """
    if not product.has_variants:
        return
    
    total_stock = 0
    any_in_stock = False
    
    for group in product.variant_groups:
        for variant in group.variants:
            if getattr(variant, 'active', True):  # Only count active variants
                total_stock += variant.stock or 0
                if variant.is_in_stock:
                    any_in_stock = True
    
    product.stock = total_stock
    product.is_in_stock = any_in_stock
    product.updated_at = datetime.utcnow()


def update_variant_inventory_by_sku(
    seller_sku: str, 
    data: VariantInventoryUpdateSingle, 
    db: Session
) -> VariantInventoryUpdateResponse:
    """Update inventory for a single variant by SKU"""
    variant = db.query(ProductVariant).filter(ProductVariant.seller_sku == seller_sku).first()
    if not variant:
        raise HTTPException(status_code=404, detail=f"Variant with SKU '{seller_sku}' not found")
    
    variant.stock = data.stock
    
    # Auto-calculate is_in_stock if not provided
    if data.is_in_stock is not None:
        variant.is_in_stock = data.is_in_stock
    else:
        variant.is_in_stock = data.stock > 0
    
    # Get product info and recalculate parent product stock
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
    product = db.query(Product).filter(Product.id == group.product_id).first() if group else None
    
    # Recalculate parent product stock
    if product:
        _recalculate_product_stock(product, db)
    
    db.commit()
    db.refresh(variant)
    
    return VariantInventoryUpdateResponse(
        variant_id=variant.id,
        seller_sku=variant.seller_sku,
        variant_name=variant.name,
        product_id=product.id if product else 0,
        product_name=product.name if product else "Unknown",
        stock=variant.stock,
        is_in_stock=variant.is_in_stock,
        message="Variant inventory updated successfully"
    )


def update_variant_inventory_by_id(
    variant_id: int, 
    data: VariantInventoryUpdateSingle, 
    db: Session
) -> VariantInventoryUpdateResponse:
    """Update inventory for a single variant by ID"""
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail=f"Variant with ID {variant_id} not found")
    
    variant.stock = data.stock
    
    # Auto-calculate is_in_stock if not provided
    if data.is_in_stock is not None:
        variant.is_in_stock = data.is_in_stock
    else:
        variant.is_in_stock = data.stock > 0
    
    # Get product info and recalculate parent product stock
    group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
    product = db.query(Product).filter(Product.id == group.product_id).first() if group else None
    
    # Recalculate parent product stock
    if product:
        _recalculate_product_stock(product, db)
    
    db.commit()
    db.refresh(variant)
    
    return VariantInventoryUpdateResponse(
        variant_id=variant.id,
        seller_sku=variant.seller_sku or "",
        variant_name=variant.name,
        product_id=product.id if product else 0,
        product_name=product.name if product else "Unknown",
        stock=variant.stock,
        is_in_stock=variant.is_in_stock,
        message="Variant inventory updated successfully"
    )


def bulk_update_variant_inventory(
    data: VariantInventoryBulkUpdate, 
    db: Session
) -> VariantInventoryBulkUpdateResponse:
    """Update inventory for multiple variants at once by SKU"""
    results = []
    errors = []
    affected_products = set()  # Track products that need stock recalculation
    
    for item in data.variants:
        variant = db.query(ProductVariant).filter(ProductVariant.seller_sku == item.seller_sku).first()
        
        if not variant:
            errors.append(VariantInventoryBulkUpdateError(
                seller_sku=item.seller_sku,
                error="Variant not found"
            ))
            continue
        
        try:
            variant.stock = item.stock
            
            # Auto-calculate is_in_stock if not provided
            if item.is_in_stock is not None:
                variant.is_in_stock = item.is_in_stock
            else:
                variant.is_in_stock = item.stock > 0
            
            # Get product info
            group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
            product = db.query(Product).filter(Product.id == group.product_id).first() if group else None
            
            if product:
                affected_products.add(product.id)
            
            db.flush()
            
            results.append(VariantInventoryUpdateResponse(
                variant_id=variant.id,
                seller_sku=variant.seller_sku or "",
                variant_name=variant.name,
                product_id=product.id if product else 0,
                product_name=product.name if product else "Unknown",
                stock=variant.stock,
                is_in_stock=variant.is_in_stock,
                message="Updated"
            ))
        except Exception as e:
            errors.append(VariantInventoryBulkUpdateError(
                seller_sku=item.seller_sku,
                error=str(e)
            ))
    
    # Recalculate stock for all affected products
    for product_id in affected_products:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            _recalculate_product_stock(product, db)
    
    db.commit()
    
    return VariantInventoryBulkUpdateResponse(
        updated=len(results),
        failed=len(errors),
        errors=errors,
        results=results
    )


# ---------- Unified Inventory (Flat List) ----------

def get_inventory_list(db: Session, search: Optional[str] = None) -> InventoryListResponse:
    """
    Get flat list of all inventory items (products without variants + all variants).
    Products with variants are NOT included as items - only their variants are.
    """
    items = []
    total_products = 0
    total_variants = 0
    
    # Get all products
    query = db.query(Product)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_filter)) |
            (Product.seller_sku.ilike(search_filter)) |
            (Product.brand.ilike(search_filter))
        )
    
    products = query.order_by(Product.name).all()
    
    for product in products:
        if not product.has_variants:
            # Simple product - add directly
            items.append(InventoryItem(
                id=product.id,
                seller_sku=product.seller_sku,
                name=product.name,
                stock=product.stock or 0,
                is_in_stock=product.is_in_stock or False,
                is_variant=False,
                image_url=product.image_url
            ))
            total_products += 1
        else:
            # Product with variants - add each variant
            for group in product.variant_groups:
                for variant in group.variants:
                    if getattr(variant, 'active', True):
                        items.append(InventoryItem(
                            id=variant.id,
                            seller_sku=variant.seller_sku,
                            name=variant.name,
                            stock=variant.stock or 0,
                            is_in_stock=variant.is_in_stock or False,
                            is_variant=True,
                            image_url=variant.image_url or product.image_url,
                            parent_id=product.id,
                            parent_sku=product.seller_sku,
                            parent_name=product.name,
                            variant_type=group.variant_type,
                            group_name=group.name
                        ))
                        total_variants += 1
    
    return InventoryListResponse(
        total_items=len(items),
        total_products=total_products,
        total_variants=total_variants,
        items=items
    )


def update_inventory_unified(
    data: InventoryUnifiedUpdate, 
    db: Session
) -> InventoryUnifiedUpdateResponse:
    """
    Update inventory for products and variants in a unified way.
    Automatically detects if SKU belongs to a product or variant.
    """
    results = []
    errors = []
    affected_products = set()
    
    for item in data.items:
        # First try to find as a product
        product = db.query(Product).filter(Product.seller_sku == item.seller_sku).first()
        
        if product:
            # It's a product
            if product.has_variants:
                # Can't update product with variants directly
                errors.append(InventoryUnifiedUpdateError(
                    seller_sku=item.seller_sku,
                    error="This is a product with variants. Update the variant SKUs instead."
                ))
                continue
            
            # Update simple product
            product.stock = item.stock
            product.is_in_stock = item.is_in_stock if item.is_in_stock is not None else item.stock > 0
            product.updated_at = datetime.utcnow()
            db.flush()
            
            results.append(InventoryUnifiedUpdateResult(
                seller_sku=item.seller_sku,
                id=product.id,
                name=product.name,
                stock=product.stock,
                is_in_stock=product.is_in_stock,
                is_variant=False,
                message="Updated"
            ))
            continue
        
        # Try to find as a variant
        variant = db.query(ProductVariant).filter(ProductVariant.seller_sku == item.seller_sku).first()
        
        if variant:
            # It's a variant
            variant.stock = item.stock
            variant.is_in_stock = item.is_in_stock if item.is_in_stock is not None else item.stock > 0
            
            # Get parent product
            group = db.query(ProductVariantGroup).filter(ProductVariantGroup.id == variant.group_id).first()
            parent = db.query(Product).filter(Product.id == group.product_id).first() if group else None
            
            if parent:
                affected_products.add(parent.id)
            
            db.flush()
            
            results.append(InventoryUnifiedUpdateResult(
                seller_sku=item.seller_sku,
                id=variant.id,
                name=variant.name,
                stock=variant.stock,
                is_in_stock=variant.is_in_stock,
                is_variant=True,
                parent_sku=parent.seller_sku if parent else None,
                message="Updated"
            ))
            continue
        
        # Not found
        errors.append(InventoryUnifiedUpdateError(
            seller_sku=item.seller_sku,
            error="SKU not found (not a product or variant)"
        ))
    
    # Recalculate stock for affected parent products
    for product_id in affected_products:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            _recalculate_product_stock(product, db)
    
    db.commit()
    
    return InventoryUnifiedUpdateResponse(
        updated=len(results),
        failed=len(errors),
        errors=errors,
        results=results
    )

