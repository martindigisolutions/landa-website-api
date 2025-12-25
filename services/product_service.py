"""
Product service for public frontend with localization support
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException

from models import Product, CategoryGroup, Category, ProductCategory, UserFavorite, User
from schemas.product import (
    ProductPublic, 
    ProductVariantPublic, 
    VariantTypePublic,
    VariantCategoryPublic,
    PaginatedProductResponse,
    CategoryGroupPublic,
    CategoryPublic,
    RelatedProductPublic
)
from utils.language import localize_field, localize_gallery


def _get_min_variant_prices(product: Product) -> tuple[float | None, float | None]:
    """
    Get the minimum regular_price and sale_price from all variants.
    Returns (min_regular_price, min_sale_price)
    """
    if not product.has_variants or not product.variant_groups:
        return product.regular_price, product.sale_price
    
    all_regular_prices = []
    all_sale_prices = []
    
    for group in product.variant_groups:
        for variant in group.variants:
            if getattr(variant, 'active', True):  # Only active variants
                if variant.regular_price is not None:
                    all_regular_prices.append(variant.regular_price)
                if variant.sale_price is not None:
                    all_sale_prices.append(variant.sale_price)
    
    min_regular = min(all_regular_prices) if all_regular_prices else product.regular_price
    min_sale = min(all_sale_prices) if all_sale_prices else product.sale_price
    
    return min_regular, min_sale


def _resolve_related_products(
    skus: list, 
    db: Session, 
    lang: str = "es"
) -> List[RelatedProductPublic]:
    """
    Resolve a list of seller_sku to actual product data.
    Only returns products that exist and are in stock.
    Maintains the original order.
    """
    if not skus:
        return []
    
    # Get all products that match the SKUs and are in stock
    products = db.query(Product).filter(
        Product.seller_sku.in_(skus),
        Product.is_in_stock == True
    ).all()
    
    # Create a lookup dict by seller_sku
    products_by_sku = {p.seller_sku: p for p in products}
    
    # Return in original order, skipping non-existent SKUs
    result = []
    for sku in skus:
        if sku in products_by_sku:
            p = products_by_sku[sku]
            # Get min prices from variants if available
            min_regular, min_sale = _get_min_variant_prices(p)
            result.append(RelatedProductPublic(
                id=p.id,
                seller_sku=p.seller_sku,
                name=localize_field(p.name, p.name_en, lang),
                regular_price=min_regular,
                sale_price=min_sale,
                image_url=p.image_url,
                is_in_stock=p.is_in_stock,
                brand=p.brand,
                has_variants=p.has_variants
            ))
    
    return result


def get_categories(db: Session, lang: str = "es") -> List[CategoryGroupPublic]:
    """Get all category groups with their categories (localized)"""
    groups = db.query(CategoryGroup).order_by(CategoryGroup.display_order, CategoryGroup.name).all()
    
    result = []
    for group in groups:
        # Only include groups that should show in filters
        if not group.show_in_filters:
            continue
            
        categories = [
            CategoryPublic(
                id=cat.id,
                name=localize_field(cat.name, cat.name_en, lang),
                slug=cat.slug,
                color=cat.color,
                icon=cat.icon
            )
            for cat in sorted(group.categories, key=lambda c: (c.display_order, c.name))
        ]
        
        # Only include groups with categories
        if categories:
            result.append(CategoryGroupPublic(
                id=group.id,
                name=localize_field(group.name, group.name_en, lang),
                slug=group.slug,
                icon=group.icon,
                show_in_filters=group.show_in_filters,
                categories=categories
            ))
    
    return result


def _product_to_public(product: Product, lang: str = "es", db: Session = None) -> ProductPublic:
    """Convert product model to localized public response with grouped variants"""
    variant_types = []
    
    # Calculate min prices from variants (if product has variants)
    min_regular_price, min_sale_price = _get_min_variant_prices(product)
    
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
    
    # Resolve related products (only if db is provided)
    similar = []
    frequently_bought = []
    if db:
        similar = _resolve_related_products(product.similar_products or [], db, lang)
        frequently_bought = _resolve_related_products(product.frequently_bought_together or [], db, lang)
    
    return ProductPublic(
        id=product.id,
        seller_sku=product.seller_sku,
        name=localize_field(product.name, product.name_en, lang),
        short_description=localize_field(product.short_description, product.short_description_en, lang),
        description=localize_field(product.description, product.description_en, lang),
        tags=localize_field(product.tags, product.tags_en, lang),
        regular_price=min_regular_price,  # Use min from variants if available
        sale_price=min_sale_price,  # Use min from variants if available
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
        bestseller_order=product.bestseller_order or 0,
        recommended_order=product.recommended_order or 0,
        variant_types=variant_types,
        similar_products=similar,
        frequently_bought_together=frequently_bought
    )


def get_products(
    db: Session,
    lang: str = "es",
    search: Optional[str] = None,
    brand: Optional[List[str]] = None,
    is_in_stock: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[List[str]] = None,
    category_group: Optional[str] = None,
    similar_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "name"
) -> PaginatedProductResponse:
    """Get paginated list of products with localization.
    
    Args:
        similar_to: If provided, returns only products that are in the 
                   similar_products array of the specified product.
                   Can be a seller_sku or product ID.
    """
    query = db.query(Product)
    
    # Handle similar_to filter FIRST - restricts to products in similar_products array
    if similar_to:
        # Try to find the source product by SKU first, then by ID
        source_product = db.query(Product).filter(Product.seller_sku == similar_to).first()
        if not source_product:
            # Try by ID
            try:
                product_id = int(similar_to)
                source_product = db.query(Product).filter(Product.id == product_id).first()
            except ValueError:
                pass
        
        if not source_product:
            raise HTTPException(status_code=404, detail=f"Product '{similar_to}' not found")
        
        # Get the similar_products array (list of seller_sku strings)
        similar_skus = source_product.similar_products or []
        
        if not similar_skus:
            # No similar products defined - return empty response
            return PaginatedProductResponse(
                page=page,
                page_size=page_size,
                total_items=0,
                total_pages=0,
                sorted_by=sort_by,
                results=[]
            )
        
        # Filter to only products with SKUs in the similar_products array
        query = query.filter(Product.seller_sku.in_(similar_skus))
    
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
        query = query.filter(Product.brand.in_(brand))
    
    if is_in_stock is not None:
        query = query.filter(Product.is_in_stock == is_in_stock)
    
    if min_price is not None:
        query = query.filter(Product.regular_price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.regular_price <= max_price)
    
    # Filter by category slug(s)
    if category:
        query = query.join(ProductCategory).join(Category).filter(Category.slug.in_(category))
    
    # Filter by category group slug
    if category_group:
        query = query.join(ProductCategory).join(Category).join(CategoryGroup).filter(CategoryGroup.slug == category_group)
    
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
    elif sort_by == "bestseller":
        # Products with bestseller_order > 0 first, then by order ascending
        query = query.filter(Product.bestseller_order > 0).order_by(Product.bestseller_order.asc())
    elif sort_by == "recommended":
        # Products with recommended_order > 0 first, then by order ascending
        query = query.filter(Product.recommended_order > 0).order_by(Product.recommended_order.asc())
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
        results=[_product_to_public(p, lang, db) for p in products]
    )


def get_product_by_id(db: Session, product_id: int, lang: str = "es") -> ProductPublic:
    """Get a single product by ID with localization and resolved related products"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_public(product, lang, db)  # Pass db to resolve related products


def get_product_by_sku(db: Session, seller_sku: str, lang: str = "es") -> ProductPublic:
    """Get a single product by seller SKU with localization and resolved related products"""
    product = db.query(Product).filter(Product.seller_sku == seller_sku).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_to_public(product, lang, db)  # Pass db to resolve related products


def get_brands(db: Session) -> List[str]:
    """Get list of unique brands"""
    brands = db.query(Product.brand).distinct().filter(Product.brand.isnot(None)).all()
    return sorted([b[0] for b in brands if b[0]])


# ---------- User Favorites ----------

def toggle_favorite(db: Session, user: User, product_id: int) -> dict:
    """Toggle a product as favorite for a user. Returns new favorite status."""
    # Check product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if already a favorite
    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id,
        UserFavorite.product_id == product_id
    ).first()
    
    if existing:
        # Remove from favorites
        db.delete(existing)
        db.commit()
        return {
            "product_id": product_id,
            "is_favorite": False,
            "message": "Product removed from favorites"
        }
    else:
        # Add to favorites
        favorite = UserFavorite(
            user_id=user.id,
            product_id=product_id
        )
        db.add(favorite)
        db.commit()
        return {
            "product_id": product_id,
            "is_favorite": True,
            "message": "Product added to favorites"
        }


def get_user_favorites(
    db: Session, 
    user: User, 
    lang: str = "es",
    page: int = 1,
    page_size: int = 20
) -> PaginatedProductResponse:
    """Get paginated list of user's favorite products"""
    # Get favorite product IDs
    favorites_query = db.query(UserFavorite.product_id).filter(
        UserFavorite.user_id == user.id
    )
    
    # Get total count
    total_items = favorites_query.count()
    total_pages = (total_items + page_size - 1) // page_size
    
    # Get paginated favorites ordered by when they were added
    offset = (page - 1) * page_size
    favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id
    ).order_by(UserFavorite.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Get the products
    product_ids = [f.product_id for f in favorites]
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    
    # Create lookup and maintain order
    products_by_id = {p.id: p for p in products}
    ordered_products = [products_by_id[pid] for pid in product_ids if pid in products_by_id]
    
    return PaginatedProductResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        sorted_by="added_date",
        results=[_product_to_public(p, lang, db) for p in ordered_products]
    )


def is_product_favorite(db: Session, user: User, product_id: int) -> bool:
    """Check if a product is in user's favorites"""
    return db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id,
        UserFavorite.product_id == product_id
    ).first() is not None


def get_user_favorite_ids(db: Session, user: User) -> List[int]:
    """Get list of product IDs that are favorites for the user"""
    favorites = db.query(UserFavorite.product_id).filter(
        UserFavorite.user_id == user.id
    ).all()
    return [f[0] for f in favorites]
