from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy import asc, desc
from schemas import ProductSchema, PaginatedProductResponse
from models import Product, User
from database import get_db
from services import product_service, auth_service

router = APIRouter()

@router.get(
    "/products",
    summary="List products",
    description="Returns a paginated list of products with optional filters and sorting.",
    response_model=PaginatedProductResponse
)
def get_products(
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
    brand: Optional[List[str]] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    order_by: Optional[str] = Query(None, pattern="^(price|name|stock)$"),
    direction: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    return product_service.get_products(
        db=db,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        order_by=order_by,
        direction=direction,
        page=page,
        page_size=page_size
    )


@router.get(
    "/products/{product_id}",
    summary="Get product by ID",
    description="Returns the details of a single product by its ID.",
    response_model=ProductSchema
)
def get_product_by_id(
    product_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    return product_service.get_product_by_id(product_id, db)
