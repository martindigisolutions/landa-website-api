from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy import asc, desc
from models import Product
import math

def get_products(
    db: Session,
    brand: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = "asc",
    page: int = 1,
    page_size: int = 20
):
    query = db.query(Product)

    if brand:
        query = query.filter(Product.brand.in_(brand))
    if min_price is not None:
        query = query.filter(Product.sale_price != None, Product.sale_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.sale_price != None, Product.sale_price <= max_price)

    if order_by:
        sort_column = {
            "price": Product.sale_price,
            "name": Product.name,
            "stock": Product.stock
        }.get(order_by)
        if sort_column is not None:
            query = query.order_by(asc(sort_column) if direction == "asc" else desc(sort_column))

    total_items = query.count()
    total_pages = math.ceil(total_items / page_size)
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    return {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "sorted_by": f"{order_by}_{direction}" if order_by else "",
        "results": results
    }

def get_product_by_id(product_id: int, db: Session):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise Exception("Product not found")
    return product

def get_brands(db: Session):
    brands = (
        db.query(Product.brand)
        .filter(Product.brand.isnot(None))
        .distinct()
        .order_by(asc(Product.brand))
        .all()
    )
    return [b[0] for b in brands]
