"""
Product service for public frontend with localization support
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException

from models import Product
from schemas.product import (
    ProductPublic, 
    ProductVariantPublic, 
    VariantTypePublic,
    VariantCategoryPublic,
    PaginatedProductResponse
)
from utils.language import localize_field, localize_gallery


def _product_to_public(product: Product, lang: str = "es") -> ProductPublic:
    """Convert product model to localized public response with grouped variants"""
    variant_types = []
    
    if product.has_variants and product.variant_groups:
        # Group by variant_type
        grouped_by_type = {}
        for group in sorted(product.variant_groups, key=lambda g: g.display_order):
            vtype = group.variant_type or "General"
            if vtype not in grouped_by_type:
                grouped_by_type[vtype] = []
            grouped_by_type[vtype].append(group)
        
        # Build variant_types response
        for vtype, groups in grouped_by_type.items():
            # Check if this type has categories or is simple
            # Simple = single group with name=null OR name equals variant_type
            is_simple = (
                len(groups) == 1 and 
                (not groups[0].name or groups[0].name == vtype)
            )
            
            if not is_simple:
                # Has categories - build categories list
                categories = []
                for group in groups:
                    # Only include active variants
                    active_variants = [v for v in group.variants if getattr(v, 'active', True)]
                    if not active_variants:
                        continue
                    
                    variants = []
                    for v in sorted(active_variants, key=lambda v: v.display_order):
                        variants.append(ProductVariantPublic(
                            id=v.id,
                            seller_sku=v.seller_sku,
                            name=v.name,
                            variant_value=v.variant_value,
                            regular_price=v.regular_price,
                            sale_price=v.sale_price,
                            stock=v.stock,
                            is_in_stock=v.is_in_stock,
                            image_url=v.image_url
                        ))
                    
                    if variants:
                        categories.append(VariantCategoryPublic(
                            id=group.id,
                            name=group.name or vtype,
                            variants=variants
                        ))
                
                if categories:
                    variant_types.append(VariantTypePublic(
                        type=vtype,
                        categories=categories,
                        variants=None
                    ))
            else:
                # Simple variants (single group with name=null)
                group = groups[0]
                active_variants = [v for v in group.variants if getattr(v, 'active', True)]
                
                variants = []
                for v in sorted(active_variants, key=lambda v: v.display_order):
                    variants.append(ProductVariantPublic(
                        id=v.id,
                        seller_sku=v.seller_sku,
                        name=v.name,
                        variant_value=v.variant_value,
                        regular_price=v.regular_price,
                        sale_price=v.sale_price,
                        stock=v.stock,
                        is_in_stock=v.is_in_stock,
                        image_url=v.image_url
                    ))
                
                if variants:
                    variant_types.append(VariantTypePublic(
                        type=vtype,
                        categories=None,
                        variants=variants
                    ))
    
    return ProductPublic(
        id=product.id,
        seller_sku=product.seller_sku,
        name=localize_field(product.name, product.name_en, lang),
        short_description=localize_field(product.short_description, product.short_description_en, lang),
        description=localize_field(product.description, product.description_en, lang),
        tags=localize_field(product.tags, product.tags_en, lang),
        regular_price=product.regular_price,
        sale_price=product.sale_price,
        stock=product.stock,
        is_in_stock=product.is_in_stock,
        restock_date=product.restock_date,
        is_favorite=product.is_favorite,
        notify_when_available=product.notify_when_available,
        image_url=product.image_url,
        gallery=localize_gallery(product.gallery, lang),
        currency=product.currency,
        has_variants=product.has_variants,
        brand=product.brand,
        variant_types=variant_types
    )


def get_products(
    db: Session,
    lang: str = "es",
    search: Optional[str] = None,
    brand: Optional[str] = None,
    is_in_stock: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "name"
) -> PaginatedProductResponse:
    """Get paginated list of products with localization"""
    query = db.query(Product)
    
    # Search in both languages
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_filter),
                Product.name_en.ilike(search_filter),
                Product.tags.ilike(search_filter),
                Product.tags_en.ilike(search_filter),
                Product.brand.ilike(search_filter)
            )
        )
    
    if brand:
        query = query.filter(Product.brand == brand)
    
    if is_in_stock is not None:
        query = query.filter(Product.is_in_stock == is_in_stock)
    
    if min_price is not None:
        query = query.filter(Product.regular_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.regular_price <= max_price)
    
    # Get total count
    total_items = query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    # Sort
    if sort_by == "price_asc":
        query = query.order_by(Product.regular_price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.regular_price.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.name)
    
    # Paginate
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()
    
    return PaginatedProductResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        sorted_by=sort_by,
        results=[_product_to_public(p, lang) for p in products]
    )


def get_product_by_id(db: Session, product_id: int, lang: str = "es") -> ProductPublic:
    """Get a single product by ID with localization"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_public(product, lang)


def get_product_by_sku(db: Session, seller_sku: str, lang: str = "es") -> ProductPublic:
    """Get a single product by seller SKU with localization"""
    product = db.query(Product).filter(Product.seller_sku == seller_sku).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_public(product, lang)


def get_brands(db: Session) -> List[str]:
    """Get list of unique brands"""
    brands = db.query(Product.brand).distinct().filter(Product.brand.isnot(None)).all()
    return sorted([b[0] for b in brands if b[0]])
