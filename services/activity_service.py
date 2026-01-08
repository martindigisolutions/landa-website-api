"""
Service for tracking and querying user activities.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import UserActivity, User, Cart, CartItem
from pydantic import BaseModel


class ActivityMetadata(BaseModel):
    """Structured metadata for activities"""
    search_query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    quantity: Optional[int] = None
    cart_id: Optional[int] = None
    order_id: Optional[int] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    page: Optional[int] = None
    page_size: Optional[int] = None
    total_results: Optional[int] = None


def log_activity(
    db: Session,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    method: str = "GET",
    endpoint: str = "",
    action_type: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
    request_body: Optional[Dict[str, Any]] = None,
    response_status: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> UserActivity:
    """
    Log a user activity. This should be called asynchronously to avoid blocking requests.
    Note: The metadata parameter is stored as activity_metadata in the database
    (metadata is a reserved SQLAlchemy attribute).
    """
    """
    Log a user activity. This should be called asynchronously to avoid blocking requests.
    """
    activity = UserActivity(
        user_id=user_id,
        session_id=session_id,
        method=method,
        endpoint=endpoint,
        action_type=action_type,
        activity_metadata=metadata or {},
        query_params=query_params or {},
        request_body=request_body,
        response_status=response_status,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.utcnow()
    )
    
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def get_users_by_last_activity(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get users ordered by their last activity timestamp.
    Returns paginated list with user info and their last activity.
    """
    # Subquery to get last activity per user
    last_activity_subquery = (
        db.query(
            UserActivity.user_id,
            func.max(UserActivity.created_at).label('last_activity_at')
        )
        .filter(UserActivity.user_id.isnot(None))
        .group_by(UserActivity.user_id)
        .subquery()
    )
    
    # Base query joining users with their last activity
    query = (
        db.query(
            User,
            last_activity_subquery.c.last_activity_at
        )
        .outerjoin(
            last_activity_subquery,
            User.id == last_activity_subquery.c.user_id
        )
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                User.email.ilike(search_term),
                User.phone.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    # Order by last activity (most recent first), then by user creation date
    query = query.order_by(
        desc(last_activity_subquery.c.last_activity_at),
        desc(User.created_at)
    )
    
    # Get total count
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    # Apply pagination
    users_with_activity = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Get activity counts for all users in one query (avoid N+1 problem)
    activity_counts_subquery = (
        db.query(
            UserActivity.user_id,
            func.count(UserActivity.id).label('activity_count')
        )
        .filter(UserActivity.user_id.isnot(None))
        .group_by(UserActivity.user_id)
        .subquery()
    )
    
    # Get activity counts for all users in result set (optimized - single query)
    user_ids_in_page = [user.id for user, _ in users_with_activity]
    activity_counts_map = {}
    if user_ids_in_page:
        activity_counts = (
            db.query(
                UserActivity.user_id,
                func.count(UserActivity.id).label('count')
            )
            .filter(UserActivity.user_id.in_(user_ids_in_page))
            .group_by(UserActivity.user_id)
            .all()
        )
        activity_counts_map = {uid: count for uid, count in activity_counts}
    
    # Build response
    results = []
    for user, last_activity_at in users_with_activity:
        activity_count = activity_counts_map.get(user.id, 0)
        
        results.append({
            "user": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "whatsapp_phone": user.whatsapp_phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "is_blocked": user.is_blocked,
                "is_suspended": user.is_suspended
            },
            "last_activity_at": last_activity_at.isoformat() if last_activity_at else None,
            "total_activities": activity_count
        })
    
    return {
        "results": results,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages
        }
    }


def get_user_activities(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 50,
    action_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get all activities for a specific user with pagination and optional filters.
    """
    query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
    
    # Apply filters
    if action_type:
        query = query.filter(UserActivity.action_type == action_type)
    
    if start_date:
        query = query.filter(UserActivity.created_at >= start_date)
    
    if end_date:
        query = query.filter(UserActivity.created_at <= end_date)
    
    # Get total count
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    # Order by most recent first
    query = query.order_by(desc(UserActivity.created_at))
    
    # Apply pagination
    activities = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Build response
    results = []
    for activity in activities:
        results.append({
            "id": activity.id,
            "method": activity.method,
            "endpoint": activity.endpoint,
            "action_type": activity.action_type,
            "metadata": activity.activity_metadata or {},
            "query_params": activity.query_params or {},
            "response_status": activity.response_status,
            "ip_address": activity.ip_address,
            "created_at": activity.created_at.isoformat() if activity.created_at else None
        })
    
    return {
        "results": results,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages
        }
    }


def get_user_carts(
    db: Session,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    include_inactive: bool = False
) -> List[Dict[str, Any]]:
    """
    Get carts for a specific user or session.
    Returns all carts with their items and totals.
    """
    query = db.query(Cart)
    
    if user_id:
        query = query.filter(Cart.user_id == user_id)
    elif session_id:
        query = query.filter(Cart.session_id == session_id)
    else:
        return []
    
    # Filter active carts if needed
    if not include_inactive:
        # Only get carts that have items or were updated recently (last 30 days)
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        query = query.filter(
            or_(
                Cart.items.any(),  # Has items
                Cart.updated_at >= cutoff_date  # Updated recently
            )
        )
    
    carts = query.order_by(desc(Cart.updated_at)).all()
    
    results = []
    for cart in carts:
        # Calculate totals
        subtotal = 0.0
        items_count = 0
        total_items = 0
        
        items_data = []
        for item in cart.items:
            # Skip deleted products/variants
            if item.product is None:
                continue
            if item.variant_id is not None and item.variant is None:
                continue
            
            # Calculate item price
            unit_price = 0.0
            if item.variant and item.variant.regular_price is not None:
                unit_price = item.variant.regular_price
            elif item.variant and item.variant.sale_price is not None:
                unit_price = item.variant.sale_price
            elif item.product.regular_price is not None:
                unit_price = item.product.regular_price
            elif item.product.sale_price is not None:
                unit_price = item.product.sale_price
            
            line_total = unit_price * item.quantity
            subtotal += line_total
            items_count += 1
            total_items += item.quantity
            
            # Get SKUs for admin reference
            product_sku = None
            variant_sku = None
            if item.product:
                product_sku = item.product.seller_sku
            if item.variant:
                variant_sku = item.variant.seller_sku
            
            items_data.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_sku": product_sku,  # SKU for admin reference
                "product_name": item.product.name if item.product else None,
                "variant_id": item.variant_id,
                "variant_sku": variant_sku,  # SKU for admin reference
                "variant_name": item.variant.name if item.variant else None,
                "quantity": item.quantity,
                "unit_price": round(unit_price, 2),
                "line_total": round(line_total, 2),
                "added_at": item.added_at.isoformat() if item.added_at else None
            })
        
        results.append({
            "id": cart.id,
            "user_id": cart.user_id,
            "session_id": cart.session_id,
            "items": items_data,
            "summary": {
                "items_count": items_count,
                "total_items": total_items,
                "subtotal": round(subtotal, 2)
            },
            "shipping": {
                "first_name": cart.shipping_first_name,
                "last_name": cart.shipping_last_name,
                "phone": cart.shipping_phone,
                "email": cart.shipping_email,
                "street": cart.shipping_street,
                "city": cart.shipping_city,
                "state": cart.shipping_state,
                "zipcode": cart.shipping_zipcode,
                "country": cart.shipping_country,
                "is_pickup": cart.is_pickup
            },
            "payment_method": cart.payment_method,
            "created_at": cart.created_at.isoformat() if cart.created_at else None,
            "updated_at": cart.updated_at.isoformat() if cart.updated_at else None
        })
    
    return results


def get_all_carts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    has_items: Optional[bool] = None,
    sort_by: str = "updated_at"
) -> Dict[str, Any]:
    """
    Get all carts with pagination (for admin).
    
    sort_by options:
    - "updated_at" (default): Order by last update date (most recent first)
    - "created_at": Order by creation date (most recent first)
    - "user_email": Order alphabetically by user email
    - "user_name": Order alphabetically by user first_name + last_name
    """
    query = db.query(Cart)
    
    if user_id:
        query = query.filter(Cart.user_id == user_id)
    
    if has_items is not None:
        if has_items:
            query = query.filter(Cart.items.any())
        else:
            query = query.filter(~Cart.items.any())
    
    # Get total count
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    # Order by specified field
    if sort_by == "updated_at":
        query = query.order_by(desc(Cart.updated_at))
    elif sort_by == "created_at":
        query = query.order_by(desc(Cart.created_at))
    elif sort_by == "user_email":
        # Join with User table and order by email
        query = query.outerjoin(User).order_by(User.email.asc().nulls_last(), desc(Cart.updated_at))
    elif sort_by == "user_name":
        # Join with User table and order by first_name, then last_name
        query = query.outerjoin(User).order_by(User.first_name.asc().nulls_last(), User.last_name.asc().nulls_last(), desc(Cart.updated_at))
    else:
        # Default to updated_at if invalid sort_by
        query = query.order_by(desc(Cart.updated_at))
    
    # Apply pagination
    carts = query.offset((page - 1) * page_size).limit(page_size).all()
    
    results = []
    for cart in carts:
        # Get item count
        items_count = len([item for item in cart.items if item.product is not None])
        
        results.append({
            "id": cart.id,
            "user_id": cart.user_id,
            "session_id": cart.session_id,
            "user": {
                "id": cart.user.id if cart.user else None,
                "email": cart.user.email if cart.user else None,
                "phone": cart.user.phone if cart.user else None,
                "first_name": cart.user.first_name if cart.user else None,
                "last_name": cart.user.last_name if cart.user else None
            } if cart.user else None,
            "items_count": items_count,
            "payment_method": cart.payment_method,
            "is_pickup": cart.is_pickup,
            "created_at": cart.created_at.isoformat() if cart.created_at else None,
            "updated_at": cart.updated_at.isoformat() if cart.updated_at else None
        })
    
    return {
        "results": results,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages
        }
    }

