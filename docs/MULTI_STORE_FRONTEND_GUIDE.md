# Multi-Store API Changes for Frontend

Este documento describe los cambios en la API para soportar **Wholesale** y **Retail** como tiendas separadas.

---

## Resumen

La API ahora soporta dos modos de operación controlados por la variable `STORE_MODE`:

| Modo | Descripción |
|------|-------------|
| `wholesale` | Tienda mayorista (comportamiento actual) |
| `retail` | Tienda minorista (nueva) |

**Mismo código de API, diferente comportamiento según el modo.**

---

## Diferencias entre Wholesale y Retail

| Aspecto | Wholesale | Retail |
|---------|-----------|--------|
| **Ver catálogo/precios** | 🔒 Requiere login | 🌐 Público |
| **Agregar al carrito** | 🔒 Requiere login | ✅ Guest puede (pendiente F3) |
| **Checkout** | 🔒 Requiere login | 🔒 Requiere login (por ahora) |
| **Métodos de pago** | Stripe + Zelle | Solo Stripe |
| **Mínimo de orden** | $100 | Sin mínimo |
| **Pickup en tienda** | ✅ Disponible | ❌ Solo envío |
| **Tipo de usuario** | `stylist` | `client` |

---

## Cambios en Endpoints (Ya Implementados)

### Endpoints de Catálogo - Auth Condicional

| Endpoint | Wholesale (sin token) | Retail (sin token) |
|----------|----------------------|-------------------|
| `GET /categories` | ❌ 401 Unauthorized | ✅ Devuelve datos |
| `GET /products` | ❌ 401 Unauthorized | ✅ Devuelve datos |
| `GET /products/{id}` | ❌ 401 Unauthorized | ✅ Devuelve datos |
| `GET /brands` | ❌ 401 Unauthorized | ✅ Devuelve datos |

**Comportamiento:**
- En **retail**: estos endpoints funcionan sin token. Si se envía un token válido, se acepta pero no es requerido.
- En **wholesale**: estos endpoints devuelven `401 Unauthorized` si no hay token.

### Endpoints de Carrito - Auth Condicional

| Endpoint | Wholesale (sin token) | Retail (sin token + X-Session-ID) |
|----------|----------------------|----------------------------------|
| `GET /cart` | ❌ 401 Unauthorized | ✅ Devuelve carrito guest |
| `POST /cart/items` | ❌ 401 Unauthorized | ✅ Agrega al carrito guest |
| `PUT /cart/items/{id}` | ❌ 401 Unauthorized | ✅ Actualiza cantidad |
| `DELETE /cart/items/{id}` | ❌ 401 Unauthorized | ✅ Elimina item |
| `DELETE /cart` | ❌ 401 Unauthorized | ✅ Vacía carrito |
| `POST /cart/lock` | ❌ 401 Unauthorized | ✅ Crea lock para checkout |

**Importante para Retail:**
- Requiere header `X-Session-ID` si no hay token
- Si hay token, usa el usuario autenticado
- Si no hay ni token ni X-Session-ID → error 400

### Endpoints que SIEMPRE requieren auth (ambos modos)

| Endpoint | Descripción |
|----------|-------------|
| `GET /favorites` | Lista de favoritos del usuario |
| `POST /products/{id}/favorite` | Toggle favorito |
| `GET /favorites/ids` | IDs de productos favoritos |
| `GET /products/{id}/is-favorite` | Check si es favorito |
| `POST /cart/merge` | Fusionar carrito guest con usuario |

---

## Qué debe hacer el Frontend para Retail

### 1. Catálogo público
- No es necesario forzar login para ver productos
- Las llamadas a `/products`, `/categories`, `/brands` funcionan sin token

### 2. Token opcional
- Si el usuario está logueado, enviar el token (para features como favoritos)
- Si no está logueado, no enviar token y la API responde igual

### 3. Favoritos
- Requieren autenticación
- Si el usuario no está logueado, decidir si ocultar o mostrar opción de login

### 4. Carrito (Implementado ✅)
- Usa `X-Session-ID` header para identificar guests
- Generar un session_id único y guardarlo en localStorage
- Enviar header `X-Session-ID: {session_id}` en todas las llamadas a `/cart/*`
- Si el usuario hace login, llamar `POST /cart/merge` para fusionar carritos

---

## Cómo identificar el modo

Al iniciar la API, se loguea el modo:

```
INFO: Store mode: retail (Landa Beauty Supply - Retail)
```

o

```
INFO: Store mode: wholesale (Landa Beauty Supply - Wholesale)
```

---

## Registro de Usuarios

El flujo de registro es **diferente** según el modo:

### Retail - Registro Directo

```
POST /register
→ Usuario creado inmediatamente
→ Devuelve access_token + user data
→ Usuario puede hacer login inmediatamente
```

**Request:**

```json
{
  "first_name": "María",
  "last_name": "García",
  "email": "maria@email.com",
  "phone": "+1234567890",
  "password": "securepass123"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "first_name": "María",
    "last_name": "García",
    "email": "maria@email.com",
    "user_type": "client"
  }
}
```

### Wholesale - Solicitud de Registro (Requiere Aprobación)

```
POST /register
→ Crea solicitud pendiente
→ Admin debe aprobar desde dashboard
→ Usuario notificado cuando se apruebe
→ Luego puede hacer login
```

**Request:** (incluye campos adicionales de negocio)

```json
{
  "first_name": "Carlos",
  "last_name": "Ruiz",
  "email": "carlos@salon.com",
  "phone": "+1234567890",
  "password": "securepass123",
  "estimated_monthly_purchase": 500.00,
  "notes": "Tengo un salón con 5 estilistas. Trabajo principalmente con tintes.",
  "business_types": ["salon", "distributor"],
  "services_offered": ["coloring", "bleaching", "straightening"],
  "frequent_products": ["dyes", "peroxides", "bleaches"],
  "team_size": "4-6"
}
```

**Response (200):**

```json
{
  "pending": true,
  "request_code": "REQ-X7K9M2",
  "message": "Tu solicitud ha sido recibida. Te notificaremos cuando sea aprobada."
}
```

> **Nota:** El `request_code` es un código único que el usuario puede usar para consultar el estado de su solicitud.

### Campos Adicionales para Wholesale

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `estimated_monthly_purchase` | float | **Sí** | Compra mensual estimada en USD |
| `business_types` | string[] | **Sí** | Tipos de negocio (ver valores abajo) |
| `services_offered` | string[] | **Sí** | Servicios que ofrece |
| `frequent_products` | string[] | **Sí** | Productos que compra frecuentemente |
| `team_size` | string | **Sí** | Tamaño del equipo |
| `notes` | string | No | Notas adicionales (info del negocio, etc.) |

⚠️ Los campos de perfil de negocio son **obligatorios** para registrarse en wholesale.

#### Valores Válidos para Perfil de Negocio

**business_types** (puede marcar varios):
- `independent_stylist` - Estilista independiente
- `salon` - Salón de belleza
- `barbershop` - Barbería
- `student` - Estudiante de cosmetología
- `distributor` - Distribuidor / reventa
- `other` - Otro

**services_offered** (puede marcar varios):
- `coloring` - Coloración
- `bleaching` - Decoloración
- `straightening` - Alisados / Botox / Keratina
- `treatments` - Tratamientos capilares
- `cuts_styling` - Cortes y estilizado
- `other` - Otro

**frequent_products** (puede marcar varios):
- `dyes` - Tintes
- `peroxides` - Peróxidos / Reveladores
- `bleaches` - Decolorantes
- `treatments` - Tratamientos / reconstructores
- `professional_shampoo` - Shampoo profesional

**team_size** (selección única):
- `solo` - Solo yo
- `2-3` - 2 – 3 estilistas
- `4-6` - 4 – 6 estilistas
- `7+` - 7 o más estilistas

---

## Endpoint /me

Obtener datos del usuario autenticado:

```
GET /me
Authorization: Bearer {token}
```

**Response (200):**

```json
{
  "id": 123,
  "first_name": "María",
  "last_name": "García",
  "email": "maria@email.com",
  "phone": "+1234567890",
  "user_type": "client",
  "registration_complete": true,
  "has_password": true,
  "password_requires_update": false
}
```

---

## Estado de Implementación Backend

| Fase | Estado | Descripción |
|------|--------|-------------|
| F1: Config Base | ✅ | `STORE_MODE` y `STORE_CONFIG` |
| F2: Auth Catálogo | ✅ | Endpoints de productos públicos en retail |
| F3: Carrito Flexible | ✅ | Guest puede agregar al carrito en retail |
| F4: Checkout Condicional | ✅ | Pagos, pickup por modo |
| F5: User Types | ✅ | Default user type por modo |
| Registro Diferenciado | ✅ | Retail directo, Wholesale requiere aprobación |

---

## Preguntas Pendientes

1. ~~**Guest Checkout**: ¿Permitir checkout sin cuenta en retail?~~ → Requiere login
2. **Merge de carritos**: ¿Qué pasa si un guest agrega items y luego hace login? → `POST /cart/merge`
3. **Branding**: ¿Diferentes colores/logo para retail vs wholesale?

---

*Última actualización: Enero 2026*
