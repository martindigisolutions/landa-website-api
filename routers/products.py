from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from schemas.product import (
    ProductPublic, 
    PaginatedProductResponse, 
    CategoryGroupPublic,
    ToggleFavoriteResponse,
    FavoriteIdsResponse
)
from models import User
from database import get_db
from services import product_service, auth_service
from utils.language import get_language_from_header

router = APIRouter()


@router.get(
    "/categories",
    summary="List product categories",
    description="""
    Returns all category groups with their categories for filtering products.
    Only returns groups marked as `show_in_filters=true`.
    
    **Localization:** Send `Accept-Language: en` header for English, 
    or `Accept-Language: es` for Spanish (default).
    """,
    response_model=List[CategoryGroupPublic]
)
def get_categories(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
):
    lang = get_language_from_header(accept_language)
    return product_service.get_categories(db, lang)


@router.get(
    "/products",
    summary="List products",
    description="""
    Returns a paginated list of products with optional filters and sorting.
    
    **Localization:** Send `Accept-Language: en` header for English, 
    or `Accept-Language: es` for Spanish (default).
    
    **Category Filters:**
    - `category`: Filter by one or more category slugs (e.g., "tintes", "shampoos"). 
      Use multiple `category` parameters to filter by multiple categories: `?category=tintes&category=shampoos`
    - `category_group`: Filter by category group slug (e.g., "tipo-de-producto")
    
    **Similar Products Filter:**
    - `similar_to`: Get products that are similar to a specific product (by seller_sku or product ID).
      Returns only products listed in the `similar_products` field of that product.
    
    **Sort Options:**
    - `name`: Sort alphabetically by name (default)
    - `price_asc`: Sort by price ascending
    - `price_desc`: Sort by price descending
    - `newest`: Sort by creation date descending
    - `bestseller`: Sort by bestseller_order (products with order > 0, then by position)
    - `recommended`: Sort by recommended_order (products with order > 0, then by position)
    """,
    response_model=PaginatedProductResponse
)
def get_products(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    search: Optional[str] = Query(None, description="Search by name, title, tags, or brand"),
    brand: Optional[List[str]] = Query(None, description="Filter by brand(s). Can be repeated for multiple brands."),
    is_in_stock: Optional[bool] = Query(None, description="Filter by availability"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    category: Optional[List[str]] = Query(None, description="Filter by category slug(s). Can be repeated for multiple categories."),
    category_group: Optional[str] = Query(None, description="Filter by category group slug"),
    similar_to: Optional[str] = Query(None, description="Get similar products for this product (seller_sku or product ID)"),
    sort_by: Optional[str] = Query("recommended", description="Sort by: recommended, bestseller, name, name_asc, name_desc, price_asc, price_desc, newest"),
    include_variants: bool = Query(True, description="Include variant details in response. Set to false for better performance when variants are not needed."),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    lang = get_language_from_header(accept_language)
    return product_service.get_products(
        db=db,
        lang=lang,
        search=search,
        brand=brand,
        is_in_stock=is_in_stock,
        min_price=min_price,
        max_price=max_price,
        category=category,
        category_group=category_group,
        similar_to=similar_to,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        include_variants=include_variants
    )


@router.get(
    "/products/{product_id}",
    summary="Get product by ID",
    description="""
    Returns the details of a single product by its ID.
    
    **Localization:** Send `Accept-Language: en` header for English, 
    or `Accept-Language: es` for Spanish (default).
    """,
    response_model=ProductPublic
)
def get_product_by_id(
    product_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
):
    lang = get_language_from_header(accept_language)
    return product_service.get_product_by_id(db, product_id, lang)


@router.get(
    "/brands",
    summary="Get list of available brands",
    description="Returns a list of unique product brands available in the catalog, ordered alphabetically.",
    response_model=List[str]
)
def get_brands(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    return product_service.get_brands(db)


# ==================== FAVORITES ====================

@router.post(
    "/products/{product_id}/favorite",
    summary="Toggle product favorite",
    description="""
    Toggle a product as favorite for the authenticated user.
    - If the product is not a favorite, it will be added to favorites.
    - If the product is already a favorite, it will be removed from favorites.
    
    Returns the new favorite status.
    """,
    response_model=ToggleFavoriteResponse
)
def toggle_favorite(
    product_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    return product_service.toggle_favorite(db, current_user, product_id)


@router.get(
    "/favorites",
    summary="Get user's favorite products",
    description="""
    Returns a paginated list of the authenticated user's favorite products.
    Products are ordered by when they were added to favorites (newest first).
    
    **Localization:** Send `Accept-Language: en` header for English, 
    or `Accept-Language: es` for Spanish (default).
    """,
    response_model=PaginatedProductResponse
)
def get_favorites(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    lang = get_language_from_header(accept_language)
    return product_service.get_user_favorites(db, current_user, lang, page, page_size)


@router.get(
    "/favorites/ids",
    summary="Get IDs of user's favorite products",
    description="""
    Returns a list of product IDs that are favorites for the authenticated user.
    Useful for quickly checking which products are favorites without loading full product data.
    """,
    response_model=FavoriteIdsResponse
)
def get_favorite_ids(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    ids = product_service.get_user_favorite_ids(db, current_user)
    return FavoriteIdsResponse(product_ids=ids)


@router.get(
    "/products/{product_id}/is-favorite",
    summary="Check if product is favorite",
    description="Check if a specific product is in the authenticated user's favorites.",
)
def check_is_favorite(
    product_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    is_fav = product_service.is_product_favorite(db, current_user, product_id)
    return {"product_id": product_id, "is_favorite": is_fav}
