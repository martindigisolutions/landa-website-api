# API de Combinación de Órdenes

## Resumen

El sistema permite combinar múltiples órdenes en un solo envío cuando cumplen ciertas condiciones. Cuando las órdenes se combinan, comparten los mismos shipments (paquetes) y tracking numbers, lo que permite optimizar el envío y reducir costos.

---

## Conceptos Clave

### ¿Qué significa "combinar órdenes"?

Cuando se combinan órdenes:
- **Múltiples órdenes** (ej: Orden #55, #56, #57) se agrupan en un **mismo envío**
- Todas las órdenes combinadas **comparten los mismos shipments**
- Si se crea un shipment para una orden combinada, **todas las órdenes del grupo lo ven**
- Si se marca un shipment como entregado, **todas las órdenes del grupo se marcan como entregadas**

### Ejemplo Visual

```
Antes de combinar:
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Orden 55│  │ Orden 56│  │ Orden 57│
│ Status: │  │ Status: │  │ Status: │
│  paid   │  │  paid   │  │  paid   │
│         │  │         │  │         │
│ Shipment│  │ Shipment│  │ Shipment│
│   #1    │  │   #1    │  │   #1    │
└─────────┘  └─────────┘  └─────────┘

Después de combinar:
┌─────────────────────────────────────┐
│  Grupo de Órdenes Combinadas         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │ Orden 55│ │ Orden 56│ │ Orden 57││
│  │ Status: │ │ Status: │ │ Status: ││
│  │ shipped │ │ shipped │ │ shipped ││
│  └─────────┘ └─────────┘ └─────────┘│
│                                     │
│  Shipments Compartidos:             │
│  ┌─────────────────────────────┐   │
│  │ Shipment #1 (compartido)    │   │
│  │ Tracking: 1Z999AA10123456784│   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │ Shipment #2 (compartido)    │   │
│  │ Tracking: 1Z999AA10123456785│   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## Para el Dashboard Admin

### 1. Combinar Órdenes

**Endpoint:** `POST /admin/orders/combine`

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body:**
```json
{
  "order_ids": [55, 56, 57],
  "notes": "Órdenes combinadas para envío conjunto - Cliente VIP"
}
```

**Validaciones Automáticas:**
1. ✅ Todas las órdenes deben existir
2. ✅ Todas las órdenes deben estar **pagadas** (`status: "paid"` y `payment_status: "completed"`)
3. ✅ Todas las órdenes deben tener la **misma dirección de envío** (mismo `city`, `state`, `zip`, `country`)
4. ✅ Ninguna orden puede estar ya combinada con otro grupo
5. ✅ Ninguna orden puede tener shipments existentes (deben estar sin enviar)

**Response (Éxito):**
```json
{
  "success": true,
  "message": "Orders combined successfully",
  "combined_group_id": "cg_abc123xyz",
  "orders": [
    {
      "id": 55,
      "status": "paid",
      "combined": true,
      "combined_group_id": "cg_abc123xyz"
    },
    {
      "id": 56,
      "status": "paid",
      "combined": true,
      "combined_group_id": "cg_abc123xyz"
    },
    {
      "id": 57,
      "status": "paid",
      "combined": true,
      "combined_group_id": "cg_abc123xyz"
    }
  ]
}
```

**Response (Error - Validación fallida):**
```json
{
  "success": false,
  "error": "validation_failed",
  "message": "Cannot combine orders: validation failed",
  "details": {
    "order_55": {
      "status": "paid",
      "payment_status": "completed",
      "address": {
        "city": "Miami",
        "state": "FL",
        "zip": "33101",
        "country": "US"
      },
      "can_combine": true
    },
    "order_56": {
      "status": "paid",
      "payment_status": "completed",
      "address": {
        "city": "Miami",
        "state": "FL",
        "zip": "33102",  // ❌ Diferente ZIP code
        "country": "US"
      },
      "can_combine": false,
      "reason": "Different shipping address"
    }
  }
}
```

**Ejemplo de uso:**
```javascript
async function combineOrders(orderIds, notes = '') {
  try {
    const response = await fetch('/admin/orders/combine', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        order_ids: orderIds,
        notes: notes
      })
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      // Mostrar errores de validación
      if (result.error === 'validation_failed') {
        console.error('No se pueden combinar las órdenes:', result.details);
        // Mostrar en UI qué órdenes fallaron y por qué
      }
      throw new Error(result.message);
    }
    
    console.log('Órdenes combinadas exitosamente:', result.combined_group_id);
    return result;
  } catch (error) {
    console.error('Error al combinar órdenes:', error);
    throw error;
  }
}

// Uso
await combineOrders([55, 56, 57], 'Cliente VIP - Envío conjunto');
```

### 2. Separar Órdenes Combinadas

**Endpoint:** `POST /admin/orders/uncombine`

**Headers:**
```
Authorization: Bearer {admin_token}
Content-Type: application/json
```

**Body:**
```json
{
  "order_ids": [55, 56, 57]
}
```

**Validaciones:**
- ✅ Todas las órdenes deben estar en el mismo grupo combinado
- ✅ No se pueden separar si ya tienen shipments entregados (solo si están en tránsito o pendientes)

**Response:**
```json
{
  "success": true,
  "message": "Orders uncombined successfully",
  "uncombined_orders": [55, 56, 57]
}
```

**Ejemplo de uso:**
```javascript
async function uncombineOrders(orderIds) {
  const response = await fetch('/admin/orders/uncombine', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      order_ids: orderIds
    })
  });
  
  return await response.json();
}
```

### 3. Obtener Órdenes de un Grupo Combinado

**Endpoint:** `GET /admin/orders/combined/{combined_group_id}`

**Response:**
```json
{
  "combined_group_id": "cg_abc123xyz",
  "orders": [
    {
      "id": 55,
      "status": "shipped",
      "combined": true,
      "combined_group_id": "cg_abc123xyz",
      "combined_with": [56, 57],
      "total": 150.99,
      "created_at": "2026-01-01T10:00:00Z"
    },
    {
      "id": 56,
      "status": "shipped",
      "combined": true,
      "combined_group_id": "cg_abc123xyz",
      "combined_with": [55, 57],
      "total": 89.50,
      "created_at": "2026-01-01T11:00:00Z"
    },
    {
      "id": 57,
      "status": "shipped",
      "combined": true,
      "combined_group_id": "cg_abc123xyz",
      "combined_with": [55, 56],
      "total": 200.00,
      "created_at": "2026-01-01T12:00:00Z"
    }
  ],
  "shared_shipments": [
    {
      "id": 1,
      "tracking_number": "1Z999AA10123456784",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T10:00:00Z",
      "estimated_delivery": "2026-01-05T18:00:00Z",
      "delivered_at": null,
      "notes": "Paquete compartido para órdenes 55, 56, 57"
    }
  ]
}
```

### 4. Crear Shipments para Órdenes Combinadas

Cuando las órdenes están combinadas, crear un shipment para **cualquiera de las órdenes del grupo** automáticamente lo crea para **todas las órdenes del grupo**.

**Endpoint:** `POST /admin/orders/{order_id}/shipments`

**Ejemplo:**
```javascript
// Crear shipment para orden 55 (que está combinada con 56 y 57)
const response = await fetch('/admin/orders/55/shipments', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    tracking_number: '1Z999AA10123456784',
    carrier: 'UPS',
    shipped_at: new Date().toISOString()
  })
});

// Este shipment aparecerá automáticamente en:
// - GET /admin/orders/55/shipments
// - GET /admin/orders/56/shipments
// - GET /admin/orders/57/shipments
```

**⚠️ Importante:** 
- No necesitas crear el shipment para cada orden individualmente
- Un solo shipment creado se aplica a todas las órdenes del grupo
- Al marcar un shipment como entregado, todas las órdenes del grupo se marcan como "delivered"

### 5. Obtener Detalle de Orden (con información de combinación)

**Endpoint:** `GET /admin/orders/{order_id}`

**Response (cuando está combinada):**
```json
{
  "id": 55,
  "status": "shipped",
  "payment_status": "completed",
  "combined": true,
  "combined_group_id": "cg_abc123xyz",
  "combined_with": [56, 57],
  "shipments": [
    {
      "id": 1,
      "tracking_number": "1Z999AA10123456784",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T10:00:00Z",
      "delivered_at": null,
      "shared_with_orders": [55, 56, 57]
    }
  ],
  "total": 150.99,
  "created_at": "2026-01-01T10:00:00Z"
}
```

**Campos nuevos:**
- `combined`: `true` si la orden está combinada con otras
- `combined_group_id`: ID único del grupo de órdenes combinadas
- `combined_with`: Array de IDs de las otras órdenes con las que está combinada
- `shipments[].shared_with_orders`: Array de IDs de órdenes que comparten este shipment

---

## Para el Frontend (Cliente)

### 1. Obtener Detalle de Orden (con información de combinación)

**Endpoint:** `GET /checkout/orders/{order_id}`

**Response (cuando está combinada):**
```json
{
  "order_id": "55",
  "status": "shipped",
  "combined": true,
  "combined_with": [56, 57],
  "shipments": [
    {
      "id": 1,
      "tracking_number": "1Z999AA10123456784",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T10:00:00Z",
      "estimated_delivery": "2026-01-05T18:00:00Z",
      "delivered_at": null,
      "shared_with_orders": [55, 56, 57]
    }
  ],
  "total": 150.99,
  "items": [...],
  "address": {...}
}
```

**Campos nuevos:**
- `combined`: `true` si esta orden está combinada con otras
- `combined_with`: Array de IDs de otras órdenes del mismo usuario que están en el mismo envío
- `shipments[].shared_with_orders`: Array de IDs de órdenes que comparten este shipment

### 2. Listar Órdenes del Usuario

**Endpoint:** `GET /checkout/orders`

**Response:**
```json
[
  {
    "id": 55,
    "status": "shipped",
    "combined": true,
    "combined_with": [56, 57],
    "shipments": [
      {
        "id": 1,
        "tracking_number": "1Z999AA10123456784",
        "delivered_at": null,
        "status": "in_transit",
        "shared_with_orders": [55, 56, 57]
      }
    ]
  },
  {
    "id": 56,
    "status": "shipped",
    "combined": true,
    "combined_with": [55, 57],
    "shipments": [
      {
        "id": 1,
        "tracking_number": "1Z999AA10123456784",
        "delivered_at": null,
        "status": "in_transit",
        "shared_with_orders": [55, 56, 57]
      }
    ]
  },
  {
    "id": 57,
    "status": "shipped",
    "combined": true,
    "combined_with": [55, 56],
    "shipments": [
      {
        "id": 1,
        "tracking_number": "1Z999AA10123456784",
        "delivered_at": null,
        "status": "in_transit",
        "shared_with_orders": [55, 56, 57]
      }
    ]
  }
]
```

**⚠️ Nota importante:** 
- Si un usuario tiene múltiples órdenes combinadas, verá el mismo shipment en todas ellas
- El frontend debe manejar esto para no mostrar información duplicada o confusa

---

## Casos de Uso y Ejemplos

### Caso 1: Combinar órdenes nuevas

```javascript
// Escenario: Cliente hizo 3 pedidos separados pero quiere que se envíen juntos

// 1. Admin verifica que las órdenes pueden combinarse
const orders = await Promise.all([
  fetch('/admin/orders/55'),
  fetch('/admin/orders/56'),
  fetch('/admin/orders/57')
]);

// 2. Admin combina las órdenes
const result = await combineOrders([55, 56, 57], 'Cliente solicitó envío conjunto');

// 3. Admin crea shipments (solo necesita crear para una orden)
await createShipment(55, {
  tracking_number: '1Z999AA10123456784',
  carrier: 'UPS'
});

// 4. El shipment aparece automáticamente en las 3 órdenes
// GET /admin/orders/55/shipments → [shipment]
// GET /admin/orders/56/shipments → [shipment] (mismo)
// GET /admin/orders/57/shipments → [shipment] (mismo)
```

### Caso 2: Marcar shipment como entregado

```javascript
// Cuando se marca un shipment como entregado para una orden combinada,
// todas las órdenes del grupo se marcan automáticamente como "delivered"

await markShipmentAsDelivered(55, 1); // Marcar shipment #1 de orden 55

// Resultado automático:
// - Orden 55: status = "delivered"
// - Orden 56: status = "delivered"
// - Orden 57: status = "delivered"
// - Shipment #1: delivered_at = fecha actual
```

### Caso 3: Mostrar información combinada en UI

```javascript
function OrderCard({ order }) {
  return (
    <div className="order-card">
      <h3>Orden #{order.id}</h3>
      <p>Status: {order.status}</p>
      
      {order.combined && (
        <div className="combined-badge">
          <span>📦 Envío combinado con órdenes: {order.combined_with.join(', ')}</span>
        </div>
      )}
      
      <div className="shipments">
        {order.shipments.map(shipment => (
          <div key={shipment.id} className="shipment">
            <div>Tracking: {shipment.tracking_number}</div>
            {shipment.shared_with_orders && shipment.shared_with_orders.length > 1 && (
              <div className="shared-info">
                Compartido con órdenes: {shipment.shared_with_orders.join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Caso 4: Validar antes de combinar (Dashboard)

```javascript
async function validateOrdersForCombination(orderIds) {
  const orders = await Promise.all(
    orderIds.map(id => fetch(`/admin/orders/${id}`).then(r => r.json()))
  );
  
  const validation = {
    canCombine: true,
    errors: [],
    warnings: []
  };
  
  // Verificar que todas estén pagadas
  const unpaidOrders = orders.filter(o => 
    o.status !== 'paid' || o.payment_status !== 'completed'
  );
  if (unpaidOrders.length > 0) {
    validation.canCombine = false;
    validation.errors.push(
      `Órdenes no pagadas: ${unpaidOrders.map(o => o.id).join(', ')}`
    );
  }
  
  // Verificar direcciones
  const addresses = orders.map(o => ({
    id: o.id,
    address: o.address
  }));
  
  const firstAddress = addresses[0].address;
  const differentAddresses = addresses.filter(a => 
    a.address.city !== firstAddress.city ||
    a.address.state !== firstAddress.state ||
    a.address.zip !== firstAddress.zip ||
    a.address.country !== firstAddress.country
  );
  
  if (differentAddresses.length > 0) {
    validation.canCombine = false;
    validation.errors.push(
      `Órdenes con direcciones diferentes: ${differentAddresses.map(a => a.id).join(', ')}`
    );
  }
  
  // Verificar si ya tienen shipments
  const ordersWithShipments = orders.filter(o => 
    o.shipments && o.shipments.length > 0
  );
  if (ordersWithShipments.length > 0) {
    validation.canCombine = false;
    validation.errors.push(
      `Órdenes que ya tienen shipments: ${ordersWithShipments.map(o => o.id).join(', ')}`
    );
  }
  
  return validation;
}

// Uso
const validation = await validateOrdersForCombination([55, 56, 57]);
if (validation.canCombine) {
  await combineOrders([55, 56, 57]);
} else {
  console.error('No se pueden combinar:', validation.errors);
}
```

---

## Reglas de Negocio

### ✅ Se pueden combinar órdenes cuando:
1. Todas las órdenes están **pagadas** (`status: "paid"`, `payment_status: "completed"`)
2. Todas las órdenes tienen la **misma dirección de envío** (city, state, zip, country)
3. Ninguna orden tiene **shipments existentes** (deben estar sin enviar)
4. Ninguna orden está ya combinada con otro grupo

### ❌ No se pueden combinar órdenes cuando:
1. Alguna orden no está pagada
2. Las direcciones de envío son diferentes
3. Alguna orden ya tiene shipments creados
4. Alguna orden ya está combinada con otro grupo

### 🔄 Comportamiento de shipments compartidos:
1. **Crear shipment:** Crear un shipment para cualquier orden del grupo lo crea para todas
2. **Actualizar shipment:** Actualizar un shipment afecta a todas las órdenes del grupo
3. **Marcar como entregado:** Marcar un shipment como entregado marca todas las órdenes como "delivered"
4. **Eliminar shipment:** Eliminar un shipment lo elimina de todas las órdenes del grupo

### 🔓 Separar órdenes combinadas:
- Solo se pueden separar si los shipments están **pendientes** o **en tránsito**
- **No se pueden separar** si algún shipment ya fue entregado (`delivered_at` no es null)

---

## Estructura de Datos

### Tabla `combined_orders` (nueva)
```sql
CREATE TABLE combined_orders (
  id INTEGER PRIMARY KEY,
  combined_group_id TEXT UNIQUE NOT NULL,  -- "cg_abc123xyz"
  order_id INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id)
);
```

### Modificaciones a `orders`:
- `combined_group_id` (TEXT, nullable): ID del grupo si está combinada
- `combined` (BOOLEAN, default false): Flag rápido para saber si está combinada

### Modificaciones a `order_shipments`:
- `combined_group_id` (TEXT, nullable): ID del grupo para el que se creó este shipment
- Cuando `combined_group_id` no es null, el shipment se aplica a todas las órdenes del grupo

---

## Flujo Completo de Ejemplo

### 1. Cliente hace 3 pedidos separados
```
Orden #55: $150.99 - Dirección: Miami, FL 33101
Orden #56: $89.50  - Dirección: Miami, FL 33101
Orden #57: $200.00 - Dirección: Miami, FL 33101
```

### 2. Admin combina las órdenes
```javascript
POST /admin/orders/combine
{
  "order_ids": [55, 56, 57],
  "notes": "Cliente VIP - Envío conjunto"
}

Response:
{
  "combined_group_id": "cg_abc123xyz",
  "orders": [55, 56, 57]
}
```

### 3. Admin crea shipments (solo para una orden)
```javascript
POST /admin/orders/55/shipments
{
  "tracking_number": "1Z999AA10123456784",
  "carrier": "UPS"
}

// Este shipment aparece automáticamente en:
// - GET /admin/orders/55/shipments → [shipment]
// - GET /admin/orders/56/shipments → [shipment]
// - GET /admin/orders/57/shipments → [shipment]
```

### 4. Cliente consulta sus órdenes
```javascript
GET /checkout/orders

Response:
[
  {
    "id": 55,
    "combined": true,
    "combined_with": [56, 57],
    "shipments": [
      {
        "tracking_number": "1Z999AA10123456784",
        "shared_with_orders": [55, 56, 57]
      }
    ]
  },
  // ... órdenes 56 y 57 con la misma información
]
```

### 5. Admin marca shipment como entregado
```javascript
PATCH /admin/orders/55/shipments/1
{
  "delivered_at": "2026-01-05T15:30:00Z"
}

// Resultado automático:
// - Orden 55: status = "delivered"
// - Orden 56: status = "delivered"
// - Orden 57: status = "delivered"
```

---

## Notas Importantes para el Frontend

1. **Campo `combined`**: Siempre verifica este campo antes de mostrar información de combinación
2. **Campo `combined_with`**: Muestra qué otras órdenes están en el mismo envío
3. **Campo `shared_with_orders` en shipments**: Indica qué órdenes comparten este shipment
4. **UI/UX**: Considera mostrar un badge o indicador visual cuando una orden está combinada
5. **Evitar duplicación**: Si un usuario tiene múltiples órdenes combinadas, considera agruparlas visualmente en la UI

---

## Notas Importantes para el Dashboard Admin

1. **Validación previa**: Siempre valida que las órdenes pueden combinarse antes de intentar combinarlas
2. **Crear shipments**: Solo necesitas crear shipments para una orden del grupo, se aplican a todas
3. **Separar órdenes**: Solo se pueden separar si no hay shipments entregados
4. **Tracking**: Los shipments compartidos tienen el mismo tracking number para todas las órdenes
5. **Notificaciones**: Considera notificar al cliente cuando se combinan sus órdenes

---

## Endpoints Resumen

### Dashboard Admin:
- `POST /admin/orders/combine` - Combinar órdenes
- `POST /admin/orders/uncombine` - Separar órdenes combinadas
- `GET /admin/orders/combined/{combined_group_id}` - Obtener órdenes de un grupo
- `GET /admin/orders/{order_id}` - Obtener orden (incluye info de combinación)
- `POST /admin/orders/{order_id}/shipments` - Crear shipment (se aplica a todas si está combinada)

### Frontend Cliente:
- `GET /checkout/orders` - Listar órdenes (incluye info de combinación)
- `GET /checkout/orders/{order_id}` - Obtener orden (incluye info de combinación)

---

## Preguntas Frecuentes

**P: ¿Puedo combinar órdenes de diferentes clientes?**
R: No, el sistema solo permite combinar órdenes que tengan la misma dirección de envío. Si son de diferentes clientes pero tienen la misma dirección, técnicamente se pueden combinar, pero esto no es recomendado.

**P: ¿Qué pasa si una orden combinada se cancela?**
R: Si una orden se cancela, se debe separar del grupo primero. Las órdenes canceladas no pueden estar combinadas.

**P: ¿Puedo agregar más órdenes a un grupo existente?**
R: Por ahora, no. Debes separar el grupo y crear uno nuevo con todas las órdenes que quieras combinar.

**P: ¿Los shipments compartidos tienen el mismo costo de envío?**
R: Sí, todos los shipments compartidos tienen el mismo tracking y se envían juntos, por lo que el costo es el mismo para todas las órdenes del grupo.

**P: ¿Cómo se calcula el costo de envío para órdenes combinadas?**
R: El costo de envío se calcula basado en el peso total de todas las órdenes combinadas, pero se divide entre las órdenes según su peso relativo (o según la política de negocio).

