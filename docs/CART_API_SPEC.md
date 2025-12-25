# 📋 Especificación API: GET /cart

## Resumen

El endpoint `GET /cart` devuelve toda la información necesaria para:
- Mostrar el **Order Summary** completo (subtotal, shipping, taxes, total)
- Validar **mínimo y máximo de compra**
- Mostrar **incentivos de shipping** (opcional)
- Calcular **impuestos dinámicamente** según dirección

---

## Endpoint

```http
GET /cart
Authorization: Bearer {token}
Accept-Language: es | en
```

**Headers:**
- `X-Session-ID`: Requerido para usuarios guest
- `Authorization`: Bearer token (opcional)
- `Accept-Language`: `en` para inglés, `es` para español (por defecto)

---

## Campos de Respuesta

### Campos Base (existentes)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | `number` | ID del carrito |
| `items_count` | `number` | Cantidad de líneas en el carrito |
| `total_items` | `number` | Cantidad total de productos |
| `subtotal` | `number` | Suma de los productos (sin shipping ni taxes) |
| `items` | `array` | Lista de items del carrito |
| `warnings` | `array` | Advertencias de stock, etc. |

### Campos de Totales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `shipping_fee` | `number` | Costo de envío calculado según reglas |
| `tax` | `number` | Impuestos calculados (ver lógica abajo) |
| `tax_rate` | `number` | Tasa de impuesto aplicada (%) |
| `tax_source` | `string` | Origen del cálculo: `grt_api`, `fixed_rate`, `store_rate`, `none` |
| `total` | `number` | `subtotal + shipping_fee + tax` |

### Campos de Validación de Compra

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `can_checkout` | `boolean` | `true` si puede proceder al checkout |
| `min_order_amount` | `number` | Monto mínimo de compra permitido |
| `max_order_amount` | `number` | Monto máximo de compra permitido |
| `order_validation_error` | `string \| null` | Mensaje de error si no cumple min/max |

### Campos de Incentivos (Opcional)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `shipping_incentive` | `object \| null` | Sugerencia para obtener mejor envío |

---

## Estructura del Shipping Incentive

Cuando el usuario está cerca de alcanzar una regla de shipping más favorable:

```json
{
  "type": "free_shipping | reduced_shipping | category_discount",
  "message": "Mensaje para mostrar al usuario",
  "amount_needed": 25.00,
  "items_needed": null,
  "category": null,
  "potential_savings": 8.00
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `type` | `string` | Tipo de incentivo |
| `message` | `string` | Mensaje listo para mostrar al usuario |
| `amount_needed` | `number \| null` | Monto adicional necesario |
| `items_needed` | `number \| null` | Cantidad de items adicionales necesarios |
| `category` | `string \| null` | Categoría específica si aplica |
| `potential_savings` | `number` | Cuánto ahorraría en envío |

---

## Lógica de Cálculo de Impuestos (Tax)

### Flujo de Decisión

```
┌─────────────────────────────────────────────────────────────┐
│  ¿Tipo de orden?                                            │
│       │                                                      │
│       ├── PICKUP ──────► Usar dirección de la TIENDA        │
│       │                         │                            │
│       │                         ▼                            │
│       │                  ¿Estado = NM?                       │
│       │                    │       │                         │
│       │                   Sí      No                         │
│       │                    │       │                         │
│       │                    ▼       ▼                         │
│       │              API GRT   Fixed Rate / 0                │
│       │                                                      │
│       └── DELIVERY ────► Usar dirección del CLIENTE         │
│                                │                             │
│                                ▼                             │
│                         ¿Estado = NM?                        │
│                           │       │                          │
│                          Sí      No                          │
│                           │       │                          │
│                           ▼       ▼                          │
│                     API GRT   Fixed Rate / 0                 │
└─────────────────────────────────────────────────────────────┘
```

### Valores de `tax_source`

| Valor | Descripción |
|-------|-------------|
| `grt_api` | Calculado usando API de New Mexico GRT |
| `fixed_rate` | Usando tasa fija configurada en admin |
| `store_rate` | Usando dirección de tienda (para pickup) |
| `none` | No se cobran impuestos |

### Notas sobre Tax

- **New Mexico**: Se usa la [API GRT](https://grt.edacnm.org) para calcular la tasa exacta por dirección
- **Fuera de NM**: Por ahora retorna `0` (configurable en admin)
- **Pickup**: Siempre usa la dirección de la tienda configurada
- El campo `tax_rate` muestra el porcentaje usado (ej: `7.875`)

---

## Formato de Respuesta

> ⚠️ **IMPORTANTE**: Este endpoint retorna respuesta **PLANA** (sin wrapper `{ success, data }`).
> Esto es consistente con el comportamiento actual del API.

---

## Ejemplos de Respuesta

### ✅ Compra válida, sin incentivo

```json
{
  "id": 123,
  "items_count": 3,
  "total_items": 5,
  "subtotal": 150.00,
  "items": [
    {
      "id": 1,
      "product_id": 101,
      "product_name": "Shampoo Profesional",
      "quantity": 2,
      "price": 25.00,
      "total": 50.00,
      "image_url": "https://..."
    }
  ],
  "warnings": [],
  
  "shipping_fee": 0.00,
  "tax": 12.38,
  "tax_rate": 8.25,
  "tax_source": "grt_api",
  "total": 162.38,
  
  "can_checkout": true,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": null,
  
  "shipping_incentive": null
}
```

### ✅ Compra válida, con incentivo de envío gratis

```json
{
  "id": 123,
  "items_count": 2,
  "total_items": 3,
  "subtotal": 75.00,
  "items": [...],
  "warnings": [],
  
  "shipping_fee": 8.00,
  "tax": 6.19,
  "tax_rate": 8.25,
  "tax_source": "grt_api",
  "total": 89.19,
  
  "can_checkout": true,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": null,
  
  "shipping_incentive": {
    "type": "free_shipping",
    "message": "Agrega $25 más para envío GRATIS",
    "amount_needed": 25.00,
    "items_needed": null,
    "category": null,
    "potential_savings": 8.00
  }
}
```

### ✅ Incentivo por categoría específica

```json
{
  "shipping_incentive": {
    "type": "category_discount",
    "message": "Agrega 2 productos de 'Tintes' para reducir el envío a $5",
    "amount_needed": null,
    "items_needed": 2,
    "category": "Tintes",
    "potential_savings": 5.00
  }
}
```

### ❌ Debajo del mínimo de compra

```json
{
  "id": 123,
  "items_count": 1,
  "total_items": 1,
  "subtotal": 35.00,
  "items": [...],
  "warnings": [],
  
  "shipping_fee": 10.00,
  "tax": 0.00,
  "tax_rate": 0,
  "tax_source": "none",
  "total": 45.00,
  
  "can_checkout": false,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": "El pedido mínimo es de $50.00. Agrega $15.00 más para continuar.",
  
  "shipping_incentive": null
}
```

### ❌ Arriba del máximo de compra

```json
{
  "id": 123,
  "items_count": 15,
  "total_items": 50,
  "subtotal": 2500.00,
  "items": [...],
  "warnings": [],
  
  "shipping_fee": 0.00,
  "tax": 206.25,
  "tax_rate": 8.25,
  "tax_source": "grt_api",
  "total": 2706.25,
  
  "can_checkout": false,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": "El pedido máximo es de $2,000.00. Reduce $500.00 para continuar.",
  
  "shipping_incentive": null
}
```

### ✅ Orden de Pickup (usa tax de tienda)

```json
{
  "id": 123,
  "items_count": 2,
  "total_items": 4,
  "subtotal": 100.00,
  "items": [...],
  "warnings": [],
  
  "shipping_fee": 0.00,
  "tax": 7.88,
  "tax_rate": 7.875,
  "tax_source": "store_rate",
  "total": 107.88,
  
  "can_checkout": true,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": null,
  
  "shipping_incentive": null
}
```

### ✅ Orden fuera de New Mexico (sin tax)

```json
{
  "id": 123,
  "items_count": 2,
  "total_items": 4,
  "subtotal": 100.00,
  "items": [...],
  "warnings": [],
  
  "shipping_fee": 12.00,
  "tax": 0.00,
  "tax_rate": 0,
  "tax_source": "none",
  "total": 112.00,
  
  "can_checkout": true,
  "min_order_amount": 50.00,
  "max_order_amount": 2000.00,
  "order_validation_error": null,
  
  "shipping_incentive": null
}
```

---

## Reglas de Negocio

### Shipping

- El costo de envío se calcula según las reglas configuradas en el backend
- Puede haber envío gratis si se cumple cierto monto o condición
- El incentivo solo se muestra si el usuario alcanzó el **80%** de una regla

### Taxes

- **New Mexico**: Usa API GRT (https://grt.edacnm.org) para tasa exacta por dirección
- **Fuera de NM**: No hay impuestos (por ahora)
- **Pickup**: Usa la dirección de la tienda configurada en admin
- La dirección de la tienda es configurable desde el dashboard admin

### Validación de Compra

- **Mínimo**: El usuario no puede hacer checkout si `subtotal < min_order_amount`
- **Máximo**: El usuario no puede hacer checkout si `subtotal > max_order_amount`
- El botón de checkout se deshabilita y se muestra `order_validation_error`
- Los valores de min/max son configurables desde el dashboard admin

---

## Resumen de Campos

| Campo | Obligatorio | Tipo | Descripción |
|-------|:-----------:|------|-------------|
| `id` | ✅ | number | ID del carrito |
| `items_count` | ✅ | number | Líneas en el carrito |
| `total_items` | ✅ | number | Total de productos |
| `subtotal` | ✅ | number | Suma de productos |
| `items` | ✅ | array | Lista de items |
| `warnings` | ✅ | array | Advertencias |
| `shipping_fee` | ✅ | number | Costo de envío |
| `tax` | ✅ | number | Impuestos (puede ser 0) |
| `tax_rate` | ✅ | number | Tasa aplicada (%) |
| `tax_source` | ✅ | string | Origen del cálculo |
| `total` | ✅ | number | Total final |
| `can_checkout` | ✅ | boolean | Si puede proceder |
| `min_order_amount` | ✅ | number | Mínimo permitido |
| `max_order_amount` | ✅ | number | Máximo permitido |
| `order_validation_error` | ✅ | string \| null | Mensaje de error |
| `shipping_incentive` | ⚪ | object \| null | Incentivo de shipping |

---

## Notas de Implementación Frontend

### Order Summary UI

```
┌─────────────────────────────────────┐
│  Order Summary                      │
├─────────────────────────────────────┤
│  Subtotal (5 items)       $150.00   │
│  Shipping                   $0.00   │
│  Tax (8.25%)               $12.38   │
├─────────────────────────────────────┤
│  Total                    $162.38   │
└─────────────────────────────────────┘
```

### Shipping Incentive Banner

Mostrar cuando `shipping_incentive` no es null:

```
┌─────────────────────────────────────────────────┐
│  🚚 Agrega $25 más para envío GRATIS           │
│     Ahorrarías $8.00                           │
└─────────────────────────────────────────────────┘
```

### Checkout Button States

```javascript
if (!can_checkout) {
  // Botón deshabilitado
  // Mostrar order_validation_error debajo del botón
}
```

### Manejo de Tax Source

```javascript
// Mostrar texto según tax_source
switch (tax_source) {
  case 'grt_api':
  case 'store_rate':
    return `Tax (${tax_rate}%)`;
  case 'fixed_rate':
    return `Tax (${tax_rate}%)`;
  case 'none':
    return 'Tax'; // No mostrar porcentaje
}
```

---

## Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2024-12-20 | Especificación inicial |
| 1.1 | 2024-12-20 | Agregados campos `tax_rate` y `tax_source` para cálculo dinámico de impuestos |
| 1.2 | 2024-12-20 | Aclaración: respuesta es PLANA (sin wrapper `{ success, data }`) |
