"""
Cart schemas for shopping cart operations
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- Product/Variant Info in Cart ----------

class CartProductInfo(BaseModel):
    """Product information for cart display"""
    id: int
    seller_sku: Optional[str] = None
    name: str
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0

    class Config:
        from_attributes = True


class CartVariantInfo(BaseModel):
    """Variant information for cart display"""
    id: int
    seller_sku: Optional[str] = None
    name: str  # Display name e.g., "Rubio", "1 Kg", "Vol 30"
    variant_type: Optional[str] = None  # Type e.g., "Color", "Tamaño", "Volumen"
    variant_value: Optional[str] = None  # Clean value for display
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0

    class Config:
        from_attributes = True


# ---------- Cart Item Schemas ----------

class CartItemBase(BaseModel):
    """Base schema for cart item"""
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(ge=1, default=1)


class CartItemCreate(CartItemBase):
    """Schema for adding item to cart"""
    pass


class CartItemUpdate(BaseModel):
    """Schema for updating cart item quantity"""
    quantity: int = Field(ge=1)


class CartItemResponse(BaseModel):
    """Full cart item response with product details"""
    id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    product: CartProductInfo
    variant: Optional[CartVariantInfo] = None
    unit_price: float  # Current price (sale_price or regular_price)
    line_total: float  # unit_price * quantity
    stock_status: str  # "available", "low_stock", "out_of_stock", "reduced"
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- Stock Warning ----------

class StockWarning(BaseModel):
    """Warning about stock issues"""
    type: str  # "low_stock", "out_of_stock", "quantity_reduced"
    message: str
    available_stock: int
    requested_quantity: Optional[int] = None


# ---------- Cart Summary ----------

class CartSummary(BaseModel):
    """Summary of cart totals"""
    items_count: int  # Number of distinct items
    total_items: int  # Total quantity of all items
    subtotal: float  # Sum of all line_totals


# ---------- Shipping Incentive ----------

class ShippingIncentive(BaseModel):
    """Incentive to encourage adding more items for better shipping"""
    type: str  # "free_shipping", "reduced_shipping", "category_discount"
    message: str  # Message ready for display (in requested language)
    amount_needed: Optional[float] = None  # Additional amount needed
    items_needed: Optional[int] = None  # Additional items needed
    category: Optional[str] = None  # Specific category if applicable
    potential_savings: float  # How much they would save on shipping


# ---------- Cart Response ----------

class CartResponse(BaseModel):
    """Full cart response with order summary and validation"""
    id: int
    items_count: int
    total_items: int
    subtotal: float
    items: List[CartItemResponse] = []
    warnings: List[StockWarning] = []
    
    # Order Summary - Totals
    shipping_fee: float = 0.0
    tax: float = 0.0
    tax_rate: float = 0.0  # Tax rate percentage applied
    tax_source: str = "none"  # "grt_api", "fixed_rate", "store_rate", "none"
    total: float = 0.0  # subtotal + shipping_fee + tax
    
    # Checkout Validation
    can_checkout: bool = True
    min_order_amount: float = 0.0
    max_order_amount: float = 0.0
    order_validation_error: Optional[str] = None
    
    # Shipping Incentive (optional)
    shipping_incentive: Optional[ShippingIncentive] = None

    class Config:
        from_attributes = True


# ---------- Add Item Response ----------

class AddItemResponse(BaseModel):
    """Response when adding item to cart"""
    success: bool
    message: str
    item: Optional[CartItemResponse] = None
    cart_summary: CartSummary
    warning: Optional[StockWarning] = None


# ---------- Update Item Response ----------

class UpdateItemResponse(BaseModel):
    """Response when updating cart item"""
    success: bool
    message: str
    item: Optional[CartItemResponse] = None
    cart_summary: CartSummary
    warning: Optional[StockWarning] = None


# ---------- Delete Item Response ----------

class DeleteItemResponse(BaseModel):
    """Response when deleting cart item"""
    success: bool
    message: str
    cart_summary: CartSummary


# ---------- Clear Cart Response ----------

class ClearCartResponse(BaseModel):
    """Response when clearing cart"""
    success: bool
    message: str


# ---------- Merge Cart Response ----------

class MergeCartResponse(BaseModel):
    """Response when merging carts (on login)"""
    success: bool
    message: str
    merged_items: int
    cart: CartResponse


# ---------- Recommendations ----------

class RecommendedProduct(BaseModel):
    """Recommended product info"""
    id: int
    seller_sku: Optional[str] = None
    name: str
    name_en: Optional[str] = None
    image_url: Optional[str] = None
    regular_price: Optional[float] = None
    sale_price: Optional[float] = None
    is_in_stock: bool = True
    stock: int = 0
    brand: Optional[str] = None
    has_variants: bool = False
    recommendation_score: int  # How many cart items recommend this product

    class Config:
        from_attributes = True


class RecommendationsResponse(BaseModel):
    """Response for cart-based recommendations ('Te puede interesar')"""
    recommendations: List[RecommendedProduct] = []
    based_on_items: int  # Number of cart items used for recommendations
