"""
Middleware for tracking user activities automatically.
Intercepts all API requests and logs user activities asynchronously.
"""
import json
import logging
from typing import Callable, Optional
from fastapi import Request, BackgroundTasks
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session

logger = logging.getLogger("landa-api.activity")

# Import database and services
from database import SessionLocal
from services import activity_service


def get_action_type(method: str, endpoint: str) -> str:
    """
    Determine action type based on HTTP method and endpoint.
    Returns a descriptive action type string.
    """
    endpoint_lower = endpoint.lower()
    
    # Product actions
    if endpoint_lower.startswith("/products"):
        if method == "GET":
            if "search" in endpoint_lower or "?" in endpoint:
                return "search_products"
            return "view_products"
        elif method == "POST":
            return "create_product"  # Admin only
        elif method in ["PUT", "PATCH"]:
            return "update_product"  # Admin only
        elif method == "DELETE":
            return "delete_product"  # Admin only
    
    # Product detail
    if endpoint_lower.startswith("/products/") and method == "GET":
        return "view_product_detail"
    
    # Categories
    if endpoint_lower.startswith("/categories") and method == "GET":
        return "view_categories"
    
    # Cart actions
    if endpoint_lower.startswith("/cart"):
        if method == "GET":
            return "view_cart"
        elif method == "POST" and "/add" in endpoint_lower:
            return "add_to_cart"
        elif method in ["PUT", "PATCH"] and "/update" in endpoint_lower:
            return "update_cart_item"
        elif method == "DELETE":
            return "remove_from_cart"
        elif method == "POST" and "/clear" in endpoint_lower:
            return "clear_cart"
        elif method == "POST" and "/lock" in endpoint_lower:
            return "lock_cart"
        elif method == "POST" and "/merge" in endpoint_lower:
            return "merge_cart"
        elif method in ["PUT", "PATCH"] and "/shipping" in endpoint_lower:
            return "update_shipping"
        elif method in ["PUT", "PATCH"] and "/payment" in endpoint_lower:
            return "update_payment_method"
    
    # Checkout actions
    if endpoint_lower.startswith("/checkout"):
        if method == "POST" and "/create" in endpoint_lower:
            return "initiate_checkout"
        elif method == "POST" and "/complete" in endpoint_lower:
            return "complete_checkout"
        elif method == "GET":
            return "view_checkout"
    
    # Payment/Stripe actions
    if endpoint_lower.startswith("/stripe") or endpoint_lower.startswith("/payment"):
        if method == "POST" and "intent" in endpoint_lower:
            return "create_payment_intent"
        elif method == "POST" and "confirm" in endpoint_lower:
            return "confirm_payment"
        elif method == "POST" and "webhook" in endpoint_lower:
            return "payment_webhook"
        return "payment_action"
    
    # Order actions
    if endpoint_lower.startswith("/orders"):
        if method == "GET":
            return "view_orders"
        elif method == "POST":
            return "create_order"
        elif method in ["PUT", "PATCH"]:
            return "update_order"
    
    # User actions
    if endpoint_lower.startswith("/register") and method == "POST":
        return "register"
    if endpoint_lower.startswith("/login") and method == "POST":
        return "login"
    if endpoint_lower.startswith("/forgot-password") and method == "POST":
        return "forgot_password"
    if endpoint_lower.startswith("/reset-password") and method == "POST":
        return "reset_password"
    if endpoint_lower.startswith("/users") and method in ["PUT", "PATCH"]:
        return "update_profile"
    
    # Admin actions
    if endpoint_lower.startswith("/admin"):
        return f"admin_{method.lower()}_{endpoint_lower.replace('/', '_').strip('_')}"
    
    # Default
    return f"{method.lower()}_{endpoint_lower.replace('/', '_').strip('_')}"


def sanitize_request_body(body: dict, max_size: int = 1000) -> Optional[dict]:
    """
    Sanitize request body to avoid storing sensitive data.
    Removes passwords, tokens, and limits size.
    """
    if not body:
        return None
    
    # Convert to string to check size
    body_str = json.dumps(body)
    if len(body_str) > max_size:
        # Truncate if too large
        return {"_truncated": True, "_size": len(body_str)}
    
    # Remove sensitive fields
    sensitive_fields = [
        "password", "password_hash", "hashed_password", "token",
        "access_token", "refresh_token", "client_secret", "secret",
        "credit_card", "card_number", "cvv", "cvc", "security_code"
    ]
    
    sanitized = body.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***REDACTED***"
    
    # Recursively sanitize nested dicts
    for key, value in sanitized.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_request_body(value, max_size)
    
    return sanitized


async def extract_request_data(request: Request, path: str) -> dict:
    """
    Extract relevant data from the request.
    """
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Try to get request body (only for POST, PUT, PATCH)
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # Read body
            body_bytes = await request.body()
            if body_bytes:
                # Parse JSON if possible
                try:
                    body_dict = json.loads(body_bytes.decode())
                    request_body = sanitize_request_body(body_dict)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Not JSON, skip body
                    pass
        except Exception as e:
            logger.warning(f"Could not read request body: {e}")
    
    # Extract metadata based on endpoint and query params
    metadata = {}
    
    # Product search/filter metadata
    if "search" in query_params:
        metadata["search_query"] = query_params.get("search")
    
    # If viewing a specific product (from URL path or query param)
    # Try to extract product SKU if available
    product_id_from_path = None
    if "/products/" in path:
        try:
            # Extract product ID from path like /products/123
            path_parts = path.split("/products/")
            if len(path_parts) > 1:
                product_id_str = path_parts[1].split("/")[0].split("?")[0]
                if product_id_str.isdigit():
                    product_id_from_path = int(product_id_str)
        except (ValueError, IndexError):
            pass
    
    # Also check if there's a seller_sku or product_id in query params
    if "seller_sku" in query_params or "sku" in query_params:
        sku = query_params.get("seller_sku") or query_params.get("sku")
        if sku:
            metadata["product_sku"] = sku
    
    # If we have a product ID from path, try to get SKU from database
    if product_id_from_path:
        try:
            from models import Product
            db_temp = SessionLocal()
            try:
                product = db_temp.query(Product).filter(Product.id == product_id_from_path).first()
                if product:
                    metadata["product_id"] = product.id
                    if product.seller_sku:
                        metadata["product_sku"] = product.seller_sku
            finally:
                db_temp.close()
        except Exception:
            # Silently fail - SKU is optional
            pass
    if "category" in query_params:
        metadata["filters"] = {"categories": query_params.getlist("category") if hasattr(query_params, "getlist") else query_params.get("category")}
    if "brand" in query_params:
        metadata["filters"] = metadata.get("filters", {})
        metadata["filters"]["brands"] = query_params.getlist("brand") if hasattr(query_params, "getlist") else query_params.get("brand")
    if "min_price" in query_params or "max_price" in query_params:
        metadata["filters"] = metadata.get("filters", {})
        if "min_price" in query_params:
            metadata["filters"]["min_price"] = query_params.get("min_price")
        if "max_price" in query_params:
            metadata["filters"]["max_price"] = query_params.get("max_price")
    
    # Cart/add metadata from body
    if request_body:
        if "product_id" in request_body:
            product_id = request_body.get("product_id")
            metadata["product_id"] = product_id
            # Try to get product SKU from database (for admin reference)
            try:
                from models import Product
                db_temp = SessionLocal()
                try:
                    product = db_temp.query(Product).filter(Product.id == product_id).first()
                    if product and product.seller_sku:
                        metadata["product_sku"] = product.seller_sku
                finally:
                    db_temp.close()
            except Exception:
                # Silently fail - SKU is optional
                pass
        if "variant_id" in request_body:
            variant_id = request_body.get("variant_id")
            metadata["variant_id"] = variant_id
            # Try to get variant SKU from database
            try:
                from models import ProductVariant
                db_temp = SessionLocal()
                try:
                    variant = db_temp.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
                    if variant and variant.seller_sku:
                        metadata["variant_sku"] = variant.seller_sku
                finally:
                    db_temp.close()
            except Exception:
                # Silently fail - SKU is optional
                pass
        if "quantity" in request_body:
            metadata["quantity"] = request_body.get("quantity")
        if "cart_id" in request_body:
            metadata["cart_id"] = request_body.get("cart_id")
        if "order_id" in request_body:
            metadata["order_id"] = request_body.get("order_id")
        if "amount" in request_body or "total" in request_body:
            metadata["amount"] = request_body.get("amount") or request_body.get("total")
        if "payment_method" in request_body:
            metadata["payment_method"] = request_body.get("payment_method")
    
    # Pagination metadata
    if "page" in query_params:
        metadata["page"] = int(query_params.get("page", 1))
    if "page_size" in query_params:
        metadata["page_size"] = int(query_params.get("page_size", 20))
    
    return {
        "query_params": query_params,
        "request_body": request_body,
        "metadata": metadata
    }


def log_activity_background_sync(
    user_id: Optional[int],
    session_id: Optional[str],
    method: str,
    endpoint: str,
    action_type: str,
    metadata: dict,
    query_params: dict,
    request_body: Optional[dict],
    response_status: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """
    Synchronous function to log activity. Should be run in a thread pool.
    """
    try:
        db = SessionLocal()
        try:
            activity_service.log_activity(
                db=db,
                user_id=user_id,
                session_id=session_id,
                method=method,
                endpoint=endpoint,
                action_type=action_type,
                metadata=metadata,
                query_params=query_params,
                request_body=request_body,
                response_status=response_status,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error logging activity: {e}", exc_info=True)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating database session for activity logging: {e}", exc_info=True)


class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks all API requests as user activities.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health check and admin endpoints (optional - can enable if needed)
        path = request.url.path
        
        # Skip certain paths
        if path in ["/api/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Get user or app from token if available
        user_id = None
        session_id = None
        app_info = None  # Will contain app_name and app_client_id if it's an app token
        
        # Try to get user/app from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from jose import jwt, JWTError
                from config import SECRET_KEY, ALGORITHM
                
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                identifier = payload.get("sub")
                token_type = payload.get("type")  # "app" or None (user)
                
                if identifier:
                    db = SessionLocal()
                    try:
                        # Check if it's an application token
                        if token_type == "app":
                            # It's an OAuth2 application
                            from models import Application
                            app = db.query(Application).filter(
                                Application.client_id == identifier,
                                Application.is_active == True
                            ).first()
                            if app:
                                app_info = {
                                    "app_name": app.name,
                                    "app_client_id": app.client_id
                                }
                                logger.debug(f"Detected app token: {app.name} ({app.client_id})")
                        else:
                            # It's a user token
                            from models import User
                            from sqlalchemy import or_
                            user = db.query(User).filter(
                                or_(
                                    User.email == identifier,
                                    User.phone == identifier,
                                    User.whatsapp_phone == identifier
                                )
                            ).first()
                            if user:
                                user_id = user.id
                    finally:
                        db.close()
            except (JWTError, Exception) as e:
                # Invalid token or error - continue without user_id/app_info
                pass
        
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID")
        
        # Extract request data
        request_data = await extract_request_data(request, path)
        
        # Add app info to metadata if it's an application call
        if app_info:
            if "metadata" not in request_data:
                request_data["metadata"] = {}
            request_data["metadata"]["app_name"] = app_info["app_name"]
            request_data["metadata"]["app_client_id"] = app_info["app_client_id"]
            logger.debug(f"Added app info to metadata: {app_info['app_name']}")
        
        # Determine action type
        action_type = get_action_type(request.method, path)
        
        # Get IP address and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Process request
        response = await call_next(request)
        
        # Log activity in background (non-blocking)
        # Use asyncio executor to run synchronous DB operations in a thread pool
        # Note: This is fire-and-forget, errors won't affect the response
        try:
            import asyncio
            import concurrent.futures
            
            # Run in thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,  # Use default thread pool executor
                log_activity_background_sync,
                user_id,
                session_id,
                request.method,
                path,
                action_type,
                request_data.get("metadata", {}),
                request_data.get("query_params", {}),
                request_data.get("request_body"),
                response.status_code,
                ip_address,
                user_agent
            )
        except Exception as e:
            # Silently fail - don't let logging errors affect the request
            logger.warning(f"Could not schedule activity logging: {e}")
        
        return response

