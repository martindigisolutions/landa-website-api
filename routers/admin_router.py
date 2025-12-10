from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services import admin_service
from schemas.admin import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationCreatedResponse,
    ProductCreate, ProductUpdate, ProductAdminResponse,
    ProductBulkCreate, ProductBulkResponse,
    ProductBulkDelete, ProductBulkDeleteResponse,
    ProductBulkUpdate, ProductBulkUpdateResponse,
    ProductVariantCreate, ProductVariantUpdate, ProductVariantResponse,
    ProductVariantGroupCreate, ProductVariantGroupResponse,
    VariantBulkDelete, VariantBulkDeleteResponse,
    OrderAdminResponse, OrderStatusUpdate, PaginatedOrdersResponse,
    AdminStats,
    UserAdminCreate, UserAdminResponse, UserAdminCreatedResponse, PaginatedUsersResponse,
    SingleAccessTokenCreate, SingleAccessTokenResponse,
    UserSuspendRequest, UserBlockRequest, UserActionResponse,
    CategoryGroupResponse
)
from schemas.product import ProductSchema

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== APPLICATION MANAGEMENT ====================
# These endpoints require applications:read or applications:write scope

@router.post(
    "/applications",
    response_model=ApplicationCreatedResponse,
    summary="Create a new application",
    description="Register a new OAuth2 application. The client_secret is only shown once!"
)
def create_application(
    data: ApplicationCreate,
    app=Depends(admin_service.require_scope("applications:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_application(data, db)


@router.get(
    "/applications",
    response_model=List[ApplicationResponse],
    summary="List all applications",
    description="Get a list of all registered applications."
)
def list_applications(
    app=Depends(admin_service.require_scope("applications:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_applications(db)


@router.get(
    "/applications/{app_id}",
    response_model=ApplicationResponse,
    summary="Get application details",
    description="Get details of a specific application by ID."
)
def get_application(
    app_id: int,
    app=Depends(admin_service.require_scope("applications:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_application(app_id, db)


@router.patch(
    "/applications/{app_id}",
    response_model=ApplicationResponse,
    summary="Update application",
    description="Update application name, description, scopes, or active status."
)
def update_application(
    app_id: int,
    data: ApplicationUpdate,
    app=Depends(admin_service.require_scope("applications:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_application(app_id, data, db)


@router.delete(
    "/applications/{app_id}",
    summary="Deactivate application",
    description="Deactivate an application (soft delete). Tokens will stop working."
)
def delete_application(
    app_id: int,
    app=Depends(admin_service.require_scope("applications:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_application(app_id, db)


@router.post(
    "/applications/{app_id}/rotate-secret",
    summary="Rotate client secret",
    description="Generate a new client_secret. The old secret will stop working immediately."
)
def rotate_secret(
    app_id: int,
    app=Depends(admin_service.require_scope("applications:write")),
    db: Session = Depends(get_db)
):
    return admin_service.rotate_client_secret(app_id, db)


# ==================== PRODUCT MANAGEMENT ====================
# These endpoints require products:read or products:write scope

@router.get(
    "/products",
    response_model=List[ProductAdminResponse],
    summary="List all products",
    description="Get a list of all products with optional filters."
)
def list_products(
    search: Optional[str] = Query(None, description="Search by name or brand"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    is_in_stock: Optional[bool] = Query(None, description="Filter by stock status"),
    app=Depends(admin_service.require_scope("products:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_products(db, search, brand, is_in_stock)


@router.get(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Get product by ID",
    description="Get details of a specific product."
)
def get_product(
    product_id: int,
    app=Depends(admin_service.require_scope("products:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_product(product_id, db)


@router.post(
    "/products",
    response_model=ProductAdminResponse,
    summary="Create product",
    description="Create a new product in the catalog."
)
def create_product(
    data: ProductCreate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_product(data, db)


@router.post(
    "/products/bulk",
    response_model=ProductBulkResponse,
    summary="Create multiple products",
    description="Create multiple products at once. Returns created products and any errors."
)
def bulk_create_products(
    data: ProductBulkCreate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_create_products(data, db)


@router.put(
    "/products/bulk",
    response_model=ProductBulkUpdateResponse,
    summary="Update multiple products",
    description="Update multiple products at once (inventory, prices, etc.). Only provided fields will be updated."
)
def bulk_update_products(
    data: ProductBulkUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_update_products(data, db)


@router.delete(
    "/products/bulk",
    response_model=ProductBulkDeleteResponse,
    summary="Delete multiple products",
    description="Delete multiple products at once by their IDs."
)
def bulk_delete_products(
    data: ProductBulkDelete,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_delete_products(data, db)


@router.put(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Update product",
    description="Update an existing product. Only provided fields will be updated."
)
def update_product(
    product_id: int,
    data: ProductUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_product(product_id, data, db)


@router.delete(
    "/products/{product_id}",
    summary="Delete product",
    description="Permanently delete a product from the catalog."
)
def delete_product(
    product_id: int,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_product(product_id, db)


# ==================== CATEGORY MANAGEMENT ====================
# These endpoints require products:read scope

@router.get(
    "/categories",
    response_model=List[CategoryGroupResponse],
    summary="List all categories",
    description="Get all category groups with their categories. Categories are grouped by their parent group."
)
def list_categories(
    app=Depends(admin_service.require_scope("products:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_categories(db)


# ==================== VARIANT MANAGEMENT ====================
# These endpoints manage individual variants without replacing all variants

@router.post(
    "/products/{product_id}/variant-groups",
    response_model=ProductVariantGroupResponse,
    summary="Add variant group to product",
    description="Add a new variant group with variants to an existing product."
)
def add_variant_group(
    product_id: int,
    data: ProductVariantGroupCreate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.add_variant_group(product_id, data, db)


@router.post(
    "/variant-groups/{group_id}/variants",
    response_model=ProductVariantResponse,
    summary="Add variant to group",
    description="Add a single variant to an existing variant group."
)
def add_variant_to_group(
    group_id: int,
    data: ProductVariantCreate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.add_variant_to_group(group_id, data, db)


@router.delete(
    "/variants/bulk",
    response_model=VariantBulkDeleteResponse,
    summary="Delete multiple variants",
    description="Delete multiple variants at once by their IDs."
)
def bulk_delete_variants(
    data: VariantBulkDelete,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_delete_variants(data, db)


@router.put(
    "/variants/{variant_id}",
    response_model=ProductVariantResponse,
    summary="Update variant",
    description="Update a single variant. Only provided fields will be updated."
)
def update_variant(
    variant_id: int,
    data: ProductVariantUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_variant(variant_id, data, db)


@router.delete(
    "/variants/{variant_id}",
    summary="Delete variant",
    description="Delete a single variant from a group."
)
def delete_variant(
    variant_id: int,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_variant(variant_id, db)


@router.delete(
    "/variant-groups/{group_id}",
    summary="Delete variant group",
    description="Delete a variant group and all its variants."
)
def delete_variant_group(
    group_id: int,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_variant_group(group_id, db)


# ==================== ORDER MANAGEMENT ====================
# These endpoints require orders:read or orders:write scope

@router.get(
    "/orders",
    response_model=PaginatedOrdersResponse,
    summary="List orders",
    description="Get a paginated list of orders with optional filters."
)
def list_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_orders(db, status, payment_status, user_id, page, page_size)


@router.get(
    "/orders/{order_id}",
    response_model=OrderAdminResponse,
    summary="Get order details",
    description="Get full details of a specific order including items."
)
def get_order(
    order_id: int,
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_order(order_id, db)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderAdminResponse,
    summary="Update order status",
    description="Update the status of an order (pending, processing, shipped, delivered, canceled, refunded)."
)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_order_status(order_id, data, db)


# ==================== STATISTICS ====================
# Requires stats:read scope

@router.get(
    "/stats",
    response_model=AdminStats,
    summary="Get admin statistics",
    description="Get dashboard statistics: totals, revenue, and recent orders."
)
def get_stats(
    app=Depends(admin_service.require_scope("stats:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_admin_stats(db)


# ==================== USER MANAGEMENT ====================
# These endpoints require users:read or users:write scope

@router.post(
    "/users",
    response_model=UserAdminCreatedResponse,
    summary="Create a new user",
    description="""Create a new user (partial registration allowed).
    At least one of phone, whatsapp_phone, or email must be provided.
    Set generate_access_link=true to receive a single-use access link for the user."""
)
def create_user(
    data: UserAdminCreate,
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_user_admin(data, db)


@router.get(
    "/users",
    response_model=PaginatedUsersResponse,
    summary="List users",
    description="Get a paginated list of users with optional filters."
)
def list_users(
    search: Optional[str] = Query(None, description="Search by phone, whatsapp_phone, email, or name"),
    user_type: Optional[str] = Query(None, description="Filter by user type (client, stylist)"),
    registration_complete: Optional[bool] = Query(None, description="Filter by registration status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_users(db, search, user_type, registration_complete, page, page_size)


@router.get(
    "/users/{user_id}",
    response_model=UserAdminResponse,
    summary="Get user details",
    description="Get full details of a specific user by ID."
)
def get_user(
    user_id: int,
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_user_admin(user_id, db)


@router.post(
    "/users/{user_id}/single-access-token",
    response_model=SingleAccessTokenResponse,
    summary="Generate single-access token",
    description="""Generate a new single-use access token for an existing user.
    The token expires in 24 hours and can only be used once.
    Optionally specify a redirect_url for where to send the user after authentication."""
)
def create_single_access_token(
    user_id: int,
    data: SingleAccessTokenCreate,
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_single_access_token_for_user(user_id, data, db)


@router.post(
    "/users/{user_id}/suspend",
    response_model=UserActionResponse,
    summary="Suspend user",
    description="Temporarily suspend a user. Suspended users cannot log in or make purchases."
)
def suspend_user(
    user_id: int,
    data: UserSuspendRequest = UserSuspendRequest(),
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.suspend_user(user_id, data, db)


@router.post(
    "/users/{user_id}/unsuspend",
    response_model=UserActionResponse,
    summary="Unsuspend user",
    description="Remove suspension from a user, allowing them to log in and make purchases again."
)
def unsuspend_user(
    user_id: int,
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.unsuspend_user(user_id, db)


@router.post(
    "/users/{user_id}/block",
    response_model=UserActionResponse,
    summary="Block user",
    description="Permanently block a user. Blocked users cannot log in or make purchases. More severe than suspension."
)
def block_user(
    user_id: int,
    data: UserBlockRequest = UserBlockRequest(),
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.block_user(user_id, data, db)


@router.post(
    "/users/{user_id}/unblock",
    response_model=UserActionResponse,
    summary="Unblock user",
    description="Remove block from a user, allowing them to log in and make purchases again."
)
def unblock_user(
    user_id: int,
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    return admin_service.unblock_user(user_id, db)

