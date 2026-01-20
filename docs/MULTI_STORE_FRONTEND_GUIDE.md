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

## Estado de Implementación Backend

| Fase | Estado | Descripción |
|------|--------|-------------|
| F1: Config Base | ✅ | `STORE_MODE` y `STORE_CONFIG` |
| F2: Auth Catálogo | ✅ | Endpoints de productos públicos en retail |
| F3: Carrito Flexible | ✅ | Guest puede agregar al carrito en retail |
| F4: Checkout Condicional | ⏳ | Mínimo, pagos, pickup por modo |
| F5: User Types | ⏳ | Default user type por modo |

---

## Preguntas Pendientes

1. **Guest Checkout**: ¿Permitir checkout sin cuenta en retail?
2. **Merge de carritos**: ¿Qué pasa si un guest agrega items y luego hace login?
3. **Branding**: ¿Diferentes colores/logo para retail vs wholesale?

---

*Última actualización: Enero 2026*
