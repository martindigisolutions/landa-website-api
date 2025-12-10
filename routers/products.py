from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from schemas.product import ProductPublic, PaginatedProductResponse
from models import User
from database import get_db
from services import product_service, auth_service
from utils.language import get_language_from_header

router = APIRouter()


@router.get(
    "/products",
    summary="List products",
    description="""
    Returns a paginated list of products with optional filters and sorting.
    
    **Localization:** Send `Accept-Language: en` header for English, 
    or `Accept-Language: es` for Spanish (default).
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
