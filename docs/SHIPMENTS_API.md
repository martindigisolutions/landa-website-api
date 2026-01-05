# API de Shipments (Paquetes) para Órdenes

## Resumen

El sistema permite que una orden tenga múltiples paquetes/envíos, cada uno con su propio tracking number. Esto es útil cuando una orden grande se divide en varios envíos.

---

## Para el Dashboard Admin

### 1. Crear un Shipment (Paquete) para una Orden

**Endpoint:** `POST /admin/orders/{order_id}/shipments`

**Headers:**
```
Authorization: Bearer {admin_token}
```

**Body:**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
  "carrier": "UPS",
  "shipped_at": "2026-01-02T10:00:00Z",
  "estimated_delivery": "2026-01-05T18:00:00Z",
  "notes": "Paquete 1 de 2 - Productos pesados"
}
```

**Campos:**
- `tracking_number` (requerido): Número de tracking del paquete
- `tracking_url` (opcional): URL completa para rastrear el paquete
- `carrier` (opcional): Nombre de la transportista (UPS, FedEx, USPS, DHL, etc.)
- `shipped_at` (opcional): Fecha y hora en que se envió el paquete
- `estimated_delivery` (opcional): Fecha estimada de entrega
- `notes` (opcional): Notas adicionales sobre este paquete

**Ejemplo de uso (crear un solo paquete):**
```javascript
await fetch('/admin/orders/123/shipments', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    tracking_number: '1Z999AA10123456784',
    tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456784',
    carrier: 'UPS',
    shipped_at: new Date().toISOString(),
    estimated_delivery: '2026-01-05T18:00:00Z',
    notes: 'Paquete 1 de 2'
  })
});
```

### 1.1. Crear Múltiples Shipments (Bulk) - RECOMENDADO

**Endpoint:** `POST /admin/orders/{order_id}/shipments/bulk`

**Headers:**
```
Authorization: Bearer {admin_token}
```

**Body:**
```json
{
  "shipments": [
    {
      "tracking_number": "1Z999AA10123456784",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T10:00:00Z",
      "estimated_delivery": "2026-01-05T18:00:00Z",
      "notes": "Paquete 1 de 5"
    },
    {
      "tracking_number": "1Z999AA10123456785",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456785",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T11:00:00Z",
      "estimated_delivery": "2026-01-06T18:00:00Z",
      "notes": "Paquete 2 de 5"
    },
    {
      "tracking_number": "1Z999AA10123456786",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456786",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T12:00:00Z",
      "estimated_delivery": "2026-01-07T18:00:00Z",
      "notes": "Paquete 3 de 5"
    },
    {
      "tracking_number": "1Z999AA10123456787",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456787",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T13:00:00Z",
      "estimated_delivery": "2026-01-08T18:00:00Z",
      "notes": "Paquete 4 de 5"
    },
    {
      "tracking_number": "1Z999AA10123456788",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456788",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T14:00:00Z",
      "estimated_delivery": "2026-01-09T18:00:00Z",
      "notes": "Paquete 5 de 5"
    }
  ]
}
```

**Response:**
```json
[
  {
    "id": 1,
    "order_id": 123,
    "tracking_number": "1Z999AA10123456784",
    "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
    "carrier": "UPS",
    "shipped_at": "2026-01-02T10:00:00Z",
    "estimated_delivery": "2026-01-05T18:00:00Z",
    "notes": "Paquete 1 de 5",
    "created_at": "2026-01-02T10:00:00Z",
    "updated_at": "2026-01-02T10:00:00Z"
  },
  {
    "id": 2,
    "order_id": 123,
    "tracking_number": "1Z999AA10123456785",
    ...
  }
  // ... resto de shipments
]
```

**Ejemplo de uso (crear múltiples paquetes de una vez):**
```javascript
// Cuando el admin prepara una orden y la divide en 5 paquetes
// Usa el endpoint bulk para crear todos en una sola llamada

await fetch('/admin/orders/123/shipments/bulk', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    shipments: [
      {
        tracking_number: '1Z999AA10123456784',
        tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456784',
        carrier: 'UPS',
        shipped_at: new Date().toISOString(),
        estimated_delivery: '2026-01-05T18:00:00Z',
        notes: 'Paquete 1 de 5'
      },
      {
        tracking_number: '1Z999AA10123456785',
        tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456785',
        carrier: 'UPS',
        shipped_at: new Date().toISOString(),
        estimated_delivery: '2026-01-06T18:00:00Z',
        notes: 'Paquete 2 de 5'
      },
      {
        tracking_number: '1Z999AA10123456786',
        tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456786',
        carrier: 'UPS',
        shipped_at: new Date().toISOString(),
        estimated_delivery: '2026-01-07T18:00:00Z',
        notes: 'Paquete 3 de 5'
      },
      {
        tracking_number: '1Z999AA10123456787',
        tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456787',
        carrier: 'UPS',
        shipped_at: new Date().toISOString(),
        estimated_delivery: '2026-01-08T18:00:00Z',
        notes: 'Paquete 4 de 5'
      },
      {
        tracking_number: '1Z999AA10123456788',
        tracking_url: 'https://www.ups.com/track?tracknum=1Z999AA10123456788',
        carrier: 'UPS',
        shipped_at: new Date().toISOString(),
        estimated_delivery: '2026-01-09T18:00:00Z',
        notes: 'Paquete 5 de 5'
      }
    ]
  })
});
```

### 2. Listar todos los Shipments de una Orden

**Endpoint:** `GET /admin/orders/{order_id}/shipments`

**Response:**
```json
[
  {
    "id": 1,
    "order_id": 123,
    "tracking_number": "1Z999AA10123456784",
    "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
    "carrier": "UPS",
    "shipped_at": "2026-01-02T10:00:00Z",
    "estimated_delivery": "2026-01-05T18:00:00Z",
    "delivered_at": "2026-01-05T15:30:00Z",
    "notes": "Paquete 1 de 2",
    "created_at": "2026-01-02T10:00:00Z",
    "updated_at": "2026-01-05T15:30:00Z"
  },
  {
    "id": 2,
    "order_id": 123,
    "tracking_number": "1Z999AA10123456785",
    "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456785",
    "carrier": "UPS",
    "shipped_at": "2026-01-02T11:00:00Z",
    "estimated_delivery": "2026-01-06T18:00:00Z",
    "delivered_at": null,
    "notes": "Paquete 2 de 2",
    "created_at": "2026-01-02T11:00:00Z",
    "updated_at": "2026-01-02T11:00:00Z"
  }
]
```

**Campos del Response:**
- `delivered_at`: `null` si el paquete no ha sido entregado, o una fecha/hora ISO 8601 si ya fue entregado.

### 3. Actualizar un Shipment

**Endpoint:** `PATCH /admin/orders/{order_id}/shipments/{shipment_id}`

**Body (todos los campos son opcionales):**
```json
{
  "tracking_number": "1Z999AA10123456784",
  "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
  "carrier": "UPS",
  "shipped_at": "2026-01-02T10:00:00Z",
  "estimated_delivery": "2026-01-05T18:00:00Z",
  "delivered_at": "2026-01-05T15:30:00Z",
  "notes": "Paquete entregado al cliente"
}
```

**Campos importantes:**
- `delivered_at` (opcional): Fecha y hora en que el paquete fue entregado. **Si se establece, el sistema automáticamente verificará si todos los shipments de la orden están entregados y marcará la orden como "delivered" si es así.**
- Para marcar como entregado ahora mismo, puedes enviar `null` o la fecha actual en formato ISO 8601.

**Ejemplo: Marcar un paquete como entregado**
```javascript
// Opción 1: Marcar como entregado con fecha/hora actual
await fetch(`/admin/orders/123/shipments/1`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    delivered_at: new Date().toISOString()
  })
});

// Opción 2: Marcar como entregado con una fecha específica
await fetch(`/admin/orders/123/shipments/1`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${adminToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    delivered_at: '2026-01-05T15:30:00Z'
  })
});
```

**Response:**
```json
{
  "id": 1,
  "order_id": 123,
  "tracking_number": "1Z999AA10123456784",
  "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
  "carrier": "UPS",
  "shipped_at": "2026-01-02T10:00:00Z",
  "estimated_delivery": "2026-01-05T18:00:00Z",
  "delivered_at": "2026-01-05T15:30:00Z",
  "notes": "Paquete entregado al cliente",
  "created_at": "2026-01-02T10:00:00Z",
  "updated_at": "2026-01-05T15:30:00Z"
}
```

**⚠️ Comportamiento automático:**
- Cuando marcas un shipment como entregado (`delivered_at` no es `null`), el sistema verifica automáticamente si **todos los shipments** de esa orden están entregados.
- Si todos los shipments están entregados, la orden se marca automáticamente como `"delivered"`.
- Esto significa que no necesitas actualizar manualmente el status de la orden cuando todos los paquetes están entregados.

### 4. Eliminar un Shipment

**Endpoint:** `DELETE /admin/orders/{order_id}/shipments/{shipment_id}`

**Response:**
```json
{
  "success": true,
  "message": "Shipment deleted successfully"
}
```

---

## Para el Frontend (Cliente)

### 1. Listar Órdenes del Usuario

**Endpoint:** `GET /checkout/orders`

**Headers:**
```
Authorization: Bearer {user_token}
```

**Response:**
```json
[
  {
    "id": 123,
    "status": "shipped",
    "payment_method": "stripe",
    "shipping_method": "standard",
    "total": 150.99,
    "created_at": "2026-01-01T10:00:00Z",
    "shipments": [
      {
        "id": 1,
        "tracking_number": "1Z999AA10123456784",
        "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
        "carrier": "UPS",
        "shipped_at": "2026-01-02T10:00:00Z",
        "delivered_at": "2026-01-05T15:30:00Z",
        "status": "delivered"
      },
      {
        "id": 2,
        "tracking_number": "1Z999AA10123456785",
        "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456785",
        "carrier": "UPS",
        "shipped_at": "2026-01-02T11:00:00Z",
        "delivered_at": null,
        "status": "in_transit"
      }
    ]
  }
]
```

### 2. Obtener Detalle de una Orden

**Endpoint:** `GET /checkout/orders/{order_id}`

**Headers:**
```
Authorization: Bearer {user_token}
```

**Response:**
```json
{
  "order_id": "123",
  "status": "shipped",
  "total": 150.99,
  "subtotal": 145.00,
  "shipping_cost": 5.99,
  "tax": 0.00,
  "items": [
    {
      "product_id": 1,
      "variant_id": 5,
      "product_name": "Tinte Profesional",
      "variant_name": "Rubio Claro",
      "quantity": 2,
      "price": 25.00,
      "image_url": "https://..."
    }
  ],
  "address": {
    "city": "Miami",
    "state": "FL",
    "zip": "33101",
    "country": "US",
    "street": "123 Main St",
    "apartment": "Apt 4B"
  },
  "shipping_method": "standard",
  "payment_method": "stripe",
  "shipments": [
    {
      "id": 1,
      "tracking_number": "1Z999AA10123456784",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T10:00:00Z",
      "estimated_delivery": "2026-01-05T18:00:00Z",
      "delivered_at": "2026-01-05T15:30:00Z",
      "notes": "Paquete 1 de 2"
    },
    {
      "id": 2,
      "tracking_number": "1Z999AA10123456785",
      "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456785",
      "carrier": "UPS",
      "shipped_at": "2026-01-02T11:00:00Z",
      "estimated_delivery": "2026-01-06T18:00:00Z",
      "notes": "Paquete 2 de 2"
    }
  ],
  "created_at": "2026-01-01T10:00:00Z"
}
```

---

## Notas Importantes

1. **Múltiples Paquetes:** Una orden puede tener múltiples shipments. El frontend debe mostrar todos los paquetes con sus respectivos tracking numbers.

2. **Campos Deprecados:** Los campos `tracking_number`, `tracking_url`, y `shipped_at` en el nivel de `Order` están deprecados pero se mantienen para compatibilidad. El frontend debe usar el array `shipments` en su lugar.

3. **Orden de Shipments:** Los shipments se devuelven ordenados por fecha de creación (más antiguos primero).

4. **Estado de Orden:** Cuando se crea el primer shipment, el estado de la orden se actualiza automáticamente a "shipped" si no estaba ya en ese estado.

5. **Eliminación de Shipments:** Si se elimina el último shipment de una orden con estado "shipped", el estado de la orden se revierte a "processing".

---

## Ejemplo de Flujo Completo

1. **Admin prepara la orden:**
   - Orden #123 está en estado "processing"
   - Admin divide la orden en 2 paquetes
   - Admin crea shipment #1 con tracking "1Z999AA10123456784"
   - Admin crea shipment #2 con tracking "1Z999AA10123456785"
   - Estado de orden cambia automáticamente a "shipped"

2. **Cliente consulta su orden:**
   - Cliente hace `GET /checkout/orders/123`
   - Recibe la orden con array `shipments` que contiene ambos paquetes
   - Frontend muestra ambos tracking numbers con sus respectivos links

3. **Cliente rastrea sus paquetes:**
   - Frontend muestra cada shipment con su tracking number
   - Cada tracking number es clickeable y lleva al tracking_url correspondiente

4. **Admin marca paquete como entregado:**
   - Admin hace `PATCH /admin/orders/123/shipments/1` con `delivered_at`
   - Si todos los shipments están entregados, la orden se marca automáticamente como "delivered"

---

## 📋 Guía para el Frontend: Manejo de Estados de Entrega

### Estados de un Shipment

Un shipment puede tener los siguientes estados basados en sus campos:

| Estado | Condición | `delivered_at` | `shipped_at` | `status` (en ShipmentInfo) |
|--------|-----------|----------------|--------------|----------------------------|
| **Pending** | No se ha enviado | `null` | `null` | `"pending"` |
| **In Transit** | Enviado pero no entregado | `null` | ✅ Tiene valor | `"in_transit"` |
| **Delivered** | Entregado al cliente | ✅ Tiene valor | ✅ Tiene valor | `"delivered"` |

### Casos de Uso Comunes

#### 1. Verificar si un shipment está entregado

```javascript
function isShipmentDelivered(shipment) {
  return shipment.delivered_at !== null && shipment.delivered_at !== undefined;
}

// Uso
const shipment = {
  id: 1,
  tracking_number: "1Z999AA10123456784",
  delivered_at: "2026-01-05T15:30:00Z"
};

if (isShipmentDelivered(shipment)) {
  console.log("Paquete entregado el:", shipment.delivered_at);
} else {
  console.log("Paquete aún en tránsito");
}
```

#### 2. Verificar si todos los shipments de una orden están entregados

```javascript
function areAllShipmentsDelivered(shipments) {
  if (!shipments || shipments.length === 0) {
    return false;
  }
  return shipments.every(shipment => 
    shipment.delivered_at !== null && shipment.delivered_at !== undefined
  );
}

// Uso
const order = {
  id: 123,
  status: "shipped",
  shipments: [
    { id: 1, delivered_at: "2026-01-05T15:30:00Z" },
    { id: 2, delivered_at: null }
  ]
};

if (areAllShipmentsDelivered(order.shipments)) {
  console.log("Todos los paquetes entregados");
  // La orden debería tener status "delivered" automáticamente
} else {
  console.log("Algunos paquetes aún en tránsito");
}
```

#### 3. Mostrar el estado de entrega en la UI

```javascript
function getShipmentStatus(shipment) {
  if (shipment.delivered_at) {
    return {
      label: "Entregado",
      color: "green",
      icon: "check-circle",
      date: shipment.delivered_at
    };
  } else if (shipment.shipped_at) {
    return {
      label: "En Tránsito",
      color: "blue",
      icon: "truck",
      estimatedDelivery: shipment.estimated_delivery
    };
  } else {
    return {
      label: "Pendiente",
      color: "gray",
      icon: "clock"
    };
  }
}
```

#### 4. Marcar un shipment como entregado (Dashboard Admin)

```javascript
async function markShipmentAsDelivered(orderId, shipmentId) {
  try {
    const response = await fetch(
      `/admin/orders/${orderId}/shipments/${shipmentId}`,
      {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${adminToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          delivered_at: new Date().toISOString()
        })
      }
    );
    
    if (!response.ok) {
      throw new Error('Error al marcar como entregado');
    }
    
    const updatedShipment = await response.json();
    
    // Verificar si todos los shipments están entregados
    const orderResponse = await fetch(`/admin/orders/${orderId}`, {
      headers: {
        'Authorization': `Bearer ${adminToken}`
      }
    });
    const order = await orderResponse.json();
    
    if (order.status === 'delivered') {
      console.log('¡Todos los paquetes entregados! La orden se marcó automáticamente como entregada.');
    }
    
    return updatedShipment;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

#### 5. Contar shipments entregados vs pendientes

```javascript
function getShipmentStats(shipments) {
  const total = shipments.length;
  const delivered = shipments.filter(s => s.delivered_at !== null).length;
  const inTransit = shipments.filter(s => 
    s.shipped_at !== null && s.delivered_at === null
  ).length;
  const pending = shipments.filter(s => s.shipped_at === null).length;
  
  return {
    total,
    delivered,
    inTransit,
    pending,
    deliveryProgress: total > 0 ? (delivered / total) * 100 : 0
  };
}

// Uso
const stats = getShipmentStats(order.shipments);
console.log(`${stats.delivered}/${stats.total} paquetes entregados`);
console.log(`Progreso: ${stats.deliveryProgress.toFixed(0)}%`);
```

#### 6. Formatear fecha de entrega para mostrar

```javascript
function formatDeliveryDate(deliveredAt) {
  if (!deliveredAt) return null;
  
  const date = new Date(deliveredAt);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return "Hoy";
  } else if (diffDays === 1) {
    return "Ayer";
  } else if (diffDays < 7) {
    return `Hace ${diffDays} días`;
  } else {
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }
}
```

### ⚠️ Notas Importantes para el Frontend

1. **Campo `delivered_at`**:
   - Si es `null` o `undefined`, el paquete NO ha sido entregado
   - Si tiene un valor (fecha ISO 8601), el paquete FUE entregado en esa fecha/hora

2. **Actualización automática del status de la orden**:
   - Cuando marcas un shipment como entregado, el backend verifica automáticamente si todos los shipments están entregados
   - Si todos están entregados, la orden se marca automáticamente como `"delivered"`
   - **No necesitas actualizar manualmente el status de la orden**

3. **Campo `status` en `ShipmentInfo`** (solo en endpoints de checkout):
   - Se calcula automáticamente: `"delivered"`, `"in_transit"`, o `"pending"`
   - Es solo informativo, no lo uses para lógica crítica
   - Siempre verifica `delivered_at` para determinar si está entregado

4. **Múltiples shipments**:
   - Una orden puede tener múltiples shipments
   - Cada shipment se entrega independientemente
   - La orden solo se marca como `"delivered"` cuando TODOS los shipments están entregados

5. **Formato de fechas**:
   - Todas las fechas vienen en formato ISO 8601: `"2026-01-05T15:30:00Z"`
   - Usa `new Date(dateString)` para convertir a objeto Date en JavaScript
   - Siempre valida que la fecha no sea `null` antes de formatear

