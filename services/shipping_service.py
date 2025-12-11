"""
Shipping calculation service with smart suggestions.

This service calculates shipping costs based on configured rules and provides
suggestions to customers when they're close (80%+) to achieving free weight.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from math import floor

from models import Product, ProductCategory, Category, ShippingRule
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


def _get_active_rules(db: Session) -> List[ShippingRule]:
    """Get all active shipping rules ordered by priority"""
    return db.query(ShippingRule).filter(
        ShippingRule.is_active == True
    ).order_by(ShippingRule.priority, ShippingRule.id).all()


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


def _calculate_total_weight(cart_items: List[dict], product_info: Dict[int, dict]) -> float:
    """Calculate total weight of all items in cart"""
    total = 0.0
    for item in cart_items:
        product_id = item["product_id"]
        quantity = item["quantity"]
        if product_id in product_info:
            total += product_info[product_id]["weight_lbs"] * quantity
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
    
    # Calculate total weight
    total_weight = _calculate_total_weight(cart_items, product_info)
    
    # Track applied rules and free weight
    applied_rules: List[AppliedShippingRule] = []
    suggestions: List[ShippingSuggestion] = []
    total_free_weight = 0.0
    shipping_cost = 0.0
    base_rate_applied = False
    minimum_charge_rule = None
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
                    suggestions.append(ShippingSuggestion(
                        suggestion_type="add_products_for_free_weight",
                        message=f"¡Agrega {products_for_next} producto(s) más de los productos seleccionados para obtener {rule.free_weight_lbs} libras de envío gratis!",
                        message_en=f"Add {products_for_next} more selected product(s) to get {rule.free_weight_lbs} lbs free shipping!",
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
            minimum_charge_rule = rule
        
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
    
    # Apply minimum weight charge if applicable
    if minimum_charge_rule and billable_weight > 0 and billable_weight < minimum_charge_rule.minimum_weight_lbs:
        shipping_cost += minimum_charge_rule.charge_amount
        applied_rules.append(AppliedShippingRule(
            rule_name=minimum_charge_rule.name,
            rule_type=minimum_charge_rule.rule_type,
            free_weight_granted=0
        ))
    
    # Apply base rate for billable weight
    if base_rate_rule and billable_weight > 0:
        # Only charge base rate if not already covered by minimum charge
        if not (minimum_charge_rule and billable_weight < minimum_charge_rule.minimum_weight_lbs):
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

