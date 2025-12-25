# Cart API - Shipping Address & Payment Methods Update

## Resumen de cambios

El carrito ahora:
1. Guarda la dirección de envío
2. Calcula tax automáticamente con la dirección guardada
3. Incluye métodos de pago disponibles
4. **`POST /checkout/options` ya no es necesario**

---

## Nuevo Endpoint: `PUT /cart/shipping`

Guarda la dirección de envío en el carrito. Una vez guardada, el tax se calcula automáticamente en cada `GET /cart`.

### Request

```http
PUT /api/v1/cart/shipping
Authorization: Bearer <token>  (o X-Session-ID para guests)
Content-Type: application/json
```

```json
{
  "street": "123 Main St",
  "city": "Albuquerque",
  "state": "NM",
  "zipcode": "87121",
  "is_pickup": false
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `street` | string | No | Calle (opcional para tax, requerido para envío) |
| `city` | string | Sí | Ciudad |
| `state` | string | Sí | Estado (código de 2 letras: NM, TX, etc.) |
| `zipcode` o `zip` | string | Sí | Código postal (acepta ambos nombres) |
| `is_pickup` | boolean | No | `true` si es pickup en tienda |
| `delivery_method` | string | No | Alternativa: "pickup" o "delivery" |

**Campos extra aceptados (ignorados):** `first_name`, `last_name`, `phone`, `email`, `country`

### Response

```json
{
  "success": true,
  "message": "Shipping address saved",
  "shipping_address": {
    "street": "123 Main St",
    "city": "Albuquerque",
    "state": "NM",
    "zipcode": "87121"
  },
  "is_pickup": false
}
```

---

## Cambios en `GET /cart`

### Nuevos campos en la respuesta:

```json
{
  "id": 1,
  "items_count": 3,
  "subtotal": 150.00,
  "shipping_fee": 9.99,
  
  // TAX - Ahora se calcula si hay dirección guardada
  "tax": 11.81,
  "tax_rate": 7.875,
  "tax_source": "grt_api",
  
  "total": 171.80,
  
  // DIRECCIÓN GUARDADA
  "shipping_address": {
    "street": "123 Main St",
    "city": "Albuquerque", 
    "state": "NM",
    "zipcode": "87121"
  },
  "is_pickup": false,
  
  // MÉTODOS DE PAGO DISPONIBLES
  "payment_methods": [
    {
      "id": "stripe",
      "name": "Credit/Debit Card",
      "name_es": "Tarjeta de Crédito/Débito",
      "enabled": true,
      "icon": "credit-card"
    },
    {
      "id": "cash",
      "name": "Cash on Delivery",
      "name_es": "Pago en Efectivo",
      "enabled": true,
      "icon": "cash"
    },
    {
      "id": "zelle",
      "name": "Zelle",
      "name_es": "Zelle",
      "enabled": true,
      "icon": "zelle"
    }
  ],
  
  // VALIDACIÓN
  "can_checkout": true,
  "min_order_amount": 50,
  "max_order_amount": 1000,
  "order_validation_error": null,
  
  // ITEMS
  "items": [...]
}
```

### Comportamiento del tax:

| Escenario | tax | tax_source |
|-----------|-----|------------|
| Sin dirección guardada | 0 | "none" |
| Dirección en NM | Calculado | "grt_api" |
| Dirección fuera de NM | 0 | "none" |
| is_pickup = true | Calculado con dirección tienda | "store_rate" |
| Error de API GRT | Usa fixed_rate o 0 | "fixed_rate" o "none" |

---

## Nuevo Endpoint: `DELETE /cart/shipping`

Elimina la dirección de envío del carrito (opcional).

### Request

```http
DELETE /api/v1/cart/shipping
Authorization: Bearer <token>
```

### Response

```json
{
  "success": true,
  "message": "Shipping address removed"
}
```

---

## Flujo Recomendado para Frontend

```
1. Usuario agrega productos al carrito
   GET /cart → tax=0, payment_methods=[...]

2. Usuario va a checkout e ingresa dirección
   PUT /cart/shipping { city, state, zipcode }

3. Frontend actualiza vista con tax calculado
   GET /cart → tax=11.81, tax_source="grt_api"

4. Usuario agrega más productos
   POST /cart/items
   GET /cart → tax se recalcula automáticamente

5. Usuario selecciona método de pago y confirma
   POST /checkout/order { payment_method: "stripe" }
```

---

## Deprecación

### ❌ `POST /checkout/options` - YA NO ES NECESARIO

Este endpoint será deprecado. Toda la información ahora está en `GET /cart`:
- ~~shipping_options~~ → Ya no se usa
- payment_methods → Ahora en `GET /cart`
- tax calculation → Ahora en `GET /cart` (con dirección guardada)

---

## Ejemplo completo

### 1. Carrito sin dirección

```http
GET /api/v1/cart
```

```json
{
  "subtotal": 150.00,
  "shipping_fee": 9.99,
  "tax": 0,
  "tax_rate": 0,
  "tax_source": "none",
  "total": 159.99,
  "shipping_address": null,
  "is_pickup": false,
  "payment_methods": [
    {"id": "stripe", "name": "Credit/Debit Card", "enabled": true},
    {"id": "cash", "name": "Cash on Delivery", "enabled": true}
  ]
}
```

### 2. Guardar dirección

```http
PUT /api/v1/cart/shipping
{
  "city": "Albuquerque",
  "state": "NM", 
  "zipcode": "87121"
}
```

### 3. Carrito con tax calculado

```http
GET /api/v1/cart
```

```json
{
  "subtotal": 150.00,
  "shipping_fee": 9.99,
  "tax": 12.59,
  "tax_rate": 7.875,
  "tax_source": "grt_api",
  "total": 172.58,
  "shipping_address": {
    "city": "Albuquerque",
    "state": "NM",
    "zipcode": "87121"
  },
  "is_pickup": false,
  "payment_methods": [...]
}
```
