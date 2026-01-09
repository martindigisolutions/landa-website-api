from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services import admin_service
from services.settings_service import SettingsService, get_settings_service
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
    OrderShipmentResponse, OrderShipmentCreate, OrderShipmentUpdate, OrderShipmentBulkCreate,
    OrderCombineRequest, OrderCombineResponse, OrderUncombineRequest, OrderUncombineResponse,
    CombinedOrdersResponse,
    AdminStats,
    UserAdminCreate, UserAdminResponse, UserAdminCreatedResponse, PaginatedUsersResponse,
    SingleAccessTokenCreate, SingleAccessTokenResponse,
    UserSuspendRequest, UserBlockRequest, UserActionResponse,
    CategoryGroupResponse,
    ShippingRuleCreate, ShippingRuleUpdate, ShippingRuleResponse,
    ShippingRulesSyncRequest, ShippingRulesSyncResponse,
    InventoryUpdateSingle, InventoryBulkUpdate, 
    InventoryUpdateResponse, InventoryBulkUpdateResponse,
    VariantInventoryUpdateSingle, VariantInventoryBulkUpdate,
    VariantInventoryUpdateResponse, VariantInventoryBulkUpdateResponse,
    InventoryListResponse, InventoryUnifiedUpdate, InventoryUnifiedUpdateResponse
)
from schemas.product import ProductSchema
from schemas.settings import (
    SettingResponse, SettingUpdate, SettingsListResponse,
    BulkSettingsUpdate, BulkSettingsResponse
)

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


# IMPORTANT: Specific routes must come BEFORE the generic /orders/{order_id} route
# ==================== ORDER COMBINATION ====================
# These endpoints require orders:write scope

@router.post(
    "/orders/combine",
    response_model=OrderCombineResponse,
    summary="Combine orders",
    description="Combine multiple orders into a single shipping group. All orders must be paid and have the same shipping address."
)
def combine_orders(
    data: OrderCombineRequest,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.combine_orders(data, db)


@router.post(
    "/orders/uncombine",
    response_model=OrderUncombineResponse,
    summary="Uncombine orders",
    description="Separate orders from a combined group. Cannot uncombine if shipments are already delivered."
)
def uncombine_orders(
    data: OrderUncombineRequest,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.uncombine_orders(data, db)


@router.get(
    "/orders/combined/{combined_group_id}",
    response_model=CombinedOrdersResponse,
    summary="Get combined orders group",
    description="Get all orders in a combined group and their shared shipments."
)
def get_combined_orders(
    combined_group_id: str,
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_combined_orders(combined_group_id, db)


# Now the generic route comes after specific routes
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


@router.post(
    "/orders/{order_id}/shipments",
    response_model=OrderShipmentResponse,
    summary="Create single shipment for order",
    description="Create a new shipment/package for an order with tracking information. An order can have multiple shipments."
)
def create_order_shipment(
    order_id: int,
    data: OrderShipmentCreate,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_order_shipment(order_id, data, db)


@router.post(
    "/orders/{order_id}/shipments/bulk",
    response_model=List[OrderShipmentResponse],
    summary="Create multiple shipments for order",
    description="Create multiple shipments/packages for an order in a single request. Useful when an order is divided into multiple packages."
)
def create_order_shipments_bulk(
    order_id: int,
    data: OrderShipmentBulkCreate,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_order_shipments_bulk(order_id, data, db)


@router.get(
    "/orders/{order_id}/shipments",
    response_model=List[OrderShipmentResponse],
    summary="Get all shipments for order",
    description="Get all shipments/packages associated with an order."
)
def get_order_shipments(
    order_id: int,
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_order_shipments(order_id, db)


@router.patch(
    "/orders/{order_id}/shipments/{shipment_id}",
    response_model=OrderShipmentResponse,
    summary="Update shipment",
    description="Update tracking information for a shipment."
)
def update_order_shipment(
    order_id: int,
    shipment_id: int,
    data: OrderShipmentUpdate,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_order_shipment(order_id, shipment_id, data, db)


@router.delete(
    "/orders/{order_id}/shipments/{shipment_id}",
    summary="Delete shipment",
    description="Delete a shipment from an order."
)
def delete_order_shipment(
    order_id: int,
    shipment_id: int,
    app=Depends(admin_service.require_scope("orders:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_order_shipment(order_id, shipment_id, db)


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


# ==================== USER ACTIVITY TRACKING ====================
# NOTE: This endpoint must come BEFORE /users/{user_id} to avoid route conflicts

@router.get(
    "/users/by-activity",
    response_model=dict,  # Using dict because schema is complex
    summary="Get users ordered by last activity",
    description="""Get a paginated list of users ordered by their most recent activity.
    
    Useful for seeing which users are most active. Users without any activities
    will appear at the end sorted by creation date.
    """
)
def get_users_by_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by email, phone, or name"),
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    return activity_service.get_users_by_last_activity(
        db=db,
        page=page,
        page_size=page_size,
        search=search
    )


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


# ==================== SHIPPING RULES MANAGEMENT ====================
# These endpoints require shipping:read or shipping:write scope

@router.post(
    "/shipping-rules/sync",
    response_model=ShippingRulesSyncResponse,
    summary="Sync all shipping rules",
    description="""Sync all shipping rules from the admin dashboard.
    
    **This REPLACES all existing rules with the new ones.**
    
    **Rule Types:**
    - `free_weight_per_product`: Every X products from selected SKUs → Z lbs free
      - Requires: product_quantity, selected_products (array of seller_sku), free_weight_lbs
    - `free_weight_per_category`: Every X products from selected categories → Z lbs free
      - Requires: product_quantity, selected_categories (array of category slugs), free_weight_lbs
    - `minimum_weight_charge`: If total weight < X lbs → charge $Y
      - Requires: minimum_weight_lbs, charge_amount
    - `base_rate`: Rate per lb for remaining billable weight
      - Requires: rate_per_lb
    
    **Priority:** Lower number = higher priority (evaluated first).
    
    Returns warnings for SKUs or categories not found in database (non-blocking).
    """
)
def sync_shipping_rules(
    data: ShippingRulesSyncRequest,
    app=Depends(admin_service.require_scope("shipping:write")),
    db: Session = Depends(get_db)
):
    return admin_service.sync_shipping_rules(data, db)


@router.post(
    "/shipping-rules",
    response_model=ShippingRuleResponse,
    summary="Create shipping rule",
    description="""Create a single new shipping rule.
    
    **Rule Types:**
    - `free_weight_per_product`: Every X products from selected SKUs → Z lbs free
    - `free_weight_per_category`: Every X products from selected categories → Z lbs free
    - `minimum_weight_charge`: If total weight < X lbs → charge $Y
    - `base_rate`: Rate per lb for remaining billable weight
    
    **Priority:** Lower number = higher priority (evaluated first).
    """
)
def create_shipping_rule(
    data: ShippingRuleCreate,
    app=Depends(admin_service.require_scope("shipping:write")),
    db: Session = Depends(get_db)
):
    return admin_service.create_shipping_rule(data, db)


@router.get(
    "/shipping-rules",
    response_model=List[ShippingRuleResponse],
    summary="List shipping rules",
    description="Get all shipping rules with optional filters. Rules are ordered by priority."
)
def list_shipping_rules(
    rule_type: Optional[str] = Query(None, description="Filter by rule type (product_type, category, weight_threshold, base_rate)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    app=Depends(admin_service.require_scope("shipping:read")),
    db: Session = Depends(get_db)
):
    return admin_service.list_shipping_rules(db, rule_type, is_active)


@router.get(
    "/shipping-rules/{rule_id}",
    response_model=ShippingRuleResponse,
    summary="Get shipping rule",
    description="Get a specific shipping rule by ID."
)
def get_shipping_rule(
    rule_id: int,
    app=Depends(admin_service.require_scope("shipping:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_shipping_rule(rule_id, db)


@router.put(
    "/shipping-rules/{rule_id}",
    response_model=ShippingRuleResponse,
    summary="Update shipping rule",
    description="Update an existing shipping rule. Only provided fields will be updated."
)
def update_shipping_rule(
    rule_id: int,
    data: ShippingRuleUpdate,
    app=Depends(admin_service.require_scope("shipping:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_shipping_rule(rule_id, data, db)


@router.delete(
    "/shipping-rules/{rule_id}",
    summary="Delete shipping rule",
    description="Permanently delete a shipping rule."
)
def delete_shipping_rule(
    rule_id: int,
    app=Depends(admin_service.require_scope("shipping:write")),
    db: Session = Depends(get_db)
):
    return admin_service.delete_shipping_rule(rule_id, db)


# ==================== INVENTORY MANAGEMENT ====================
# These endpoints require inventory:write scope (or products:write as fallback)

@router.put(
    "/inventory/sku/{seller_sku}",
    response_model=InventoryUpdateResponse,
    summary="Update inventory by SKU",
    description="""Update stock quantity for a single product by its SKU.
    
    If `is_in_stock` is not provided, it will be automatically set based on stock > 0.
    """
)
def update_inventory_by_sku(
    seller_sku: str,
    data: InventoryUpdateSingle,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_inventory_by_sku(seller_sku, data, db)


@router.put(
    "/inventory/product/{product_id}",
    response_model=InventoryUpdateResponse,
    summary="Update inventory by product ID",
    description="""Update stock quantity for a single product by its ID.
    
    If `is_in_stock` is not provided, it will be automatically set based on stock > 0.
    """
)
def update_inventory_by_id(
    product_id: int,
    data: InventoryUpdateSingle,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_inventory_by_id(product_id, data, db)


@router.put(
    "/inventory/bulk",
    response_model=InventoryBulkUpdateResponse,
    summary="Bulk update inventory",
    description="""Update stock quantities for multiple products at once.
    
    Products are identified by their `seller_sku`.
    If `is_in_stock` is not provided for an item, it will be automatically set based on stock > 0.
    
    Returns the count of successfully updated products and any errors.
    """
)
def bulk_update_inventory(
    data: InventoryBulkUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_update_inventory(data, db)


# ==================== VARIANT INVENTORY MANAGEMENT ====================
# For products with variants, each variant has its own stock

@router.put(
    "/inventory/variant/sku/{seller_sku}",
    response_model=VariantInventoryUpdateResponse,
    summary="Update variant inventory by SKU",
    description="""Update stock quantity for a single product variant by its SKU.
    
    Use this for products with variants (colors, sizes, etc.) where each variant has its own stock.
    If `is_in_stock` is not provided, it will be automatically set based on stock > 0.
    """
)
def update_variant_inventory_by_sku(
    seller_sku: str,
    data: VariantInventoryUpdateSingle,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_variant_inventory_by_sku(seller_sku, data, db)


@router.put(
    "/inventory/variant/{variant_id}",
    response_model=VariantInventoryUpdateResponse,
    summary="Update variant inventory by ID",
    description="""Update stock quantity for a single product variant by its ID.
    
    If `is_in_stock` is not provided, it will be automatically set based on stock > 0.
    """
)
def update_variant_inventory_by_id(
    variant_id: int,
    data: VariantInventoryUpdateSingle,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_variant_inventory_by_id(variant_id, data, db)


@router.put(
    "/inventory/variants/bulk",
    response_model=VariantInventoryBulkUpdateResponse,
    summary="Bulk update variant inventory",
    description="""Update stock quantities for multiple product variants at once.
    
    Variants are identified by their `seller_sku`.
    If `is_in_stock` is not provided for an item, it will be automatically set based on stock > 0.
    
    Returns the count of successfully updated variants and any errors.
    """
)
def bulk_update_variant_inventory(
    data: VariantInventoryBulkUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.bulk_update_variant_inventory(data, db)


# ==================== UNIFIED INVENTORY (FLAT LIST) ====================
# Simplified endpoints that handle both products and variants uniformly

@router.get(
    "/inventory",
    response_model=InventoryListResponse,
    summary="Get all inventory items (flat list)",
    description="""
    Returns a flat list of all inventory items:
    - Simple products (without variants)
    - Individual variants (for products with variants)
    
    Products with variants are NOT included - only their variants are listed.
    Each item has `is_variant` to indicate if it's a variant or simple product.
    
    Use the `search` parameter to filter by name, SKU, or brand.
    """
)
def get_inventory_list(
    search: Optional[str] = Query(None, description="Search by name, SKU, or brand"),
    app=Depends(admin_service.require_scope("products:read")),
    db: Session = Depends(get_db)
):
    return admin_service.get_inventory_list(db, search)


@router.put(
    "/inventory",
    response_model=InventoryUnifiedUpdateResponse,
    summary="Update inventory (unified)",
    description="""
    Update inventory for products and variants using a single endpoint.
    
    Send a list of SKUs with their new stock values. The system automatically
    detects if each SKU belongs to a simple product or a variant.
    
    **Important:**
    - For products with variants, you must update the variant SKUs (not the parent product SKU)
    - Parent product stock is automatically recalculated from its variants
    
    **Example:**
    ```json
    {
      "items": [
        {"seller_sku": "PROD-SIMPLE-001", "stock": 50},
        {"seller_sku": "TINTE-001-RUBIO", "stock": 25},
        {"seller_sku": "TINTE-001-NEGRO", "stock": 30}
      ]
    }
    ```
    """
)
def update_inventory_unified(
    data: InventoryUnifiedUpdate,
    app=Depends(admin_service.require_scope("products:write")),
    db: Session = Depends(get_db)
):
    return admin_service.update_inventory_unified(data, db)


# ==================== STORE SETTINGS MANAGEMENT ====================
# These endpoints require settings:read or settings:write scope

@router.get(
    "/settings",
    response_model=SettingsListResponse,
    summary="Get all store settings",
    description="""Get all store configuration settings.
    
    Settings include:
    - Store address (for tax calculation on pickup orders)
    - Tax configuration (method, rates, etc.)
    - Order limits (min/max order amounts)
    """
)
def get_all_settings(
    app=Depends(admin_service.require_scope("settings:read")),
    db: Session = Depends(get_db)
):
    service = get_settings_service(db)
    settings = service.get_all_settings()
    return {"settings": settings}


@router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="Get a single setting",
    description="Get a specific setting by its key."
)
def get_setting(
    key: str,
    app=Depends(admin_service.require_scope("settings:read")),
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    service = get_settings_service(db)
    setting = service.get_setting(key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return setting


@router.put(
    "/settings/{key}",
    response_model=SettingResponse,
    summary="Update a single setting",
    description="Update the value of a specific setting."
)
def update_setting(
    key: str,
    data: SettingUpdate,
    app=Depends(admin_service.require_scope("settings:write")),
    db: Session = Depends(get_db)
):
    from fastapi import HTTPException
    service = get_settings_service(db)
    setting = service.update_setting(key, data.value)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return setting


@router.put(
    "/settings",
    response_model=BulkSettingsResponse,
    summary="Bulk update settings",
    description="""Update multiple settings at once.
    
    **Example:**
    ```json
    {
      "settings": [
        {"key": "store_city", "value": "Albuquerque"},
        {"key": "store_state", "value": "NM"},
        {"key": "min_order_amount", "value": "50"}
      ]
    }
    ```
    """
)
def bulk_update_settings(
    data: BulkSettingsUpdate,
    app=Depends(admin_service.require_scope("settings:write")),
    db: Session = Depends(get_db)
):
    service = get_settings_service(db)
    updated_count = service.update_settings_bulk(data.settings)
    return {
        "success": True,
        "message": f"Successfully updated {updated_count} settings",
        "updated_count": updated_count
    }


@router.post(
    "/settings/seed",
    response_model=BulkSettingsResponse,
    summary="Seed default settings",
    description="""Initialize default settings if they don't exist.
    
    This is useful for first-time setup. Existing settings are not overwritten.
    """
)
def seed_default_settings(
    app=Depends(admin_service.require_scope("settings:write")),
    db: Session = Depends(get_db)
):
    service = get_settings_service(db)
    created_count = service.seed_default_settings()
    return {
        "success": True,
        "message": f"Created {created_count} default settings",
        "updated_count": created_count
    }


# ==================== USER ACTIVITY TRACKING (continued) ====================

@router.get(
    "/activities",
    response_model=dict,  # Using dict because schema is complex
    summary="Get all activities",
    description="""Get all activities from all users with pagination and optional filters.
    
    This endpoint returns activities from all users (or filtered by user_id if provided).
    Useful for admin analytics and monitoring system-wide activity.
    
    Filters:
    - `user_id`: Filter by specific user
    - `action_type`: Filter by action type (e.g., "view_products", "add_to_cart")
    - `start_date`, `end_date`: Filter by date range (ISO format)
    - `exclude_admin`: If true, excludes admin activities (endpoints starting with /admin)
    """
)
def get_all_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    exclude_admin: bool = Query(False, description="Exclude admin activities"),
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    from datetime import datetime
    from fastapi import HTTPException
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
    
    return activity_service.get_all_activities(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        action_type=action_type,
        start_date=start_dt,
        end_date=end_dt,
        exclude_admin=exclude_admin
    )


@router.get(
    "/users/{user_id}/activities",
    response_model=dict,  # Using dict because schema is complex
    summary="Get user activities",
    description="""Get all activities for a specific user with pagination.
    
    You can filter by action_type (e.g., "view_products", "add_to_cart", "checkout")
    and date range.
    
    Filters:
    - `action_type`: Filter by action type
    - `start_date`, `end_date`: Filter by date range (ISO format)
    - `exclude_admin`: If true, excludes admin activities (endpoints starting with /admin)
    """
)
def get_user_activities(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    exclude_admin: bool = Query(False, description="Exclude admin activities"),
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    from datetime import datetime
    from fastapi import HTTPException
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
    
    return activity_service.get_user_activities(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
        action_type=action_type,
        start_date=start_dt,
        end_date=end_dt,
        exclude_admin=exclude_admin
    )


@router.get(
    "/users/{user_id}/carts",
    response_model=List[dict],  # Using dict because schema is complex
    summary="Get user carts",
    description="""Get all carts for a specific user.
    
    Returns all carts (current and historical) with their items and totals.
    """
)
def get_user_carts(
    user_id: int,
    include_inactive: bool = Query(False, description="Include inactive/empty carts"),
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    return activity_service.get_user_carts(
        db=db,
        user_id=user_id,
        include_inactive=include_inactive
    )


@router.get(
    "/carts",
    response_model=dict,  # Using dict because schema is complex
    summary="Get all carts",
    description="""Get all carts with pagination (admin view).
    
    Useful for monitoring all active carts in the system.
    
    Sort options:
    - "updated_at" (default): Order by last update date (most recent first)
    - "created_at": Order by creation date (most recent first)
    - "user_email": Order alphabetically by user email
    - "user_name": Order alphabetically by user name
    """
)
def get_all_carts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    has_items: Optional[bool] = Query(None, description="Filter carts with/without items"),
    sort_by: str = Query("updated_at", description="Sort by: updated_at, created_at, user_email, user_name"),
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    return activity_service.get_all_carts(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        has_items=has_items,
        sort_by=sort_by
    )


@router.get(
    "/carts/{cart_id}",
    response_model=dict,  # Using dict because schema is complex
    summary="Get cart details",
    description="""Get detailed information about a specific cart including all items.
    """
)
def get_cart_details(
    cart_id: int,
    app=Depends(admin_service.require_scope("orders:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    from models import Cart
    from fastapi import HTTPException
    
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    carts = activity_service.get_user_carts(
        db=db,
        user_id=cart.user_id,
        session_id=cart.session_id,
        include_inactive=True
    )
    
    # Find the specific cart
    for cart_data in carts:
        if cart_data["id"] == cart_id:
            return cart_data
    
    raise HTTPException(status_code=404, detail="Cart not found")


@router.get(
    "/activities/stats",
    response_model=dict,
    summary="Get activity statistics",
    description="""Get statistics about user activities in the database.
    
    Useful for monitoring and understanding usage patterns.
    """
)
def get_activity_stats(
    app=Depends(admin_service.require_scope("users:read")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    return activity_service.get_activity_stats(db)


@router.post(
    "/activities/cleanup",
    response_model=dict,
    summary="Cleanup old activities",
    description="""Delete old activities from the database.
    
    **IMPORTANT:** This operation cannot be undone. Use `dry_run=true` first to see what would be deleted.
    
    **Recommended:** Run cleanup monthly to keep the table size manageable.
    """
)
def cleanup_activities(
    older_than_days: int = Query(90, ge=1, description="Delete activities older than this many days"),
    dry_run: bool = Query(True, description="If true, only return counts without deleting"),
    app=Depends(admin_service.require_scope("users:write")),
    db: Session = Depends(get_db)
):
    from services import activity_service
    return activity_service.cleanup_old_activities(
        db=db,
        older_than_days=older_than_days,
        dry_run=dry_run
    )
