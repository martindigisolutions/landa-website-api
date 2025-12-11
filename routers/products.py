from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from schemas.product import ProductPublic, PaginatedProductResponse, CategoryGroupPublic
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
    """,
    response_model=PaginatedProductResponse
)
def get_products(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
    search: Optional[str] = Query(None, description="Search by name, title, tags, or brand"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    is_in_stock: Optional[bool] = Query(None, description="Filter by availability"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    category: Optional[List[str]] = Query(None, description="Filter by category slug(s). Can be repeated for multiple categories."),
    category_group: Optional[str] = Query(None, description="Filter by category group slug"),
    sort_by: Optional[str] = Query("name", description="Sort by: name, price_asc, price_desc, newest"),
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
        page=page,
        page_size=page_size,
        sort_by=sort_by
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
