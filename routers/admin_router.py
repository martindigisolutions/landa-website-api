from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services import admin_service
from schemas.admin import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, ApplicationCreatedResponse,
    ProductCreate, ProductUpdate, ProductAdminResponse,
    OrderAdminResponse, OrderStatusUpdate, PaginatedOrdersResponse,
    AdminStats
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

