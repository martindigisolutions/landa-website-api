# Shipping Rules API

Sistema de reglas de envío configurables para calcular costos de shipping y otorgar libras gratis basadas en productos o categorías.

---

## Resumen

El sistema permite:
- Configurar reglas de libras gratis por productos específicos o categorías
- Establecer cargos mínimos por peso bajo
- Definir tarifas base por libra
- Calcular automáticamente el costo de envío en checkout
- Mostrar sugerencias inteligentes cuando el cliente está cerca de cumplir una regla

---

## Tipos de Reglas

| Tipo | Descripción | Campos Requeridos |
|------|-------------|-------------------|
| `free_weight_per_product` | Por cada X productos de SKUs específicos → Z lbs gratis | `product_quantity`, `selected_products`, `free_weight_lbs` |
| `free_weight_per_category` | Por cada X productos de categorías → Z lbs gratis | `product_quantity`, `selected_categories`, `free_weight_lbs` |
| `minimum_weight_charge` | Si peso billable < X lbs → cobrar $Y | `minimum_weight_lbs`, `charge_amount` |
| `base_rate` | Tarifa por libra para peso restante | `rate_per_lb` |

---

## Endpoints Admin

Todos los endpoints requieren autenticación OAuth con scope `shipping:read` o `shipping:write`.

### POST `/admin/shipping-rules/sync`

Sincroniza TODAS las reglas desde el dashboard. **Reemplaza todas las reglas existentes.**

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request:**
```json
{
  "rules": [
    {
      "rule_type": "free_weight_per_product",
      "name": "Tintes específicos - 1 lb gratis cada 3",
      "is_active": true,
      "priority": 0,
      "product_quantity": 3,
      "selected_products": ["SKU-001", "SKU-002", "SKU-003"],
      "free_weight_lbs": 1.0
    },
    {
      "rule_type": "free_weight_per_category",
      "name": "Extensiones - 2 lbs gratis cada 5",
      "is_active": true,
      "priority": 5,
      "product_quantity": 5,
      "selected_categories": ["extensiones", "extensiones-clip", "extensiones-bundle"],
      "free_weight_lbs": 2.0
    },
    {
      "rule_type": "minimum_weight_charge",
      "name": "Cargo envío pequeño",
      "is_active": true,
      "priority": 10,
      "minimum_weight_lbs": 2.0,
      "charge_amount": 5.99
    },
    {
      "rule_type": "base_rate",
      "name": "Tarifa base por libra",
      "is_active": true,
      "priority": 100,
      "rate_per_lb": 1.50
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "synced": 4,
  "message": "Successfully synced 4 shipping rules",
  "warnings": [
    "SKUs not found in database (rule will still apply): SKU-999"
  ]
}
```

---

### POST `/admin/shipping-rules`

Crea una regla individual.

**Request:**
```json
{
  "rule_type": "free_weight_per_product",
  "name": "Tintes - 1 lb gratis cada 3",
  "product_quantity": 3,
  "selected_products": ["SKU-001", "SKU-002"],
  "free_weight_lbs": 1.0,
  "priority": 0,
  "is_active": true
}
```

**Response (200):**
```json
{
  "id": 1,
  "rule_type": "free_weight_per_product",
  "name": "Tintes - 1 lb gratis cada 3",
  "selected_products": ["SKU-001", "SKU-002"],
  "selected_categories": [],
  "product_quantity": 3,
  "free_weight_lbs": 1.0,
  "minimum_weight_lbs": null,
  "charge_amount": null,
  "rate_per_lb": null,
  "priority": 0,
  "is_active": true,
  "created_at": "2025-12-11T12:00:00",
  "updated_at": "2025-12-11T12:00:00"
}
```

---

### GET `/admin/shipping-rules`

Lista todas las reglas ordenadas por prioridad.

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `rule_type` | string | Filtrar por tipo de regla |
| `is_active` | boolean | Filtrar por estado activo |

**Response (200):**
```json
[
  {
    "id": 1,
    "rule_type": "free_weight_per_product",
    "name": "Tintes - 1 lb gratis cada 3",
    "selected_products": ["SKU-001", "SKU-002"],
    "selected_categories": [],
    "product_quantity": 3,
    "free_weight_lbs": 1.0,
    "minimum_weight_lbs": null,
    "charge_amount": null,
    "rate_per_lb": null,
    "priority": 0,
    "is_active": true,
    "created_at": "2025-12-11T12:00:00",
    "updated_at": "2025-12-11T12:00:00"
  }
]
```

---

### GET `/admin/shipping-rules/{rule_id}`

Obtiene una regla por ID.

**Response (200):**
```json
{
  "id": 1,
  "rule_type": "free_weight_per_product",
  "name": "Tintes - 1 lb gratis cada 3",
  "selected_products": ["SKU-001", "SKU-002"],
  "selected_categories": [],
  "product_quantity": 3,
  "free_weight_lbs": 1.0,
  "minimum_weight_lbs": null,
  "charge_amount": null,
  "rate_per_lb": null,
  "priority": 0,
  "is_active": true,
  "created_at": "2025-12-11T12:00:00",
  "updated_at": "2025-12-11T12:00:00"
}
```

---

### PUT `/admin/shipping-rules/{rule_id}`

Actualiza una regla. Solo los campos enviados serán actualizados.

**Request:**
```json
{
  "name": "Tintes - 2 lbs gratis cada 3",
  "free_weight_lbs": 2.0,
  "is_active": false
}
```

**Response (200):** Regla actualizada completa.

---

### DELETE `/admin/shipping-rules/{rule_id}`

Elimina una regla permanentemente.

**Response (200):**
```json
{
  "msg": "Shipping rule 'Tintes - 1 lb gratis cada 3' deleted successfully"
}
```

---

## Endpoint Checkout

### POST `/checkout/calculate-shipping`

Calcula el costo de envío basado en el contenido del carrito y las reglas configuradas. **No requiere autenticación.**

**Request:**
```json
{
  "products": [
    {"product_id": 1, "quantity": 3},
    {"product_id": 2, "quantity": 2, "variant_id": 5}
  ],
  "address": {
    "city": "Miami",
    "state": "FL",
    "zip": "33101",
    "country": "US"
  }
}
```

**Response (200):**
```json
{
  "total_weight_lbs": 5.5,
  "free_weight_lbs": 2.0,
  "billable_weight_lbs": 3.5,
  "shipping_cost": 5.25,
  "applied_rules": [
    {
      "rule_name": "Tintes específicos - 1 lb gratis cada 3",
      "rule_type": "free_weight_per_product",
      "free_weight_granted": 2.0,
      "quantity_matched": 6
    }
  ],
  "suggestions": [
    {
      "suggestion_type": "add_products_for_free_weight",
      "message": "¡Agrega 1 producto(s) más de Extensiones para obtener 2.0 libras de envío gratis!",
      "message_en": "Add 1 more product(s) from Extensiones to get 2.0 lbs free shipping!",
      "products_needed": 1,
      "category_name": "Extensiones",
      "potential_savings": 2.0
    },
    {
      "suggestion_type": "fill_remaining_weight",
      "message": "¡Todavía puedes agregar hasta 0.5 libras más por el mismo costo de envío!",
      "message_en": "You can still add up to 0.5 more lbs for the same shipping cost!",
      "remaining_lbs": 0.5
    }
  ],
  "summary": "Envío: $5.25",
  "summary_en": "Shipping: $5.25"
}
```

---

## Campos de Response

### CalculateShippingResponse

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_weight_lbs` | float | Peso total del carrito en libras |
| `free_weight_lbs` | float | Libras cubiertas por envío gratis |
| `billable_weight_lbs` | float | Libras a cobrar (total - free) |
| `shipping_cost` | float | Costo final de envío en USD |
| `applied_rules` | array | Lista de reglas aplicadas |
| `suggestions` | array | Sugerencias para ahorrar en envío |
| `summary` | string | Mensaje resumen en español |
| `summary_en` | string | Mensaje resumen en inglés |

### AppliedShippingRule

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `rule_name` | string | Nombre de la regla |
| `rule_type` | string | Tipo de regla |
| `free_weight_granted` | float | Libras gratis otorgadas |
| `quantity_matched` | int | Cantidad de productos que coincidieron |

### ShippingSuggestion

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `suggestion_type` | string | `add_products_for_free_weight` o `fill_remaining_weight` |
| `message` | string | Mensaje en español |
| `message_en` | string | Mensaje en inglés |
| `products_needed` | int | Productos faltantes (para add_products) |
| `category_name` | string | Nombre de categoría (para category rules) |
| `potential_savings` | float | Libras que podrían ahorrarse |
| `remaining_lbs` | float | Libras restantes en capacidad gratis |

---

## Lógica de Cálculo

### Orden de Evaluación

Las reglas se evalúan en orden de `priority` (menor = primero):

1. **Calcular peso base** del envío (suma de `weight_lbs` × `quantity` por producto)
2. **Aplicar reglas `free_weight_per_product`** (acumular libras gratis)
3. **Aplicar reglas `free_weight_per_category`** (acumular libras gratis)
4. **Calcular peso billable** = peso total - libras gratis (mínimo 0)
5. **Aplicar `minimum_weight_charge`** si peso billable < umbral
6. **Aplicar `base_rate`** al peso billable restante
7. **Generar sugerencias** para clientes cerca del 80% de cumplir una regla

### Fórmulas

**Libras gratis por producto/categoría:**
```
libras_gratis = floor(cantidad_productos_aplicables / product_quantity) * free_weight_lbs
```

**Sugerencias (80% threshold):**
```
progreso = (cantidad_actual % product_quantity) / product_quantity
si progreso >= 0.8:
    productos_faltantes = product_quantity - (cantidad_actual % product_quantity)
    mostrar sugerencia
```

---

## Ejemplos de Reglas

### Regla: Libras gratis por productos específicos
```json
{
  "rule_type": "free_weight_per_product",
  "name": "Tintes específicos - 1 lb gratis cada 3",
  "product_quantity": 3,
  "selected_products": ["TINTE-001", "TINTE-002", "TINTE-003"],
  "free_weight_lbs": 1.0,
  "priority": 0
}
```
**Efecto:** Por cada 3 productos de los SKUs seleccionados, se otorga 1 lb gratis.

---

### Regla: Libras gratis por categoría
```json
{
  "rule_type": "free_weight_per_category",
  "name": "Extensiones - 2 lbs gratis cada 5",
  "product_quantity": 5,
  "selected_categories": ["extensiones", "extensiones-clip"],
  "free_weight_lbs": 2.0,
  "priority": 5
}
```
**Efecto:** Por cada 5 productos de las categorías seleccionadas, se otorgan 2 lbs gratis.

---

### Regla: Cargo mínimo por peso bajo
```json
{
  "rule_type": "minimum_weight_charge",
  "name": "Cargo por pedido pequeño",
  "minimum_weight_lbs": 2.0,
  "charge_amount": 5.99,
  "priority": 10
}
```
**Efecto:** Si el peso billable es menor a 2 lbs, se cobra $5.99 adicionales.

---

### Regla: Tarifa base por libra
```json
{
  "rule_type": "base_rate",
  "name": "Tarifa estándar",
  "rate_per_lb": 1.50,
  "priority": 100
}
```
**Efecto:** Se cobra $1.50 por cada libra de peso billable (si no aplica minimum_weight_charge).

---

## Notas de Implementación

1. **Campo `weight_lbs` en productos:** Cada producto debe tener su peso configurado en libras para que el cálculo funcione correctamente.

2. **Validación de SKUs/categorías:** El sync valida si los SKUs y categorías existen, pero solo genera warnings (no bloquea). Las reglas se aplican aunque algunos SKUs no existan.

3. **Prioridad:** Usar valores como 0, 5, 10, 100 para mantener orden claro. Las reglas de descuento deben tener menor prioridad (evaluarse primero).

4. **Productos con múltiples categorías:** Si un producto pertenece a cualquiera de las categorías seleccionadas, cuenta para la regla.

5. **Sugerencias al 80%:** Solo se muestran sugerencias cuando el cliente tiene 80% o más de progreso hacia cumplir una regla.

---

## Scopes OAuth Requeridos

| Endpoint | Scope Requerido |
|----------|-----------------|
| `POST /admin/shipping-rules/sync` | `shipping:write` |
| `POST /admin/shipping-rules` | `shipping:write` |
| `GET /admin/shipping-rules` | `shipping:read` |
| `GET /admin/shipping-rules/{id}` | `shipping:read` |
| `PUT /admin/shipping-rules/{id}` | `shipping:write` |
| `DELETE /admin/shipping-rules/{id}` | `shipping:write` |
| `POST /checkout/calculate-shipping` | (público) |

---

## Errores Comunes

| Código | Mensaje | Causa |
|--------|---------|-------|
| 400 | "free_weight_per_product rule requires selected_products" | Falta campo requerido según tipo de regla |
| 400 | "Invalid rule_type" | Tipo de regla no válido |
| 401 | "Invalid or expired token" | Token OAuth inválido o expirado |
| 403 | "Insufficient scope" | Token no tiene scope `shipping:read` o `shipping:write` |
| 404 | "Shipping rule not found" | ID de regla no existe |

