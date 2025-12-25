# 🔒 API de Checkout con Sistema de Locks

## Resumen del Flujo

```
1. PUT /cart/shipping      → Guardar dirección, calcular tax
2. PUT /cart/payment-method → Guardar método de pago
3. POST /cart/lock         → Reservar stock (5 min), obtener lock_token
4. [Procesar pago]         → Stripe/Zelle
5. POST /orders            → Crear orden con lock_token
```

---

## Endpoints

### 1. `PUT /cart/payment-method`

Guarda el método de pago en el carrito.

**Request:**
```http
PUT /cart/payment-method
X-Session-ID: session_abc123  (para guests)
Authorization: Bearer xxx      (para usuarios autenticados)
Content-Type: application/json

{
    "payment_method": "stripe"
}
```

**Valores permitidos:** `"stripe"` | `"zelle"`

**Response exitosa (200):**
```json
{
    "success": true,
    "payment_method": "stripe",
    "message": "Payment method saved"
}
```

**Errores:**
- `400`: Método de pago inválido
- `404`: Carrito no encontrado

---

### 2. `GET /cart` (actualizado)

Ahora incluye `payment_method` en la respuesta.

**Response:**
```json
{
    "id": 1,
    "items": [...],
    "subtotal": 100.00,
    "shipping_fee": 10.00,
    "tax": 8.25,
    "tax_rate": 8.25,
    "tax_source": "grt_api",
    "total": 118.25,
    "shipping_address": {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-1234",
        "email": "john@example.com",
        "street": "123 Main St",
        "city": "Albuquerque",
        "state": "NM",
        "zipcode": "87102",
        "country": "US"
    },
    "is_pickup": false,
    "payment_method": "stripe",
    "can_checkout": true,
    "min_order_amount": 50,
    "max_order_amount": 1000,
    "order_validation_error": null,
    "shipping_incentive": null
}
```

---

### 3. `POST /cart/lock`

Valida stock y reserva temporalmente (5 minutos).

**Request:**
```http
POST /cart/lock
X-Session-ID: session_abc123
Authorization: Bearer xxx
Content-Type: application/json

{}
```
*No necesita body, usa el carrito actual.*

**Response exitosa (200):**
```json
{
    "success": true,
    "lock_token": "lock_a1b2c3d4e5f6",
    "expires_at": "2024-12-25T15:30:00Z",
    "expires_in_seconds": 900,
    "payment_intent": {
        "client_secret": "pi_xxx_secret_yyy",
        "amount": 11825,
        "currency": "usd"
    }
}
```

> **Nota:** `payment_intent` solo se incluye si `payment_method` es `"stripe"`.

**Response sin stock (200 pero success=false):**
```json
{
    "success": false,
    "error": "stock_unavailable",
    "message": "Algunos productos no tienen stock suficiente",
    "unavailable_items": [
        {
            "product_id": 123,
            "variant_id": 456,
            "product_name": "Shampoo XYZ",
            "variant_name": "500ml",
            "requested": 5,
            "available": 2
        }
    ]
}
```

**Errores:**
- `400`: Carrito vacío o sin dirección de envío
- `400`: Método de pago no seleccionado
- `404`: Carrito no encontrado

**Comportamiento:**
- Cancela cualquier lock anterior del mismo carrito
- Reserva stock por 5 minutos
- Si es Stripe, crea `PaymentIntent`
- Solo puede existir 1 lock activo por carrito

---

### 4. `DELETE /cart/lock`

Cancela un lock y libera el stock reservado.

**Request:**
```http
DELETE /cart/lock
X-Session-ID: session_abc123
Authorization: Bearer xxx
Content-Type: application/json

{
    "lock_token": "lock_a1b2c3d4e5f6"
}
```

**Response exitosa (200):**
```json
{
    "success": true,
    "message": "Lock cancelled, stock released"
}
```

**Errores:**
- `400`: Token inválido o ya expirado
- `404`: Lock no encontrado

---

### 4b. `POST /cart/lock/release` (para sendBeacon)

Endpoint alternativo para liberar lock via `navigator.sendBeacon()`.
Acepta `text/plain` además de `application/json`.

**Request con sendBeacon:**
```javascript
// Frontend code
navigator.sendBeacon('/cart/lock/release', lock_token);
```

```http
POST /cart/lock/release
Content-Type: text/plain

lock_a1b2c3d4e5f6
```

**Request con JSON (también soportado):**
```http
POST /cart/lock/release
Content-Type: application/json

{
    "lock_token": "lock_a1b2c3d4e5f6"
}
```

**Response exitosa (200):**
```json
{
    "success": true,
    "message": "Lock released"
}
```

**Notas:**
- No requiere `X-Session-ID` ni `Authorization` (el token es suficiente para identificar)
- Acepta body como texto plano (solo el token) o como JSON
- Siempre retorna 200 OK (incluso si el lock no existe o ya expiró)
- Diseñado para ser "fire and forget"

---

### Liberación del Lock (Cuándo llamar)

| Escenario | Acción del Frontend |
|-----------|---------------------|
| Usuario navega a otra página (SPA) | `DELETE /cart/lock` al desmontar componente |
| Usuario hace clic en "Volver" o "Cancelar" | `DELETE /cart/lock` explícitamente |
| Usuario cierra pestaña/navegador | `navigator.sendBeacon('/cart/lock/release', token)` |
| Pago falla (ej: tarjeta rechazada) | `DELETE /cart/lock` para liberar stock |

**Ejemplo de implementación:**

```javascript
// React component
useEffect(() => {
    // Cleanup on unmount
    return () => {
        if (lockToken) {
            fetch('/cart/lock', {
                method: 'DELETE',
                body: JSON.stringify({ lock_token: lockToken })
            });
        }
    };
}, [lockToken]);

// Handle browser close
useEffect(() => {
    const handleBeforeUnload = () => {
        if (lockToken) {
            navigator.sendBeacon('/cart/lock/release', lockToken);
        }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, [lockToken]);
```

> **Importante:** El timeout de 5 minutos es un **respaldo** por si el frontend 
> no puede llamar DELETE (crash, pérdida de conexión, móvil). El frontend 
> **siempre intentará** liberar el lock activamente cuando sea posible.

---

### 5. `POST /orders` (actualizado)

Ahora requiere `lock_token` para crear la orden.

**Request:**
```http
POST /orders
X-Session-ID: session_abc123
Authorization: Bearer xxx
Content-Type: application/json

{
    "lock_token": "lock_a1b2c3d4e5f6",
    "payment_id": "pi_xxx"
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `lock_token` | string | ✅ Sí | Token obtenido de POST /cart/lock |
| `payment_id` | string | ❌ No | ID de pago de Stripe (para confirmar) |

**Response exitosa (201):**
```json
{
    "success": true,
    "order_id": 456,
    "order_number": "ORD-2024-000456",
    "status": "paid",
    "message": "Order created successfully"
}
```

**Response - Lock expirado (400):**
```json
{
    "success": false,
    "error": "lock_expired",
    "message": "La reserva expiró. Por favor, intenta de nuevo."
}
```

**Response - Lock ya usado (400):**
```json
{
    "success": false,
    "error": "lock_already_used",
    "message": "Este lock ya fue utilizado para crear una orden."
}
```

**Comportamiento:**
- Valida que `lock_token` sea válido y no haya expirado
- Crea la orden
- Descuenta stock permanentemente
- Limpia el carrito
- Invalida el `lock_token`

---

## Flujos Completos

### Flujo Stripe

```
┌────────────────────────────────────────────────────────────┐
│ 1. Usuario llena dirección                                 │
│    PUT /cart/shipping                                      │
│    { street, city, state, zipcode, ... }                   │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Usuario selecciona Stripe                               │
│    PUT /cart/payment-method                                │
│    { payment_method: "stripe" }                            │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Usuario hace clic en "Pagar"                            │
│    POST /cart/lock                                         │
│    → Recibe: lock_token + payment_intent.client_secret     │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Frontend confirma pago con Stripe                       │
│    stripe.confirmPayment({ clientSecret })                 │
│    → Espera confirmación de Stripe                         │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 5. Crear orden                                             │
│    POST /orders                                            │
│    { lock_token, payment_id: "pi_xxx" }                    │
│    → Orden creada con status "paid"                        │
│    → Carrito limpiado                                      │
└────────────────────────────────────────────────────────────┘
```

### Flujo Zelle

```
┌────────────────────────────────────────────────────────────┐
│ 1. Usuario llena dirección                                 │
│    PUT /cart/shipping                                      │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Usuario selecciona Zelle                                │
│    PUT /cart/payment-method                                │
│    { payment_method: "zelle" }                             │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Usuario hace clic en "Confirmar Pedido"                 │
│    POST /cart/lock                                         │
│    → Recibe: lock_token (sin payment_intent)               │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Frontend muestra instrucciones de Zelle                 │
│    - Email/teléfono para enviar pago                       │
│    - Monto exacto a enviar                                 │
│    - Referencia/concepto a incluir                         │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 5. Usuario confirma que hizo la transferencia              │
│    POST /orders                                            │
│    { lock_token }                                          │
│    → Orden creada con status "pending_verification"        │
│    → Carrito limpiado                                      │
└────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│ 6. Admin verifica pago y actualiza orden                   │
│    (Desde dashboard de admin)                              │
│    → status cambia a "paid"                                │
└────────────────────────────────────────────────────────────┘
```

---

## Manejo de Errores en Frontend

### Error de Stock Durante Lock

```javascript
const response = await fetch('/cart/lock', { method: 'POST' });
const data = await response.json();

if (!data.success && data.error === 'stock_unavailable') {
    // Mostrar modal con productos sin stock
    showStockErrorModal(data.unavailable_items);
    
    // Opcional: Actualizar carrito para reflejar stock real
    await refreshCart();
}
```

### Lock Expirado al Crear Orden

```javascript
const response = await fetch('/orders', {
    method: 'POST',
    body: JSON.stringify({ lock_token, payment_id })
});
const data = await response.json();

if (!data.success && data.error === 'lock_expired') {
    // Informar al usuario
    showError('Tu reserva expiró. Por favor, intenta de nuevo.');
    
    // Volver al paso de lock
    await createNewLock();
}
```

---

## Tiempos

| Operación | Tiempo |
|-----------|--------|
| Lock expira | 5 minutos |
| Limpieza automática | Cada 5 minutos |

---

## Estados de una Orden

| Status | Descripción | Cuándo |
|--------|-------------|--------|
| `pending_verification` | Esperando verificación de pago | Zelle - recién creada |
| `paid` | Pago confirmado | Stripe confirmado / Zelle verificado |
| `processing` | En preparación | Admin marcó como procesando |
| `shipped` | Enviado | Delivery con tracking |
| `ready_for_pickup` | Listo para recoger | Pickup preparado |
| `completed` | Entregado | Cliente recibió |
| `cancelled` | Cancelado | Admin canceló |
| `refunded` | Reembolsado | Dinero devuelto |

---

## Ejemplo Completo (JavaScript)

```javascript
async function checkout() {
    try {
        // 1. Guardar dirección (ya debería estar guardada)
        // await saveShippingAddress(addressData);
        
        // 2. Guardar método de pago
        await fetch('/cart/payment-method', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payment_method: 'stripe' })
        });
        
        // 3. Crear lock y reservar stock
        const lockResponse = await fetch('/cart/lock', { method: 'POST' });
        const lockData = await lockResponse.json();
        
        if (!lockData.success) {
            if (lockData.error === 'stock_unavailable') {
                showStockError(lockData.unavailable_items);
                return;
            }
            throw new Error(lockData.message);
        }
        
        const { lock_token, payment_intent } = lockData;
        
        // 4. Procesar pago con Stripe
        const { error, paymentIntent } = await stripe.confirmPayment({
            clientSecret: payment_intent.client_secret,
            confirmParams: {
                return_url: window.location.origin + '/checkout/complete'
            }
        });
        
        if (error) {
            // Cancelar lock si el pago falla
            await fetch('/cart/lock', {
                method: 'DELETE',
                body: JSON.stringify({ lock_token })
            });
            throw error;
        }
        
        // 5. Crear orden
        const orderResponse = await fetch('/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lock_token,
                payment_id: paymentIntent.id
            })
        });
        
        const orderData = await orderResponse.json();
        
        if (orderData.success) {
            // Redirigir a página de confirmación
            window.location.href = `/orders/${orderData.order_id}/confirmation`;
        }
        
    } catch (error) {
        console.error('Checkout failed:', error);
        showError(error.message);
    }
}
```

---

## Preguntas Frecuentes

### ¿Qué pasa si el usuario cierra la ventana durante el pago?

- El lock expira después de 5 minutos
- El stock se libera automáticamente
- Si pagó con Stripe pero no creó la orden, el pago queda en Stripe (puede verificarse manualmente o implementar webhook después)

### ¿Puede el usuario tener múltiples locks?

No. Al crear un nuevo lock, se cancela automáticamente el anterior.

### ¿Qué pasa si el stock cambia entre GET /cart y POST /cart/lock?

El POST /cart/lock verificará el stock actual. Si no hay suficiente, retornará `success: false` con los items afectados.

### ¿El frontend necesita hacer polling para verificar expiración?

Opcional. Pueden:
1. Mostrar un contador de 5 minutos
2. Hacer polling cada minuto
3. O simplemente intentar crear la orden y manejar el error `lock_expired`
