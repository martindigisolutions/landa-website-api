"""
Shipping calculation service with smart suggestions.

This service calculates shipping costs based on configured rules and provides
suggestions to customers when they're close (80%+) to achieving free weight.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from math import floor

from models import Product, ProductCategory, Category, ShippingRule, ProductVariant
from schemas.checkout import (
    CalculateShippingRequest, CalculateShippingResponse,
    AppliedShippingRule, ShippingSuggestion
)


# Threshold for showing suggestions (80% progress toward a rule)
SUGGESTION_THRESHOLD = 0.8


def _get_product_info(product_ids: List[int], db: Session) -> Dict[int, dict]:
    """
    Get product info needed for shipping calculations.
    Returns dict mapping product_id to {seller_sku, weight_lbs, brand, category_slugs}
    """
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    
    product_info = {}
    for p in products:
        # Get category slugs for this product
        category_slugs = []
        for pc in p.product_categories:
            if pc.category:
                category_slugs.append(pc.category.slug)
        
        product_info[p.id] = {
            "seller_sku": p.seller_sku,
            "weight_lbs": p.weight_lbs or 0.0,
            "brand": p.brand,
            "category_slugs": category_slugs,
            "name": p.name
        }
    
    return product_info


def _get_item_weight(item: dict, product_info: Dict[int, dict], db: Session) -> float:
    """
    Get weight for a cart item, considering variant weight override.
    If variant has weight_lbs set, use it. Otherwise use product weight.
    """
    product_id = item.get("product_id")
    variant_id = item.get("variant_id")
    
    # Default to product weight
    weight = product_info.get(product_id, {}).get("weight_lbs", 0.0)
    
    # Check if variant has a weight override
    if variant_id:
        variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
        if variant and variant.weight_lbs is not None:
            weight = variant.weight_lbs
    
    return weight


def _get_active_rules(db: Session) -> List[ShippingRule]:
    """Get all active shipping rules ordered by priority"""
    return db.query(ShippingRule).filter(
        ShippingRule.is_active == True
    ).order_by(ShippingRule.priority, ShippingRule.id).all()


def _get_product_names_by_skus(skus: List[str], db: Session, lang: str = "es") -> Tuple[List[str], List[str]]:
    """
    Get product names from SKUs for display in messages.
    Returns tuple of (names_in_spanish, names_in_english)
    """
    if not skus:
        return [], []
    products = db.query(Product).filter(Product.seller_sku.in_(skus)).all()
    names_es = [p.name for p in products if p.name]
    names_en = [(p.name_en or p.name) for p in products if p.name]
    return names_es, names_en


def _count_matching_products_by_sku(
    cart_items: List[dict], 
    selected_skus: List[str], 
    product_info: Dict[int, dict]
) -> Tuple[int, float]:
    """
    Count how many products in cart match the selected SKUs.
    Returns (count, total_weight_of_matching_products)
    """
    count = 0
    weight = 0.0
    
    for item in cart_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        
        if product_id in product_info:
            sku = product_info[product_id]["seller_sku"]
            if sku and sku in selected_skus:
                count += quantity
                weight += (product_info[product_id]["weight_lbs"] * quantity)
    
    return count, weight


def _count_matching_products_by_category(
    cart_items: List[dict], 
    selected_categories: List[str], 
    product_info: Dict[int, dict]
) -> Tuple[int, float]:
    """
    Count how many products in cart belong to any of the selected categories.
    Returns (count, total_weight_of_matching_products)
    """
    count = 0
    weight = 0.0
    
    for item in cart_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        
        if product_id in product_info:
            product_categories = product_info[product_id]["category_slugs"]
            # Check if product belongs to any of the selected categories
            if any(cat in selected_categories for cat in product_categories):
                count += quantity
                weight += (product_info[product_id]["weight_lbs"] * quantity)
    
    return count, weight


def _calculate_total_weight(cart_items: List[dict], product_info: Dict[int, dict], db: Session) -> float:
    """Calculate total weight of all items in cart, considering variant weights"""
    total = 0.0
    for item in cart_items:
        quantity = item.get("quantity", 1)
        weight = _get_item_weight(item, product_info, db)
        total += weight * quantity
    return total


def _get_category_name(category_slug: str, db: Session) -> str:
    """Get category name from slug"""
    category = db.query(Category).filter(Category.slug == category_slug).first()
    return category.name if category else category_slug


def calculate_shipping(
    data: CalculateShippingRequest, 
    db: Session
) -> CalculateShippingResponse:
    """
    Calculate shipping cost based on cart contents and configured rules.
    
    Algorithm:
    1. Calculate total weight of cart
    2. Apply free_weight rules (per product/category) to accumulate free weight
    3. Calculate billable weight = total - free weight (min 0)
    4. Apply minimum_weight_charge if billable weight < threshold
    5. Apply base_rate to remaining billable weight
    6. Generate suggestions for customers close to achieving bonuses
    """
    
    # Get product IDs from cart
    product_ids = [item.product_id for item in data.products]
    cart_items = [{"product_id": item.product_id, "quantity": item.quantity} for item in data.products]
    
    # Get product info
    product_info = _get_product_info(product_ids, db)
    
    # Get active rules
    rules = _get_active_rules(db)
    
    # Calculate total weight (considering variant weights)
    total_weight = _calculate_total_weight(cart_items, product_info, db)
    
    # Track applied rules and free weight
    applied_rules: List[AppliedShippingRule] = []
    suggestions: List[ShippingSuggestion] = []
    total_free_weight = 0.0
    shipping_cost = 0.0
    base_rate_applied = False
    minimum_charge_rules: List = []  # Collect all minimum charge rules
    base_rate_rule = None
    
    # First pass: Calculate free weight from rules and collect suggestions
    for rule in rules:
        if rule.rule_type == "free_weight_per_product":
            matching_count, _ = _count_matching_products_by_sku(
                cart_items, rule.selected_products or [], product_info
            )
            
            if matching_count > 0:
                # Calculate how many times the rule triggers
                times_triggered = floor(matching_count / rule.product_quantity)
                free_weight_granted = times_triggered * rule.free_weight_lbs
                
                if free_weight_granted > 0:
                    total_free_weight += free_weight_granted
                    applied_rules.append(AppliedShippingRule(
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        free_weight_granted=free_weight_granted,
                        quantity_matched=matching_count
                    ))
                
                # Check if customer is close to next threshold (80%+)
                products_for_next = rule.product_quantity - (matching_count % rule.product_quantity)
                progress = (matching_count % rule.product_quantity) / rule.product_quantity
                
                if progress >= SUGGESTION_THRESHOLD and products_for_next > 0:
                    # Get product names for the message (Spanish and English)
                    names_es, names_en = _get_product_names_by_skus(rule.selected_products or [], db)
                    
                    # Build Spanish text
                    products_text_es = ", ".join(names_es[:3])
                    if len(names_es) > 3:
                        products_text_es += f" y {len(names_es) - 3} mas"
                    
                    # Build English text
                    products_text_en = ", ".join(names_en[:3])
                    if len(names_en) > 3:
                        products_text_en += f" and {len(names_en) - 3} more"
                    
                    suggestions.append(ShippingSuggestion(
                        suggestion_type="add_products_for_free_weight",
                        message=f"Agrega {products_for_next} producto(s) mas de: {products_text_es} para obtener {rule.free_weight_lbs} libras de envio gratis!",
                        message_en=f"Add {products_for_next} more of: {products_text_en} to get {rule.free_weight_lbs} lbs free shipping!",
                        products_needed=products_for_next,
                        potential_savings=rule.free_weight_lbs
                    ))
            
            # Also suggest if they have 0 but rule exists
            elif rule.product_quantity == 1:
                # Special case: if only 1 product needed, don't spam suggestions
                pass
        
        elif rule.rule_type == "free_weight_per_category":
            matching_count, _ = _count_matching_products_by_category(
                cart_items, rule.selected_categories or [], product_info
            )
            
            if matching_count > 0:
                times_triggered = floor(matching_count / rule.product_quantity)
                free_weight_granted = times_triggered * rule.free_weight_lbs
                
                if free_weight_granted > 0:
                    total_free_weight += free_weight_granted
                    applied_rules.append(AppliedShippingRule(
                        rule_name=rule.name,
                        rule_type=rule.rule_type,
                        free_weight_granted=free_weight_granted,
                        quantity_matched=matching_count
                    ))
                
                # Check if customer is close to next threshold
                products_for_next = rule.product_quantity - (matching_count % rule.product_quantity)
                progress = (matching_count % rule.product_quantity) / rule.product_quantity
                
                if progress >= SUGGESTION_THRESHOLD and products_for_next > 0:
                    # Get first category name for display
                    category_name = _get_category_name(rule.selected_categories[0], db) if rule.selected_categories else "la categoría"
                    
                    suggestions.append(ShippingSuggestion(
                        suggestion_type="add_products_for_free_weight",
                        message=f"¡Agrega {products_for_next} producto(s) más de {category_name} para obtener {rule.free_weight_lbs} libras de envío gratis!",
                        message_en=f"Add {products_for_next} more product(s) from {category_name} to get {rule.free_weight_lbs} lbs free shipping!",
                        products_needed=products_for_next,
                        category_name=category_name,
                        potential_savings=rule.free_weight_lbs
                    ))
        
        elif rule.rule_type == "minimum_weight_charge":
            minimum_charge_rules.append(rule)  # Collect all minimum charge rules
        
        elif rule.rule_type == "base_rate":
            base_rate_rule = rule
    
    # Calculate billable weight
    billable_weight = max(0, total_weight - total_free_weight)
    
    # Second pass: Apply charges
    
    # Check if remaining free weight capacity exists (for suggestions)
    if total_free_weight > 0 and billable_weight > 0:
        # Customer has some free weight but is over - let them know they can fill it
        remaining_free_capacity = total_free_weight - (total_weight - billable_weight)
        if remaining_free_capacity > 0:
            suggestions.append(ShippingSuggestion(
                suggestion_type="fill_remaining_weight",
                message=f"¡Todavía puedes agregar hasta {remaining_free_capacity:.1f} libras más por el mismo costo de envío!",
                message_en=f"You can still add up to {remaining_free_capacity:.1f} more lbs for the same shipping cost!",
                remaining_lbs=remaining_free_capacity
            ))
    
    # Find the applicable minimum charge rule
    # Sort by minimum_weight_lbs ascending to find the smallest threshold that applies
    applicable_min_charge = None
    if billable_weight > 0 and minimum_charge_rules:
        sorted_rules = sorted(minimum_charge_rules, key=lambda r: r.minimum_weight_lbs)
        for rule in sorted_rules:
            if billable_weight < rule.minimum_weight_lbs:
                applicable_min_charge = rule
                break
    
    # Apply minimum weight charge if applicable
    if applicable_min_charge:
        shipping_cost += applicable_min_charge.charge_amount
        applied_rules.append(AppliedShippingRule(
            rule_name=applicable_min_charge.name,
            rule_type=applicable_min_charge.rule_type,
            free_weight_granted=0
        ))
    
    # Apply base rate for billable weight (only if no minimum charge applied)
    if base_rate_rule and billable_weight > 0 and not applicable_min_charge:
        base_charge = billable_weight * base_rate_rule.rate_per_lb
        shipping_cost += base_charge
        base_rate_applied = True
    
    # Build summary message
    if shipping_cost == 0:
        summary = "¡Envío gratis!"
        summary_en = "Free shipping!"
    else:
        summary = f"Envío: ${shipping_cost:.2f}"
        summary_en = f"Shipping: ${shipping_cost:.2f}"
    
    return CalculateShippingResponse(
        total_weight_lbs=round(total_weight, 2),
        free_weight_lbs=round(total_free_weight, 2),
        billable_weight_lbs=round(billable_weight, 2),
        shipping_cost=round(shipping_cost, 2),
        applied_rules=applied_rules,
        suggestions=suggestions,
        summary=summary,
        summary_en=summary_en
    )


def calculate_shipping_cost_simple(cart_items: List[dict], db: Session) -> Tuple[float, List]:
    """
    Calculate shipping cost for cart items without requiring address.
    
    Args:
        cart_items: List of dicts with {product_id: int, quantity: int}
        db: Database session
    
    Returns:
        Tuple of (shipping_cost, suggestions)
    """
    if not cart_items:
        return 0.0, []
    
    # Get product IDs from cart
    product_ids = [item["product_id"] for item in cart_items]
    
    # Get product info
    product_info = _get_product_info(product_ids, db)
    
    # Get active rules
    rules = _get_active_rules(db)
    
    # Calculate total weight (considering variant weights)
    total_weight = _calculate_total_weight(cart_items, product_info, db)
    
    # Track applied rules and free weight
    suggestions: List = []
    total_free_weight = 0.0
    shipping_cost = 0.0
    minimum_charge_rules: List = []  # Collect all minimum charge rules
    base_rate_rule = None
    
    # First pass: Calculate free weight from rules and collect suggestions
    for rule in rules:
        if rule.rule_type == "free_weight_per_product":
            matching_count, _ = _count_matching_products_by_sku(
                cart_items, rule.selected_products or [], product_info
            )
            
            if matching_count > 0:
                times_triggered = floor(matching_count / rule.product_quantity)
                free_weight_granted = times_triggered * rule.free_weight_lbs
                total_free_weight += free_weight_granted
                
                # Check if customer is close to next threshold (80%+)
                products_for_next = rule.product_quantity - (matching_count % rule.product_quantity)
                progress = (matching_count % rule.product_quantity) / rule.product_quantity
                
                if progress >= SUGGESTION_THRESHOLD and products_for_next > 0:
                    # Get product names for the message (Spanish and English)
                    names_es, names_en = _get_product_names_by_skus(rule.selected_products or [], db)
                    
                    # Build Spanish text
                    products_text_es = ", ".join(names_es[:3])
                    if len(names_es) > 3:
                        products_text_es += f" y {len(names_es) - 3} mas"
                    
                    # Build English text
                    products_text_en = ", ".join(names_en[:3])
                    if len(names_en) > 3:
                        products_text_en += f" and {len(names_en) - 3} more"
                    
                    suggestions.append({
                        "type": "add_products",
                        "message": f"Agrega {products_for_next} producto(s) mas de: {products_text_es} para obtener {rule.free_weight_lbs} libras de envio gratis!",
                        "message_en": f"Add {products_for_next} more of: {products_text_en} to get {rule.free_weight_lbs} lbs free shipping!",
                        "items_needed": products_for_next,
                        "selected_products": names_es,  # Keep Spanish names for compatibility
                        "selected_products_en": names_en,
                        "potential_savings": rule.free_weight_lbs
                    })
        
        elif rule.rule_type == "free_weight_per_category":
            matching_count, _ = _count_matching_products_by_category(
                cart_items, rule.selected_categories or [], product_info
            )
            
            if matching_count > 0:
                times_triggered = floor(matching_count / rule.product_quantity)
                free_weight_granted = times_triggered * rule.free_weight_lbs
                total_free_weight += free_weight_granted
                
                # Check if customer is close to next threshold
                products_for_next = rule.product_quantity - (matching_count % rule.product_quantity)
                progress = (matching_count % rule.product_quantity) / rule.product_quantity
                
                if progress >= SUGGESTION_THRESHOLD and products_for_next > 0:
                    category_name = _get_category_name(rule.selected_categories[0], db) if rule.selected_categories else "la categoria"
                    suggestions.append({
                        "type": "add_category",
                        "message": f"Agrega {products_for_next} producto(s) mas de {category_name} para obtener {rule.free_weight_lbs} libras de envio gratis!",
                        "message_en": f"Add {products_for_next} more product(s) from {category_name} to get {rule.free_weight_lbs} lbs free shipping!",
                        "items_needed": products_for_next,
                        "category": category_name,
                        "potential_savings": rule.free_weight_lbs
                    })
        
        elif rule.rule_type == "minimum_weight_charge":
            minimum_charge_rules.append(rule)  # Collect all minimum charge rules
        
        elif rule.rule_type == "base_rate":
            base_rate_rule = rule
    
    # Calculate billable weight
    billable_weight = max(0, total_weight - total_free_weight)
    
    # Find the applicable minimum charge rule
    # Rules are sorted by priority, so we find the first one where billable_weight < minimum_weight_lbs
    # Sort by minimum_weight_lbs ascending to find the smallest threshold that applies
    applicable_min_charge = None
    if billable_weight > 0 and minimum_charge_rules:
        # Sort by minimum_weight_lbs (ascending) to find the smallest applicable threshold
        sorted_rules = sorted(minimum_charge_rules, key=lambda r: r.minimum_weight_lbs)
        for rule in sorted_rules:
            if billable_weight < rule.minimum_weight_lbs:
                applicable_min_charge = rule
                break
    
    # Apply minimum weight charge if applicable
    if applicable_min_charge:
        shipping_cost += applicable_min_charge.charge_amount
    
    # Apply base rate for billable weight (only if no minimum charge applied)
    if base_rate_rule and billable_weight > 0 and not applicable_min_charge:
        base_charge = billable_weight * base_rate_rule.rate_per_lb
        shipping_cost += base_charge
    
    final_cost = round(shipping_cost, 2)
    
    # Don't show suggestions if shipping is already free
    if final_cost == 0:
        suggestions = []
    
    return final_cost, suggestions


def calculate_shipping_cost(cart_items: List[dict], db: Session) -> float:
    """
    Calculate shipping cost for cart items.
    
    Args:
        cart_items: List of dicts with {product_id: int, quantity: int}
        db: Database session
    
    Returns:
        Shipping cost in dollars
    """
    cost, _ = calculate_shipping_cost_simple(cart_items, db)
    return cost


def get_shipping_incentive(cart_items: List[dict], db: Session) -> Optional[Dict]:
    """
    Get shipping incentive/suggestion for cart.
    
    Returns a dict with incentive info or None if no incentive applies.
    """
    if not cart_items:
        return None
    
    cost, suggestions = calculate_shipping_cost_simple(cart_items, db)
    
    if not suggestions:
        return None
    
    # Get the first/best suggestion
    suggestion = suggestions[0]
    
    # Map to incentive format
    incentive = {
        "type": "free_shipping" if cost > 0 else "reduced_shipping",
        "message": suggestion.get("message", ""),
        "message_en": suggestion.get("message_en", ""),
        "amount_needed": None,
        "items_needed": suggestion.get("items_needed"),
        "category": suggestion.get("category"),
        "potential_savings": cost  # They would save the shipping cost
    }
    
    return incentive

