# API de Productos - Documentación para Dashboard

## Localización (i18n)

La API soporta **español (es)** e **inglés (en)** para los campos de texto.

### Para endpoints públicos (`/products`)
Envía el header `Accept-Language`:
```
Accept-Language: en  → Respuesta en inglés
Accept-Language: es  → Respuesta en español (default)
```

### Para endpoints admin (`/admin/products`)
Devuelve **todos los campos** en ambos idiomas para que el dashboard pueda editarlos.

---

## Autenticación

Todos los endpoints requieren un token Bearer obtenido via OAuth2:

```
Authorization: Bearer <access_token>
```

### Obtener Token

```http
POST /oauth/token
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "client_id": "app_landa_admin",
  "client_secret": "sk_live_..."
}
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 7200,
  "scope": "products:read products:write ..."
}
```

---

## Scopes Requeridos

| Acción | Scope |
|--------|-------|
| Listar/Obtener productos | `products:read` |
| Crear/Actualizar/Eliminar productos | `products:write` |

---

## Endpoints

### 1. Listar Productos

```http
GET /admin/products
Authorization: Bearer <token>
```

**Query params opcionales:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `search` | string | Buscar por nombre o marca |
| `brand` | string | Filtrar por marca exacta |
| `is_in_stock` | boolean | Filtrar por disponibilidad |

**Ejemplos:**
```
GET /admin/products
GET /admin/products?search=shampoo
GET /admin/products?brand=L'Oreal&is_in_stock=true
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "seller_sku": "SHMP-001",
    "name": "Shampoo Profesional",
    "name_en": "Professional Shampoo",
    "short_description": "Para cabello seco",
    "short_description_en": "For dry hair",
    "description": "Descripción larga...",
    "description_en": "Long description...",
    "tags": "shampoo;cabello;profesional",
    "tags_en": "shampoo;hair;professional",
    "regular_price": 29.99,
    "sale_price": 24.99,
    "stock": 100,
    "is_in_stock": true,
    "restock_date": null,
    "is_favorite": false,
    "notify_when_available": false,
    "image_url": "https://example.com/image.jpg",
    "currency": "USD",
    "low_stock_threshold": 5,
    "has_variants": false,
    "brand": "L'Oreal",
    "created_at": "2025-12-01T10:00:00",
    "updated_at": "2025-12-08T15:30:00",
    "variant_groups": []
  }
]
```

---

### 2. Obtener Producto por ID

```http
GET /admin/products/{product_id}
Authorization: Bearer <token>
```

**Ejemplo:**
```
GET /admin/products/1
```

**Respuesta:** (mismo formato que listar, un solo objeto)

---

### 3. Crear Producto (sin variantes)

```http
POST /admin/products
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "seller_sku": "SHMP-001",
  "name": "Shampoo Profesional",
  "name_en": "Professional Shampoo",
  "short_description": "Para cabello seco",
  "short_description_en": "For dry hair",
  "description": "Descripción larga del producto...",
  "description_en": "Long product description...",
  "tags": "shampoo;cabello;profesional",
  "tags_en": "shampoo;hair;professional",
  "regular_price": 29.99,
  "sale_price": 24.99,
  "stock": 100,
  "is_in_stock": true,
  "restock_date": null,
  "is_favorite": false,
  "notify_when_available": false,
  "image_url": "https://example.com/image.jpg",
  "currency": "USD",
  "low_stock_threshold": 5,
  "has_variants": false,
  "brand": "L'Oreal"
}
```

**Campos:**

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `seller_sku` | string | No | null | SKU único para enlazar con dashboard |
| **Nombres** |
| `name` | string | **Sí** | - | Nombre/título del producto (español) |
| `name_en` | string | No | null | Nombre/título del producto (inglés) |
| **Descripciones** |
| `short_description` | string | No | null | Descripción corta (español) |
| `short_description_en` | string | No | null | Descripción corta (inglés) |
| `description` | string | No | null | Descripción larga (español) |
| `description_en` | string | No | null | Descripción larga (inglés) |
| **Tags** |
| `tags` | string | No | null | Tags separados por `;` (español) |
| `tags_en` | string | No | null | Tags separados por `;` (inglés) |
| **Precios e Inventario** |
| `regular_price` | float | **Sí** | - | Precio regular |
| `sale_price` | float | No | null | Precio de oferta |
| `stock` | int | No | 0 | Cantidad en inventario |
| `is_in_stock` | bool | No | true | Disponibilidad |
| `restock_date` | date | No | null | Fecha reabastecimiento (YYYY-MM-DD) |
| `low_stock_threshold` | int | No | 5 | Umbral de stock bajo |
| **Display** |
| `is_favorite` | bool | No | false | Marcar como favorito |
| `notify_when_available` | bool | No | false | Notificar disponibilidad |
| `image_url` | string | No | null | URL de imagen principal |
| `gallery` | array | No | [] | Array de URLs de imágenes adicionales |
| `currency` | string | No | "USD" | Moneda |
| `has_variants` | bool | No | false | Tiene variantes |
| `brand` | string | No | null | Marca |

---

### 4. Crear Producto con Variantes

La estructura de variantes soporta **3 niveles**:
1. **Tipo de Variante** (`variant_type`): "Color", "Tamaño", "Volumen" - REQUERIDO
2. **Categoría** (`name`): "Naturales", "Fantasías" - OPCIONAL (null = variantes simples)
3. **Variantes**: Los valores específicos

```http
POST /admin/products
Authorization: Bearer <token>
Content-Type: application/json
```

**Ejemplo 1: Variantes CON categorías (tintes con grupos)**
```json
{
  "seller_sku": "TINTE-LOREAL-001",
  "name": "Tinte L'Oreal Profesional",
  "regular_price": 25.99,
  "brand": "L'Oreal",
  "has_variants": true,
  "variant_groups": [
    {
      "variant_type": "Color",
      "name": "Naturales",
      "display_order": 0,
      "variants": [
        {
          "seller_sku": "TINTE-NAT-RUBIO",
          "name": "Rubio",
          "variant_value": "Rubio",
          "stock": 50,
          "regular_price": 25.99,
          "image_url": "https://example.com/rubio.jpg"
        },
        {
          "seller_sku": "TINTE-NAT-CASTANO",
          "name": "Castaño",
          "stock": 30
        }
      ]
    },
    {
      "variant_type": "Color",
      "name": "Fantasías",
      "display_order": 1,
      "variants": [
        {
          "seller_sku": "TINTE-FAN-AZUL",
          "name": "Azul",
          "stock": 20,
          "regular_price": 29.99
        },
        {
          "seller_sku": "TINTE-FAN-ROSA",
          "name": "Rosa",
          "stock": 15
        }
      ]
    }
  ]
}
```

**Ejemplo 2: Variantes SIMPLES sin categorías (peróxido)**
```json
{
  "seller_sku": "PEROXIDO-001",
  "name": "Peróxido Profesional",
  "regular_price": 6.99,
  "has_variants": true,
  "variant_groups": [
    {
      "variant_type": "Volumen",
      "name": null,
      "display_order": 0,
      "variants": [
        {"seller_sku": "PER-V10", "name": "Vol 10", "stock": 100},
        {"seller_sku": "PER-V20", "name": "Vol 20", "stock": 80},
        {"seller_sku": "PER-V30", "name": "Vol 30", "stock": 60}
      ]
    }
  ]
}
```

**Ejemplo 3: Producto con MÚLTIPLES tipos de variantes**
```json
{
  "seller_sku": "TINTE-MULTI-001",
  "name": "Tinte con colores y peróxidos",
  "regular_price": 4.95,
  "has_variants": true,
  "variant_groups": [
    {
      "variant_type": "Peroxido",
      "name": null,
      "variants": [
        {"seller_sku": "906", "name": "Vol 10", "stock": 100},
        {"seller_sku": "907", "name": "Vol 20", "stock": 100},
        {"seller_sku": "908", "name": "Vol 30", "stock": 100}
      ]
    },
    {
      "variant_type": "Color",
      "name": "Colores Naturales",
      "variants": [
        {"seller_sku": "902", "name": "Negro", "stock": 100},
        {"seller_sku": "903", "name": "Azul", "stock": 100}
      ]
    },
    {
      "variant_type": "Color",
      "name": "Fantasia",
      "variants": [
        {"seller_sku": "904", "name": "Rojo", "stock": 100},
        {"seller_sku": "905", "name": "Amarillo Neon", "stock": 100}
      ]
    }
  ]
}
```

**Estructura de variant_groups:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `variant_type` | string | **Sí** | Tipo de variante: "Color", "Tamaño", "Volumen", etc. |
| `name` | string | No | Categoría: "Naturales", "Fantasías" (`null` = variantes simples) |
| `display_order` | int | No | Orden de visualización (0, 1, 2...) |
| `variants` | array | **Sí** | Lista de variantes |

**Estructura de variants:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `seller_sku` | string | No | SKU único de la variante |
| `name` | string | **Sí** | Nombre para mostrar (ej: "Rubio") |
| `variant_value` | string | No | Valor limpio para filtros (default: `name`) |
| `barcode` | string | No | Código de barras/UPC |
| `attributes` | object | No | Atributos adicionales `{}` |
| `regular_price` | float | No | Precio (si es diferente al padre) |
| `sale_price` | float | No | Precio de oferta |
| `stock` | int | No | Inventario de esta variante |
| `is_in_stock` | bool | No | Disponibilidad (default: true) |
| `image_url` | string | No | Imagen específica de variante |
| `display_order` | int | No | Orden de visualización |
| `active` | bool | No | Activo (default: true, false = oculto) |

> **Notas:**
> - Si `variant_value` no se envía, se usa el valor de `name`
> - Si `regular_price` de la variante es `null`, se usa el precio del producto padre
> - Variantes con `active: false` no aparecen en el frontend público

---

### 5. Actualizar Producto

```http
PUT /admin/products/{product_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (solo campos a actualizar):**
```json
{
  "regular_price": 34.99,
  "sale_price": 29.99,
  "stock": 50,
  "is_in_stock": true
}
```

**Ejemplo actualizando traducciones:**
```json
{
  "name_en": "Professional Shampoo Updated",
  "description_en": "New English description...",
  "tags_en": "shampoo;hair;dry"
}
```

**Ejemplo actualizando/reemplazando variantes:**
```json
{
  "variant_groups": [
    {
      "variant_type": "Color",
      "name": "Naturales",
      "variants": [
        {"name": "Rubio", "seller_sku": "TINTE-RUB", "stock": 100},
        {"name": "Castaño", "seller_sku": "TINTE-CAS", "stock": 50},
        {"name": "Negro", "seller_sku": "TINTE-NEG", "stock": 30}
      ]
    },
    {
      "variant_type": "Color",
      "name": "Fantasías",
      "variants": [
        {"name": "Azul", "seller_sku": "TINTE-AZU", "stock": 20}
      ]
    }
  ]
}
```

> **Comportamiento de variantes:**
> - Si envías `variant_groups` → **Reemplaza TODAS** las variantes existentes
> - Si NO envías `variant_groups` → No toca las variantes
> - Si envías `variant_groups: []` → **Elimina todas** las variantes

---

### 6. Crear Múltiples Productos (Bulk)

```http
POST /admin/products/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "products": [
    {
      "seller_sku": "PROD-001",
      "name": "Producto 1",
      "regular_price": 29.99,
      "stock": 100,
      "brand": "Marca A"
    },
    {
      "seller_sku": "PROD-002",
      "name": "Producto 2",
      "regular_price": 19.99,
      "stock": 50,
      "brand": "Marca B"
    },
    {
      "seller_sku": "PROD-003",
      "name": "Producto 3 con variantes",
      "regular_price": 25.99,
      "has_variants": true,
      "variant_groups": [
        {
          "name": "Colores",
          "variants": [
            {"name": "Rojo", "seller_sku": "PROD-003-RED", "stock": 20},
            {"name": "Azul", "seller_sku": "PROD-003-BLUE", "stock": 15}
          ]
        }
      ]
    }
  ]
}
```

**Respuesta:**
```json
{
  "created": 2,
  "failed": 1,
  "errors": [
    {
      "index": 1,
      "seller_sku": "PROD-002",
      "error": "SKU already exists"
    }
  ],
  "products": [
    {
      "id": 1,
      "seller_sku": "PROD-001",
      "name": "Producto 1",
      ...
    },
    {
      "id": 3,
      "seller_sku": "PROD-003",
      "name": "Producto 3 con variantes",
      "has_variants": true,
      "variant_groups": [...]
    }
  ]
}
```

> **Nota:** Los productos que fallan no detienen la operación. Se continúa con los demás y se reportan los errores al final.

---

### 7. Actualizar Múltiples Productos (Bulk Update)

Ideal para sincronizar inventario y precios desde el dashboard.

```http
PUT /admin/products/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "products": [
    {
      "id": 1,
      "stock": 100,
      "regular_price": 29.99
    },
    {
      "id": 2,
      "stock": 50,
      "sale_price": 19.99,
      "is_in_stock": true
    },
    {
      "id": 3,
      "is_in_stock": false
    },
    {
      "id": 4,
      "regular_price": 39.99,
      "stock": 75,
      "low_stock_threshold": 10
    }
  ]
}
```

**Campos actualizables en bulk:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | **Requerido.** ID del producto a actualizar |
| `seller_sku` | string | SKU del producto |
| **Nombres** |
| `name` | string | Nombre del producto (español) |
| `name_en` | string | Nombre del producto (inglés) |
| **Descripciones** |
| `short_description` | string | Descripción corta (español) |
| `short_description_en` | string | Descripción corta (inglés) |
| `description` | string | Descripción completa (español) |
| `description_en` | string | Descripción completa (inglés) |
| **Tags** |
| `tags` | string | Tags separados por `;` (español) |
| `tags_en` | string | Tags separados por `;` (inglés) |
| **Precios e Inventario** |
| `regular_price` | float | Precio regular |
| `sale_price` | float | Precio de oferta |
| `stock` | int | Cantidad en inventario |
| `is_in_stock` | bool | Disponibilidad |
| `low_stock_threshold` | int | Umbral de stock bajo |
| `image_url` | string | URL de imagen principal |
| `gallery` | array | Array de URLs de imágenes adicionales |
| `brand` | string | Marca |
| `variant_groups` | array | Reemplaza variantes (ver estructura abajo) |

**Respuesta:**
```json
{
  "updated": 3,
  "failed": 1,
  "errors": [
    {
      "id": 3,
      "seller_sku": null,
      "error": "Product not found"
    }
  ],
  "products": [
    {
      "id": 1,
      "name": "Producto 1",
      "stock": 100,
      "regular_price": 29.99,
      "updated_at": "2025-12-08T15:30:00",
      ...
    },
    ...
  ]
}
```

---

### 8. Eliminar Múltiples Productos (Bulk Delete)

```http
DELETE /admin/products/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "product_ids": [1, 2, 3, 5, 8]
}
```

**Respuesta:**
```json
{
  "deleted": 4,
  "failed": 1,
  "errors": [
    {
      "id": 5,
      "error": "Product not found"
    }
  ]
}
```

> **Nota:** Eliminar productos también elimina sus grupos de variantes y variantes asociadas.

---

### 9. Eliminar Producto

```http
DELETE /admin/products/{product_id}
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "msg": "Product 'Shampoo Profesional' deleted successfully"
}
```

> **Nota:** Eliminar un producto también elimina todos sus grupos de variantes y variantes asociadas.

---

## Respuesta de Producto con Variantes (Admin y Frontend)

La respuesta agrupa las variantes por `variant_type`. Cada tipo puede tener:
- **`categories`**: Lista de categorías con variantes (cuando hay subcategorías)
- **`variants`**: Lista directa de variantes (cuando es simple, sin categorías)

```json
{
  "id": 266,
  "seller_sku": "901",
  "name": "Tintes prueba con varios tipos de variantes",
  "name_en": "Dyes test with multiple variant types",
  "regular_price": 4.95,
  "has_variants": true,
  "brand": "SARAH K",
  "created_at": "2025-12-08T08:55:25.345884",
  "updated_at": "2025-12-08T09:32:50.793527",
  "variant_types": [
    {
      "type": "Color",
      "categories": [
        {
          "id": 3,
          "name": "Colores Naturales",
          "display_order": 0,
          "variants": [
            {
              "id": 5,
              "group_id": 3,
              "seller_sku": "902",
              "name": "Negro",
              "variant_value": "Negro",
              "barcode": null,
              "regular_price": 4.95,
              "stock": 100,
              "is_in_stock": true,
              "active": true
            },
            {
              "id": 6,
              "group_id": 3,
              "seller_sku": "903",
              "name": "Azul",
              "variant_value": "Azul",
              "regular_price": 4.95,
              "stock": 100,
              "active": true
            }
          ]
        },
        {
          "id": 4,
          "name": "Fantasia",
          "display_order": 0,
          "variants": [
            {
              "id": 7,
              "group_id": 4,
              "seller_sku": "904",
              "name": "Rojo",
              "variant_value": "Rojo",
              "stock": 100,
              "active": true
            },
            {
              "id": 8,
              "group_id": 4,
              "seller_sku": "905",
              "name": "Amarillo Neon",
              "variant_value": "Amarillo Neon",
              "stock": 100,
              "active": true
            }
          ]
        }
      ],
      "variants": null
    },
    {
      "type": "Peroxido",
      "categories": null,
      "variants": [
        {
          "id": 9,
          "group_id": 5,
          "seller_sku": "906",
          "name": "Vol 10",
          "variant_value": "Vol 10",
          "regular_price": 4.95,
          "stock": 100,
          "active": true
        },
        {
          "id": 10,
          "group_id": 5,
          "seller_sku": "907",
          "name": "Vol 20",
          "variant_value": "Vol 20",
          "stock": 100,
          "active": true
        },
        {
          "id": 11,
          "group_id": 5,
          "seller_sku": "908",
          "name": "Vol 30",
          "variant_value": "Vol 30",
          "stock": 100,
          "active": true
        }
      ]
    }
  ]
}
```

### Lógica de la estructura

| Situación | `categories` | `variants` |
|-----------|--------------|------------|
| Con subcategorías (Color → Naturales, Fantasía) | `[{name, variants}]` | `null` |
| Sin subcategorías (Peroxido → Vol 10, 20, 30) | `null` | `[{variant}]` |

---

## Para Frontend Next.js - Procesando Variantes

### Respuesta del Frontend (con Accept-Language: es)

El frontend público recibe solo variantes **activas** con la misma estructura `variant_types`:

```json
{
  "id": 266,
  "name": "Tinte con colores y peróxidos",
  "has_variants": true,
  "variant_types": [
    {
      "type": "Color",
      "categories": [
        {
          "id": 3,
          "name": "Colores Naturales",
          "variants": [
            {"id": 5, "name": "Negro", "variant_value": "Negro", "stock": 100},
            {"id": 6, "name": "Azul", "variant_value": "Azul", "stock": 100}
          ]
        },
        {
          "id": 4,
          "name": "Fantasia",
          "variants": [
            {"id": 7, "name": "Rojo", "variant_value": "Rojo", "stock": 100},
            {"id": 8, "name": "Amarillo Neon", "variant_value": "Amarillo Neon", "stock": 100}
          ]
        }
      ],
      "variants": null
    },
    {
      "type": "Peroxido",
      "categories": null,
      "variants": [
        {"id": 9, "name": "Vol 10", "variant_value": "Vol 10", "stock": 100},
        {"id": 10, "name": "Vol 20", "variant_value": "Vol 20", "stock": 100},
        {"id": 11, "name": "Vol 30", "variant_value": "Vol 30", "stock": 100}
      ]
    }
  ]
}
```

### Código React/Next.js para renderizar variantes

La API ya devuelve los datos agrupados, solo necesitas renderizar:

```typescript
interface Variant {
  id: number;
  name: string;
  variant_value: string | null;
  regular_price: number | null;
  stock: number | null;
  is_in_stock: boolean | null;
  image_url: string | null;
}

interface VariantCategory {
  id: number;
  name: string;
  variants: Variant[];
}

interface VariantType {
  type: string;                          // "Color", "Peroxido"
  categories: VariantCategory[] | null;  // null = variantes simples
  variants: Variant[] | null;            // Solo cuando categories es null
}

interface Product {
  // ... otros campos
  variant_types: VariantType[];
}

// Componente para renderizar variantes
function ProductVariants({ product }: { product: Product }) {
  return (
    <div>
      {product.variant_types.map((vt) => (
        <div key={vt.type} className="variant-type-section">
          <h3>{vt.type}</h3>

          {vt.categories ? (
            // CON categorías (ej: Color → Naturales, Fantasías)
            vt.categories.map((category) => (
              <div key={category.id} className="variant-category">
                <h4>{category.name}</h4>
                <div className="variants-grid">
                  {category.variants.map((variant) => (
                    <VariantButton key={variant.id} variant={variant} />
                  ))}
                </div>
              </div>
            ))
          ) : (
            // SIN categorías (ej: Peroxido → Vol 10, Vol 20, Vol 30)
            <div className="variants-grid">
              {vt.variants?.map((variant) => (
                <VariantButton key={variant.id} variant={variant} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### Resultado visual esperado

```
📦 Variantes del Producto

🔹 Peroxido (variantes simples)
   [Vol 10] [Vol 20] [Vol 30]

🎨 Color (por categoría)
   📁 Colores Naturales
      [Negro] [Azul]
   📁 Fantasia
      [Rojo] [Amarillo Neon]
```

---

## Errores Comunes

| Código | Mensaje | Descripción |
|--------|---------|-------------|
| 400 | UNIQUE constraint failed | SKU duplicado |
| 401 | Invalid or expired token | Token inválido o expirado |
| 403 | Insufficient scope | Falta el scope requerido |
| 404 | Product not found | Producto no encontrado |

---

## Ejemplo Completo con cURL

### Crear producto simple:
```bash
curl -X POST "http://127.0.0.1:8000/admin/products" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_sku": "SHMP-001",
    "name": "Shampoo Profesional",
    "regular_price": 29.99,
    "stock": 100,
    "brand": "L'\''Oreal"
  }'
```

### Crear producto con variantes simples:
```bash
curl -X POST "http://127.0.0.1:8000/admin/products" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_sku": "PEROXIDO-001",
    "name": "Peróxido Profesional",
    "regular_price": 6.99,
    "has_variants": true,
    "variant_groups": [
      {
        "variant_type": "Volumen",
        "name": null,
        "variants": [
          {"name": "Vol 10", "seller_sku": "PER-V10", "stock": 100},
          {"name": "Vol 20", "seller_sku": "PER-V20", "stock": 80},
          {"name": "Vol 30", "seller_sku": "PER-V30", "stock": 60}
        ]
      }
    ]
  }'
```

### Crear producto con variantes y categorías:
```bash
curl -X POST "http://127.0.0.1:8000/admin/products" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_sku": "TINTE-001",
    "name": "Tinte Profesional",
    "regular_price": 25.99,
    "has_variants": true,
    "variant_groups": [
      {
        "variant_type": "Color",
        "name": "Naturales",
        "variants": [
          {"name": "Rubio", "seller_sku": "TINTE-RUB", "stock": 50},
          {"name": "Castaño", "seller_sku": "TINTE-CAS", "stock": 30}
        ]
      },
      {
        "variant_type": "Color",
        "name": "Fantasías",
        "variants": [
          {"name": "Azul", "seller_sku": "TINTE-AZU", "stock": 20}
        ]
      }
    ]
  }'
```

### Listar productos:
```bash
curl -X GET "http://127.0.0.1:8000/admin/products" \
  -H "Authorization: Bearer <token>"
```

### Actualizar producto:
```bash
curl -X PUT "http://127.0.0.1:8000/admin/products/1" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"regular_price": 34.99, "stock": 75}'
```

### Crear múltiples productos (bulk):
```bash
curl -X POST "http://127.0.0.1:8000/admin/products/bulk" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"seller_sku": "PROD-001", "name": "Producto 1", "regular_price": 29.99},
      {"seller_sku": "PROD-002", "name": "Producto 2", "regular_price": 19.99},
      {"seller_sku": "PROD-003", "name": "Producto 3", "regular_price": 39.99}
    ]
  }'
```

### Actualizar múltiples productos (bulk update):
```bash
curl -X PUT "http://127.0.0.1:8000/admin/products/bulk" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {"id": 1, "stock": 100, "regular_price": 29.99},
      {"id": 2, "stock": 50, "is_in_stock": true},
      {"id": 3, "sale_price": 19.99}
    ]
  }'
```

### Eliminar múltiples productos (bulk delete):
```bash
curl -X DELETE "http://127.0.0.1:8000/admin/products/bulk" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"product_ids": [1, 2, 3, 5, 8]}'
```

### Eliminar producto:
```bash
curl -X DELETE "http://127.0.0.1:8000/admin/products/1" \
  -H "Authorization: Bearer <token>"
```

---

## Campos de Localización (i18n)

### Campos con soporte multiidioma

| Campo Base | Español | Inglés | Descripción |
|------------|---------|--------|-------------|
| Nombre | `name` | `name_en` | Nombre/título del producto |
| Desc. corta | `short_description` | `short_description_en` | Descripción corta |
| Descripción | `description` | `description_en` | Descripción completa |
| Tags | `tags` | `tags_en` | Etiquetas para búsqueda (separadas por `;`) |

### Comportamiento

1. **Endpoints Admin** (`/admin/products`): Devuelven **todos** los campos en ambos idiomas
2. **Endpoints Públicos** (`/products`): Devuelven campos según `Accept-Language` header
3. **Fallback**: Si no hay traducción en inglés, se usa el español

### Ejemplo de sincronización con Dashboard

```python
# Desde Django, enviar producto con traducciones
payload = {
    "seller_sku": "PROD-001",
    "name": "Shampoo Profesional",
    "name_en": "Professional Shampoo",
    "description": "Descripción en español...",
    "description_en": "English description...",
    "tags": "shampoo;cabello;seco",
    "tags_en": "shampoo;hair;dry",
    "regular_price": 29.99
}

response = requests.post(
    "http://api/admin/products",
    json=payload,
    headers={"Authorization": f"Bearer {token}"}
)
```

---

## Gestión Individual de Variantes

Estos endpoints permiten agregar, actualizar o eliminar variantes sin reemplazar todas las existentes.

### 1. Agregar grupo de variantes a un producto

```http
POST /admin/products/{product_id}/variant-groups
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "name": "Nuevo Color",
  "display_order": 2,
  "variants": [
    {"name": "Morado", "seller_sku": "TINTE-MOR", "stock": 25},
    {"name": "Verde", "seller_sku": "TINTE-VER", "stock": 30}
  ]
}
```

---

### 2. Agregar variante a un grupo existente

```http
POST /admin/variant-groups/{group_id}/variants
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "name": "Platino",
  "seller_sku": "TINTE-PLA",
  "stock": 40,
  "regular_price": 32.99
}
```

---

### 3. Actualizar una variante

```http
PUT /admin/variants/{variant_id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Body (solo campos a actualizar):**
```json
{
  "stock": 100,
  "regular_price": 29.99,
  "is_in_stock": true
}
```

---

### 4. Eliminar una variante

```http
DELETE /admin/variants/{variant_id}
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "msg": "Variant 'Rubio' deleted successfully"
}
```

---

### 5. Eliminar un grupo completo

```http
DELETE /admin/variant-groups/{group_id}
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "msg": "Variant group 'Naturales' deleted successfully"
}
```

> **Nota:** Eliminar un grupo también elimina todas sus variantes.

---

### 6. Eliminar múltiples variantes (Bulk)

```http
DELETE /admin/variants/bulk
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "variant_ids": [10, 11, 12, 15]
}
```

**Respuesta:**
```json
{
  "deleted": 3,
  "failed": 1,
  "errors": [
    {"id": 15, "error": "Variant not found"}
  ]
}
```

---

## Resumen de Endpoints de Variantes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/admin/products/{id}/variant-groups` | Agregar grupo con variantes |
| POST | `/admin/variant-groups/{id}/variants` | Agregar variante a grupo |
| PUT | `/admin/variants/{id}` | Actualizar variante |
| DELETE | `/admin/variants/{id}` | Eliminar variante |
| DELETE | `/admin/variant-groups/{id}` | Eliminar grupo |
| DELETE | `/admin/variants/bulk` | Eliminar múltiples variantes |
