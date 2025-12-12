# Inventory Management API

Sistema de gestión de inventario separado de la gestión de catálogo de productos.

---

## Resumen

El inventario (stock) de productos se gestiona de forma **separada** del catálogo:

- **Crear/Actualizar productos**: Solo información del catálogo (nombre, descripción, precio, imágenes, etc.)
- **Gestionar inventario**: Endpoints dedicados para actualizar stock

Cuando se crea un producto nuevo, **siempre** se crea con:
- `stock: 0`
- `is_in_stock: false`

Para poner el producto disponible, debes usar los endpoints de inventario.

---

## 🌟 Endpoints Unificados (Recomendados)

Estos endpoints manejan **productos simples y variantes** de forma uniforme en una sola lista plana.

### GET `/admin/inventory`

Obtiene una lista plana de todos los items de inventario.

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `search` | string (opcional) | Filtrar por nombre, SKU o marca |

**Response (200):**
```json
{
  "total_items": 5,
  "total_products": 2,
  "total_variants": 3,
  "items": [
    {
      "id": 123,
      "seller_sku": "PROD-001",
      "name": "Producto Simple",
      "stock": 50,
      "is_in_stock": true,
      "is_variant": false,
      "image_url": "https://..."
    },
    {
      "id": 456,
      "seller_sku": "TINTE-001-RUBIO",
      "name": "Rubio",
      "stock": 25,
      "is_in_stock": true,
      "is_variant": true,
      "parent_id": 200,
      "parent_sku": "TINTE-001",
      "parent_name": "Tinte Profesional",
      "variant_type": "Color",
      "group_name": "Naturales",
      "image_url": "https://..."
    },
    {
      "id": 457,
      "seller_sku": "TINTE-001-NEGRO",
      "name": "Negro",
      "stock": 30,
      "is_in_stock": true,
      "is_variant": true,
      "parent_id": 200,
      "parent_sku": "TINTE-001",
      "parent_name": "Tinte Profesional",
      "variant_type": "Color",
      "group_name": "Oscuros",
      "image_url": "https://..."
    }
  ]
}
```

**Notas:**
- Los productos con variantes **NO** aparecen como items - solo sus variantes
- Cada item tiene `is_variant` para saber si es variante o producto simple
- Las variantes incluyen `parent_sku` y `parent_name` para referencia

---

### PUT `/admin/inventory`

Actualiza el inventario de productos y variantes de forma unificada.

**Request Body:**
```json
{
  "items": [
    {"seller_sku": "PROD-001", "stock": 50},
    {"seller_sku": "TINTE-001-RUBIO", "stock": 25},
    {"seller_sku": "TINTE-001-NEGRO", "stock": 30, "is_in_stock": true}
  ]
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `items` | array | ✅ Sí | Lista de items a actualizar |
| `items[].seller_sku` | string | ✅ Sí | SKU del producto o variante |
| `items[].stock` | integer | ✅ Sí | Nueva cantidad en stock |
| `items[].is_in_stock` | boolean | ❌ No | Se calcula automáticamente si no se envía |

**Response (200):**
```json
{
  "updated": 3,
  "failed": 0,
  "errors": [],
  "results": [
    {
      "seller_sku": "PROD-001",
      "id": 123,
      "name": "Producto Simple",
      "stock": 50,
      "is_in_stock": true,
      "is_variant": false,
      "parent_sku": null,
      "message": "Updated"
    },
    {
      "seller_sku": "TINTE-001-RUBIO",
      "id": 456,
      "name": "Rubio",
      "stock": 25,
      "is_in_stock": true,
      "is_variant": true,
      "parent_sku": "TINTE-001",
      "message": "Updated"
    }
  ]
}
```

**Ejemplo cURL:**
```bash
curl -X PUT "https://api.example.com/admin/inventory" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"seller_sku": "PROD-001", "stock": 50},
      {"seller_sku": "TINTE-001-RUBIO", "stock": 25},
      {"seller_sku": "TINTE-001-NEGRO", "stock": 30}
    ]
  }'
```

**⚠️ Importante:**
- Para productos con variantes, **debes actualizar el SKU de cada variante** (no el del producto padre)
- Si envías el SKU de un producto con variantes, recibirás error:
  ```json
  {
    "seller_sku": "TINTE-001",
    "error": "This is a product with variants. Update the variant SKUs instead."
  }
  ```
- El stock del producto padre se **recalcula automáticamente** al actualizar sus variantes

---

## Endpoints Detallados (Alternativos)

Los siguientes endpoints están disponibles si necesitas actualizar items individualmente.

### Endpoints de Inventario

Todos los endpoints requieren autenticación OAuth con scope `products:write`.

### PUT `/admin/inventory/sku/{seller_sku}`

Actualiza el inventario de un producto por su SKU.

**Path Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `seller_sku` | string | SKU del producto |

**Request Body:**
```json
{
  "stock": 50,
  "is_in_stock": true
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `stock` | integer | ✅ Sí | Nueva cantidad en stock |
| `is_in_stock` | boolean | ❌ No | Si no se envía, se calcula automáticamente (`stock > 0`) |

**Response (200):**
```json
{
  "seller_sku": "TINTE-001",
  "product_id": 123,
  "stock": 50,
  "is_in_stock": true,
  "message": "Inventory updated successfully"
}
```

**Ejemplo cURL:**
```bash
curl -X PUT "https://api.example.com/admin/inventory/sku/TINTE-001" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"stock": 50}'
```

---

### PUT `/admin/inventory/product/{product_id}`

Actualiza el inventario de un producto por su ID.

**Path Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `product_id` | integer | ID del producto |

**Request Body:**
```json
{
  "stock": 25,
  "is_in_stock": true
}
```

**Response (200):**
```json
{
  "seller_sku": "TINTE-001",
  "product_id": 123,
  "stock": 25,
  "is_in_stock": true,
  "message": "Inventory updated successfully"
}
```

---

### PUT `/admin/inventory/bulk`

Actualiza el inventario de múltiples productos a la vez.

**Request Body:**
```json
{
  "products": [
    {
      "seller_sku": "TINTE-001",
      "stock": 50
    },
    {
      "seller_sku": "TINTE-002",
      "stock": 30,
      "is_in_stock": true
    },
    {
      "seller_sku": "SHAMPOO-001",
      "stock": 0,
      "is_in_stock": false
    }
  ]
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `products` | array | ✅ Sí | Lista de productos a actualizar |
| `products[].seller_sku` | string | ✅ Sí | SKU del producto |
| `products[].stock` | integer | ✅ Sí | Nueva cantidad en stock |
| `products[].is_in_stock` | boolean | ❌ No | Si no se envía, se calcula automáticamente |

**Response (200):**
```json
{
  "updated": 2,
  "failed": 1,
  "errors": [
    {
      "seller_sku": "SHAMPOO-001",
      "error": "Product not found"
    }
  ],
  "results": [
    {
      "seller_sku": "TINTE-001",
      "product_id": 123,
      "stock": 50,
      "is_in_stock": true,
      "message": "Updated"
    },
    {
      "seller_sku": "TINTE-002",
      "product_id": 124,
      "stock": 30,
      "is_in_stock": true,
      "message": "Updated"
    }
  ]
}
```

**Ejemplo cURL:**
```bash
curl -X PUT "https://api.example.com/admin/inventory/bulk" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"seller_sku": "TINTE-001", "stock": 50},
      {"seller_sku": "TINTE-002", "stock": 30}
    ]
  }'
```

---

## Flujo de Trabajo Recomendado

### 1. Publicar un nuevo producto

```bash
# Paso 1: Crear el producto (se crea con stock=0, is_in_stock=false)
POST /admin/products
{
  "seller_sku": "NUEVO-001",
  "name": "Nuevo Producto",
  "regular_price": 29.99,
  ...
}

# Paso 2: Configurar el inventario inicial
PUT /admin/inventory/sku/NUEVO-001
{
  "stock": 100
}
```

### 2. Actualización masiva de inventario (desde otro sistema)

```bash
# Sincronizar inventario desde el sistema principal
PUT /admin/inventory/bulk
{
  "products": [
    {"seller_sku": "SKU-001", "stock": 45},
    {"seller_sku": "SKU-002", "stock": 0},
    {"seller_sku": "SKU-003", "stock": 120},
    ...
  ]
}
```

### 3. Marcar producto como agotado

```bash
PUT /admin/inventory/sku/PRODUCTO-001
{
  "stock": 0,
  "is_in_stock": false
}
```

### 4. Producto con preventa (stock 0 pero disponible)

```bash
# Producto disponible para preventa aunque no haya stock físico
PUT /admin/inventory/sku/PREVENTA-001
{
  "stock": 0,
  "is_in_stock": true
}
```

---

## Comportamiento de `is_in_stock`

| `stock` | `is_in_stock` enviado | Resultado |
|---------|----------------------|-----------|
| 50 | (no enviado) | `is_in_stock: true` |
| 0 | (no enviado) | `is_in_stock: false` |
| 50 | `false` | `is_in_stock: false` (forzado, ej: producto discontinuado) |
| 0 | `true` | `is_in_stock: true` (preventa/backorder) |

---

---

## Endpoints de Inventario de Variantes

Para productos con variantes (colores, tamaños, etc.), cada variante tiene su propio stock independiente.

### PUT `/admin/inventory/variant/sku/{seller_sku}`

Actualiza el inventario de una variante por su SKU.

**Path Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `seller_sku` | string | SKU de la variante |

**Request Body:**
```json
{
  "stock": 25,
  "is_in_stock": true
}
```

**Response (200):**
```json
{
  "variant_id": 456,
  "seller_sku": "TINTE-001-RUBIO",
  "variant_name": "Rubio",
  "product_id": 123,
  "product_name": "Tinte Profesional",
  "stock": 25,
  "is_in_stock": true,
  "message": "Variant inventory updated successfully"
}
```

---

### PUT `/admin/inventory/variant/{variant_id}`

Actualiza el inventario de una variante por su ID.

**Path Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `variant_id` | integer | ID de la variante |

**Request Body:**
```json
{
  "stock": 15
}
```

**Response (200):**
```json
{
  "variant_id": 456,
  "seller_sku": "TINTE-001-RUBIO",
  "variant_name": "Rubio",
  "product_id": 123,
  "product_name": "Tinte Profesional",
  "stock": 15,
  "is_in_stock": true,
  "message": "Variant inventory updated successfully"
}
```

---

### PUT `/admin/inventory/variants/bulk`

Actualiza el inventario de múltiples variantes a la vez.

**Request Body:**
```json
{
  "variants": [
    {
      "seller_sku": "TINTE-001-RUBIO",
      "stock": 25
    },
    {
      "seller_sku": "TINTE-001-NEGRO",
      "stock": 30
    },
    {
      "seller_sku": "TINTE-001-CASTANO",
      "stock": 0,
      "is_in_stock": false
    }
  ]
}
```

**Response (200):**
```json
{
  "updated": 3,
  "failed": 0,
  "errors": [],
  "results": [
    {
      "variant_id": 456,
      "seller_sku": "TINTE-001-RUBIO",
      "variant_name": "Rubio",
      "product_id": 123,
      "product_name": "Tinte Profesional",
      "stock": 25,
      "is_in_stock": true,
      "message": "Updated"
    },
    {
      "variant_id": 457,
      "seller_sku": "TINTE-001-NEGRO",
      "variant_name": "Negro",
      "product_id": 123,
      "product_name": "Tinte Profesional",
      "stock": 30,
      "is_in_stock": true,
      "message": "Updated"
    },
    {
      "variant_id": 458,
      "seller_sku": "TINTE-001-CASTANO",
      "variant_name": "Castaño",
      "product_id": 123,
      "product_name": "Tinte Profesional",
      "stock": 0,
      "is_in_stock": false,
      "message": "Updated"
    }
  ]
}
```

---

## Producto Simple vs Producto con Variantes

| Tipo de Producto | Endpoints a usar | Stock del producto |
|-----------------|------------------|-------------------|
| **Simple** (sin variantes) | `/admin/inventory/sku/{sku}` o `/admin/inventory/bulk` | Se actualiza directamente |
| **Con variantes** | `/admin/inventory/variant/sku/{sku}` o `/admin/inventory/variants/bulk` | **Calculado automáticamente** |

### ⚠️ Importante: Stock de Productos con Variantes

Para productos con variantes:
- El **stock del producto** = **suma del stock de todas sus variantes**
- El **is_in_stock del producto** = `true` si **al menos una variante** tiene stock
- El stock se **recalcula automáticamente** cada vez que se actualiza una variante

**NO puedes** actualizar directamente el stock de un producto que tiene variantes. Si lo intentas, recibirás un error **con la lista de variantes y su inventario actual**:

```json
{
  "detail": {
    "error": "Product has variants",
    "message": "Product 'TINTE-001' has variants. Use /admin/inventory/variants/bulk to update variant stock. Product stock is automatically calculated as the sum of all variant stocks.",
    "product_id": 123,
    "product_name": "Tinte Profesional",
    "product_stock": 55,
    "product_is_in_stock": true,
    "variants": [
      {
        "variant_id": 456,
        "seller_sku": "TINTE-001-RUBIO",
        "name": "Rubio",
        "group_name": "Color",
        "stock": 25,
        "is_in_stock": true
      },
      {
        "variant_id": 457,
        "seller_sku": "TINTE-001-NEGRO",
        "name": "Negro",
        "group_name": "Color",
        "stock": 30,
        "is_in_stock": true
      },
      {
        "variant_id": 458,
        "seller_sku": "TINTE-001-CASTANO",
        "name": "Castaño",
        "group_name": "Color",
        "stock": 0,
        "is_in_stock": false
      }
    ],
    "hint": "Update the variants listed above using /admin/inventory/variants/bulk"
  }
}
```

Esto te permite ver qué variantes tiene el producto y sus SKUs para actualizarlas correctamente.

### Ejemplo: Stock calculado automáticamente

Si actualizas las variantes:
```bash
PUT /admin/inventory/variants/bulk
{
  "variants": [
    {"seller_sku": "TINTE-001-RUBIO", "stock": 25},
    {"seller_sku": "TINTE-001-NEGRO", "stock": 30},
    {"seller_sku": "TINTE-001-CASTANO", "stock": 0}
  ]
}
```

El producto padre automáticamente tendrá:
- `stock: 55` (25 + 30 + 0)
- `is_in_stock: true` (porque Rubio y Negro tienen stock)

### ¿Cómo saber si un producto tiene variantes?

En la respuesta de productos, el campo `has_variants` indica si tiene variantes:

```json
{
  "id": 123,
  "name": "Tinte Profesional",
  "has_variants": true,
  "stock": 55,
  "is_in_stock": true,
  "variant_types": [
    {
      "type": "Color",
      "variants": [
        {"id": 456, "seller_sku": "TINTE-001-RUBIO", "name": "Rubio", "stock": 25},
        {"id": 457, "seller_sku": "TINTE-001-NEGRO", "name": "Negro", "stock": 30},
        {"id": 458, "seller_sku": "TINTE-001-CASTANO", "name": "Castaño", "stock": 0}
      ]
    }
  ]
}
```

---

## Notas Importantes

1. **Productos nuevos**: Siempre se crean con `stock=0` e `is_in_stock=false`
2. **Actualización de catálogo**: Los endpoints `PUT /admin/products/{id}` y `PUT /admin/products/bulk` **NO** permiten modificar stock
3. **SKU requerido para bulk**: El update masivo usa `seller_sku` como identificador
4. **Productos simples**: Usar endpoints `/admin/inventory/...`
5. **Productos con variantes**: Usar endpoints `/admin/inventory/variant/...` o `/admin/inventory/variants/bulk`
6. **Stock calculado**: El stock de un producto con variantes es la **suma automática** del stock de sus variantes
7. **No editar stock de productos con variantes**: Recibirás error 400 si intentas usar `/admin/inventory/sku/{sku}` en un producto con variantes

---

## Errores Comunes

| Código | Error | Causa |
|--------|-------|-------|
| 400 | "Product has variants. Use /admin/inventory/variants/bulk..." | Intentaste actualizar stock de un producto con variantes directamente |
| 404 | "Product with SKU 'XXX' not found" | El SKU de producto no existe |
| 404 | "Product with ID X not found" | El ID de producto no existe |
| 404 | "Variant with SKU 'XXX' not found" | El SKU de variante no existe |
| 404 | "Variant with ID X not found" | El ID de variante no existe |
| 401 | "Invalid or expired token" | Token OAuth inválido |
| 403 | "Insufficient scope" | Token no tiene scope `products:write` |

---

## Scopes Requeridos

| Endpoint | Scope |
|----------|-------|
| `GET /admin/inventory` | `products:read` |
| `PUT /admin/inventory` | `products:write` |
| `PUT /admin/inventory/sku/{sku}` | `products:write` |
| `PUT /admin/inventory/product/{id}` | `products:write` |
| `PUT /admin/inventory/bulk` | `products:write` |
| `PUT /admin/inventory/variant/sku/{sku}` | `products:write` |
| `PUT /admin/inventory/variant/{id}` | `products:write` |
| `PUT /admin/inventory/variants/bulk` | `products:write` |

