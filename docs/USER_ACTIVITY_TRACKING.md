# Sistema de Tracking de Actividades de Usuarios

## 📋 Descripción General

El sistema de tracking de actividades captura automáticamente todas las acciones que realizan los usuarios en la plataforma. Esto permite a los administradores:

- Ver qué usuarios están más activos
- Analizar el comportamiento de navegación
- Entender qué productos buscan los usuarios
- Ver los carritos de los usuarios
- Auditar acciones importantes (checkouts, pagos, etc.)

**El sistema funciona automáticamente** - no requiere configuración adicional. Cada vez que un usuario hace una acción (buscar productos, agregar al carrito, hacer checkout, etc.), se registra automáticamente.

---

## 🔐 Autenticación

Todos los endpoints requieren autenticación OAuth2 con el scope apropiado:

- `users:read` - Para ver actividades y carritos de usuarios
- `orders:read` - Para ver todos los carritos del sistema

**Ejemplo de autenticación:**
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## 📊 Endpoints Disponibles

### 1. Listar Usuarios por Última Actividad

Obtiene una lista paginada de usuarios ordenados por su última actividad (más recientes primero).

**Endpoint:** `GET /admin/users/by-activity`

**Query Parameters:**
- `page` (opcional, default: 1) - Número de página
- `page_size` (opcional, default: 20, máximo: 100) - Elementos por página
- `search` (opcional) - Buscar por email, teléfono o nombre

**Ejemplo de Request:**
```http
GET /admin/users/by-activity?page=1&page_size=20&search=juan
Authorization: Bearer YOUR_TOKEN
```

**Ejemplo de Response:**
```json
{
  "results": [
    {
      "user": {
        "id": 1,
        "email": "juan@example.com",
        "phone": "+1234567890",
        "first_name": "Juan",
        "last_name": "Pérez",
        "user_type": "client",
        "created_at": "2024-01-15T10:30:00",
        "is_blocked": false,
        "is_suspended": false
      },
      "last_activity_at": "2024-01-20T15:45:30",
      "total_activities": 156
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3
  }
}
```

**Casos de Uso:**
- Ver qué usuarios están activos recientemente
- Identificar usuarios inactivos
- Buscar usuarios específicos para análisis

---

### 2. Ver Actividades de un Usuario

Obtiene todas las actividades de un usuario específico con paginación y filtros.

**Endpoint:** `GET /admin/users/{user_id}/activities`

**Path Parameters:**
- `user_id` (requerido) - ID del usuario

**Query Parameters:**
- `page` (opcional, default: 1) - Número de página
- `page_size` (opcional, default: 50, máximo: 100) - Elementos por página
- `action_type` (opcional) - Filtrar por tipo de acción (ej: "search_products", "add_to_cart", "checkout")
- `start_date` (opcional) - Fecha de inicio en formato ISO (ej: "2024-01-15T00:00:00")
- `end_date` (opcional) - Fecha de fin en formato ISO (ej: "2024-01-20T23:59:59")

**Tipos de Acciones Comunes:**
- `view_products` - Ver lista de productos
- `search_products` - Buscar productos
- `view_product_detail` - Ver detalle de producto
- `add_to_cart` - Agregar producto al carrito
- `update_cart_item` - Actualizar cantidad en carrito
- `remove_from_cart` - Eliminar del carrito
- `view_cart` - Ver carrito
- `initiate_checkout` - Iniciar checkout
- `complete_checkout` - Completar checkout
- `create_payment_intent` - Crear intención de pago
- `confirm_payment` - Confirmar pago
- `login` - Iniciar sesión
- `register` - Registrarse

**Ejemplo de Request:**
```http
GET /admin/users/1/activities?page=1&page_size=50&action_type=search_products&start_date=2024-01-15T00:00:00
Authorization: Bearer YOUR_TOKEN
```

**Ejemplo de Response:**
```json
{
  "results": [
    {
      "id": 1234,
      "method": "GET",
      "endpoint": "/products",
      "action_type": "search_products",
      "metadata": {
        "search_query": "tinte rubio",
        "filters": {
          "categories": ["tintes"],
          "min_price": "10"
        },
        "page": 1,
        "page_size": 20
      },
      "query_params": {
        "search": "tinte rubio",
        "category": "tintes",
        "min_price": "10",
        "page": "1"
      },
      "response_status": 200,
      "ip_address": "192.168.1.1",
      "created_at": "2024-01-20T15:45:30"
    },
    {
      "id": 1233,
      "method": "POST",
      "endpoint": "/cart/add",
      "action_type": "add_to_cart",
      "metadata": {
        "product_id": 42,
        "variant_id": 15,
        "quantity": 2
      },
      "query_params": {},
      "request_body": {
        "product_id": 42,
        "variant_id": 15,
        "quantity": 2
      },
      "response_status": 200,
      "ip_address": "192.168.1.1",
      "created_at": "2024-01-20T15:43:15"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 156,
    "total_pages": 4
  }
}
```

**Casos de Uso:**
- Analizar el comportamiento de un usuario específico
- Ver qué productos busca un usuario
- Entender el flujo de compra de un usuario
- Auditar acciones sospechosas
- Ver historial completo de interacciones

---

### 3. Ver Carritos de un Usuario

Obtiene todos los carritos (actuales e históricos) de un usuario específico.

**Endpoint:** `GET /admin/users/{user_id}/carts`

**Path Parameters:**
- `user_id` (requerido) - ID del usuario

**Query Parameters:**
- `include_inactive` (opcional, default: false) - Incluir carritos vacíos o antiguos

**Ejemplo de Request:**
```http
GET /admin/users/1/carts?include_inactive=false
Authorization: Bearer YOUR_TOKEN
```

**Ejemplo de Response:**
```json
[
  {
    "id": 10,
    "user_id": 1,
    "session_id": null,
    "items": [
      {
        "id": 25,
        "product_id": 42,
        "product_name": "Tinte Rubio #8",
        "variant_id": 15,
        "variant_name": "500ml",
        "quantity": 2,
        "unit_price": 29.99,
        "line_total": 59.98,
        "added_at": "2024-01-20T15:43:15"
      }
    ],
    "summary": {
      "items_count": 1,
      "total_items": 2,
      "subtotal": 59.98
    },
    "shipping": {
      "first_name": "Juan",
      "last_name": "Pérez",
      "phone": "+1234567890",
      "email": "juan@example.com",
      "street": "123 Main St",
      "city": "Miami",
      "state": "FL",
      "zipcode": "33101",
      "country": "US",
      "is_pickup": false
    },
    "payment_method": "stripe",
    "created_at": "2024-01-20T14:30:00",
    "updated_at": "2024-01-20T15:45:30"
  }
]
```

**Casos de Uso:**
- Ver qué tiene un usuario en su carrito actual
- Revisar carritos históricos
- Entender el proceso de compra
- Ver dirección de envío guardada

---

### 4. Listar Todos los Carritos

Obtiene una lista paginada de todos los carritos del sistema.

**Endpoint:** `GET /admin/carts`

**Query Parameters:**
- `page` (opcional, default: 1) - Número de página
- `page_size` (opcional, default: 20, máximo: 100) - Elementos por página
- `user_id` (opcional) - Filtrar por usuario específico
- `has_items` (opcional) - Filtrar carritos con/sin items (true/false)
- `sort_by` (opcional, default: "updated_at") - Ordenar por:
  - `"updated_at"` - Por fecha de actualización (más recientes primero) - **por defecto**
  - `"created_at"` - Por fecha de creación (más recientes primero)
  - `"user_email"` - Alfabéticamente por email del usuario
  - `"user_name"` - Alfabéticamente por nombre del usuario

**Ejemplo de Request:**
```http
GET /admin/carts?page=1&page_size=20&has_items=true&sort_by=user_email
Authorization: Bearer YOUR_TOKEN
```

**Nota:** Los carritos están ordenados por defecto por fecha de actualización (más recientes primero). Puedes cambiar el ordenamiento usando el parámetro `sort_by`.

**Ejemplo de Response:**
```json
{
  "results": [
    {
      "id": 10,
      "user_id": 1,
      "session_id": null,
      "user": {
        "id": 1,
        "email": "juan@example.com",
        "phone": "+1234567890",
        "first_name": "Juan",
        "last_name": "Pérez"
      },
      "items_count": 3,
      "payment_method": "stripe",
      "is_pickup": false,
      "created_at": "2024-01-20T14:30:00",
      "updated_at": "2024-01-20T15:45:30"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3
  }
}
```

**Casos de Uso:**
- Ver todos los carritos activos en el sistema
- Monitorear carritos abandonados
- Analizar patrones de compra
- Identificar carritos que necesitan atención

---

### 5. Ver Detalle de un Carrito

Obtiene información detallada de un carrito específico incluyendo todos sus items.

**Endpoint:** `GET /admin/carts/{cart_id}`

**Path Parameters:**
- `cart_id` (requerido) - ID del carrito

**Ejemplo de Request:**
```http
GET /admin/carts/10
Authorization: Bearer YOUR_TOKEN
```

**Ejemplo de Response:**
```json
{
  "id": 10,
  "user_id": 1,
  "session_id": null,
  "items": [
    {
      "id": 25,
      "product_id": 42,
      "product_name": "Tinte Rubio #8",
      "variant_id": 15,
      "variant_name": "500ml",
      "quantity": 2,
      "unit_price": 29.99,
      "line_total": 59.98,
      "added_at": "2024-01-20T15:43:15"
    },
    {
      "id": 26,
      "product_id": 50,
      "product_name": "Shampoo Profesional",
      "variant_id": null,
      "variant_name": null,
      "quantity": 1,
      "unit_price": 15.99,
      "line_total": 15.99,
      "added_at": "2024-01-20T16:00:00"
    }
  ],
  "summary": {
    "items_count": 2,
    "total_items": 3,
    "subtotal": 75.97
  },
  "shipping": {
    "first_name": "Juan",
    "last_name": "Pérez",
    "phone": "+1234567890",
    "email": "juan@example.com",
    "street": "123 Main St",
    "city": "Miami",
    "state": "FL",
    "zipcode": "33101",
    "country": "US",
    "is_pickup": false
  },
  "payment_method": "stripe",
  "created_at": "2024-01-20T14:30:00",
  "updated_at": "2024-01-20T16:00:00"
}
```

**Casos de Uso:**
- Ver detalle completo de un carrito específico
- Analizar contenido de carritos abandonados
- Verificar información de envío guardada

---

## 🔍 Casos de Uso Comunes

### Analizar el Comportamiento de un Usuario

1. Lista usuarios activos: `GET /admin/users/by-activity`
2. Selecciona un usuario y obtén sus actividades: `GET /admin/users/{user_id}/activities`
3. Filtra por tipo de acción para ver patrones específicos (ej: todas las búsquedas)

### Investigar un Carrito Abandonado

1. Lista todos los carritos: `GET /admin/carts?has_items=true`
2. Ordena por `updated_at` para ver los más recientes
3. Obtén el detalle del carrito: `GET /admin/carts/{cart_id}`
4. Revisa las actividades del usuario: `GET /admin/users/{user_id}/activities?action_type=view_cart`

### Entender Búsquedas Populares

1. Obtén actividades de tipo "search_products": `GET /admin/users/{user_id}/activities?action_type=search_products`
2. Analiza el campo `metadata.search_query` para ver términos de búsqueda

### Auditar Proceso de Checkout

1. Filtra actividades por "initiate_checkout" y "complete_checkout"
2. Compara timestamps para ver cuánto tiempo tarda un usuario en completar el checkout
3. Revisa los carritos asociados para entender el contenido

---

## 📝 Notas Importantes

### Datos Sensibles

El sistema sanitiza automáticamente datos sensibles:
- Contraseñas y hashes se reemplazan con `***REDACTED***`
- Tokens y secretos no se guardan
- Información de tarjetas de crédito no se almacena

### Performance

- Las actividades se guardan de forma asíncrona (no afectan el rendimiento de las requests)
- Los endpoints tienen paginación para manejar grandes volúmenes de datos
- Se recomienda usar filtros (`action_type`, fechas) para consultas más eficientes

### Límites

- `page_size` máximo: 100 elementos por página
- Las actividades se guardan indefinidamente (considera implementar rotación periódica si es necesario)

---

## 🆘 Soporte

Si tienes preguntas o encuentras algún problema con estos endpoints, contacta al equipo de desarrollo.

**Última actualización:** Enero 2025

