"""
Script para verificar productos con poco inventario.
Muestra productos y variantes cuyo stock es menor o igual a su umbral de stock bajo.
"""
from database import SessionLocal
from models import Product, ProductVariant, ProductVariantGroup

def get_low_stock_products():
    """Obtiene todos los productos con poco inventario"""
    db = SessionLocal()
    try:
        # Obtener todos los productos
        products = db.query(Product).all()
        
        low_stock_items = []
        
        for product in products:
            threshold = product.low_stock_threshold or 10  # Default 10 si es None
            
            if not product.has_variants:
                # Producto simple - verificar stock directamente
                if product.stock is not None and product.stock <= threshold:
                    low_stock_items.append({
                        'type': 'product',
                        'id': product.id,
                        'sku': product.seller_sku,
                        'name': product.name,
                        'stock': product.stock,
                        'threshold': threshold,
                        'is_in_stock': product.is_in_stock
                    })
            else:
                # Producto con variantes - verificar cada variante
                for group in product.variant_groups:
                    for variant in group.variants:
                        if getattr(variant, 'active', True):  # Solo variantes activas
                            # Usar el threshold del producto padre
                            if variant.stock is not None and variant.stock <= threshold:
                                low_stock_items.append({
                                    'type': 'variant',
                                    'variant_id': variant.id,
                                    'variant_sku': variant.seller_sku,
                                    'variant_name': variant.name,
                                    'product_id': product.id,
                                    'product_sku': product.seller_sku,
                                    'product_name': product.name,
                                    'stock': variant.stock,
                                    'threshold': threshold,
                                    'is_in_stock': variant.is_in_stock,
                                    'variant_type': group.variant_type,
                                    'group_name': group.name
                                })
        
        return low_stock_items
    finally:
        db.close()

def print_low_stock_report():
    """Imprime un reporte de productos con poco inventario"""
    items = get_low_stock_products()
    
    if not items:
        print("No hay productos con poco inventario.")
        return
    
    print(f"\nPRODUCTOS CON POCO INVENTARIO ({len(items)} items)\n")
    print("=" * 80)
    
    # Separar productos simples y variantes
    products = [item for item in items if item['type'] == 'product']
    variants = [item for item in items if item['type'] == 'variant']
    
    if products:
        print("\nPRODUCTOS SIMPLES:")
        print("-" * 80)
        for item in products:
            status = "[EN STOCK]" if item['is_in_stock'] else "[SIN STOCK]"
            print(f"SKU: {item['sku'] or 'N/A':<20} | Nombre: {item['name']:<30} | "
                  f"Stock: {item['stock']}/{item['threshold']} "
                  f"| {status}")
    
    if variants:
        print("\nVARIANTES:")
        print("-" * 80)
        # Agrupar por producto
        variants_by_product = {}
        for item in variants:
            product_key = item['product_sku'] or f"ID-{item['product_id']}"
            if product_key not in variants_by_product:
                variants_by_product[product_key] = {
                    'product_name': item['product_name'],
                    'variants': []
                }
            variants_by_product[product_key]['variants'].append(item)
        
        for product_key, data in variants_by_product.items():
            print(f"\n  Producto: {data['product_name']} (SKU: {product_key})")
            for variant in data['variants']:
                status = "[EN STOCK]" if variant['is_in_stock'] else "[SIN STOCK]"
                variant_label = f"{variant['variant_name']}"
                if variant.get('group_name'):
                    variant_label = f"{variant['group_name']} - {variant_label}"
                print(f"    - {variant_label:<30} | SKU: {variant['variant_sku'] or 'N/A':<20} | "
                      f"Stock: {variant['stock']}/{variant['threshold']} | {status}")
    
    print("\n" + "=" * 80)
    print(f"\nTotal: {len(products)} productos simples, {len(variants)} variantes con poco inventario")

if __name__ == "__main__":
    print_low_stock_report()

