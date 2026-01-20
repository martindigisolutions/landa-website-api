# Registration Requests API (Admin)

Endpoints para gestionar solicitudes de registro en modo **Wholesale**.

> **Nota:** Estos endpoints requieren autenticación OAuth2 con scope `users:write` o `users:read`.

---

## Resumen del Flujo

```
1. Usuario llama POST /register en wholesale (con perfil de negocio obligatorio)
2. Se crea RegistrationRequest con status="pending"
3. Admin ve lista de solicitudes pendientes
4. Admin aprueba o rechaza
5. Si aprueba → Se crea User, se notifica al usuario
6. Usuario puede hacer login
```

> **Campos obligatorios para registro wholesale:**
> - `estimated_monthly_purchase` (compra mensual estimada)
> - `business_types` (tipo de negocio)
> - `services_offered` (servicios que ofrece)
> - `frequent_products` (productos frecuentes)
> - `team_size` (tamaño del equipo)

---

## Endpoints

### 1. Listar Solicitudes de Registro

```
GET /admin/registration-requests
```

**Query Parameters:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `status` | string | (todos) | Filtrar por: `pending`, `approved`, `rejected` |
| `page` | int | 1 | Página |
| `page_size` | int | 20 | Items por página |

**Response (200):**

```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "results": [
    {
      "id": 123,
      "request_code": "REQ-X7K9M2",
      "first_name": "María",
      "last_name": "González",
      "email": "maria@salon.com",
      "phone": "+1234567890",
      "whatsapp_phone": "+1234567890",
      "estimated_monthly_purchase": 500.00,
      "notes": "Tengo un salón con 5 estilistas",
      "business_types": ["salon"],
      "services_offered": ["coloring", "bleaching", "treatments"],
      "frequent_products": ["dyes", "peroxides", "treatments"],
      "team_size": "4-6",
      "status": "pending",
      "created_at": "2026-01-15T10:30:00",
      "reviewed_at": null,
      "reviewed_by": null,
      "rejection_reason": null
    },
    {
      "id": 122,
      "request_code": "REQ-A3B4C5",
      "first_name": "Carlos",
      "last_name": "Ruiz",
      "email": "carlos@beauty.com",
      "phone": "+0987654321",
      "whatsapp_phone": null,
      "estimated_monthly_purchase": 1200.00,
      "notes": null,
      "business_types": ["independent_stylist"],
      "services_offered": ["coloring", "cuts_styling"],
      "frequent_products": ["dyes", "professional_shampoo"],
      "team_size": "solo",
      "status": "approved",
      "created_at": "2026-01-14T09:00:00",
      "reviewed_at": "2026-01-14T11:30:00",
      "reviewed_by": {
        "id": 1,
        "first_name": "Admin",
        "last_name": "User"
      },
      "rejection_reason": null
    }
  ]
}
```

---

### 2. Ver Detalle de Solicitud

```
GET /admin/registration-requests/{request_id}
```

**Response (200):**

```json
{
  "id": 123,
  "request_code": "REQ-X7K9M2",
  "first_name": "María",
  "last_name": "González",
  "email": "maria@salon.com",
  "phone": "+1234567890",
  "whatsapp_phone": "+1234567890",
  "birthdate": "1990-05-15",
  "estimated_monthly_purchase": 500.00,
  "notes": "Tengo un salón con 5 estilistas. Trabajo principalmente con tintes y tratamientos.",
  "business_types": ["salon"],
  "services_offered": ["coloring", "bleaching", "straightening", "treatments"],
  "frequent_products": ["dyes", "peroxides", "bleaches", "treatments"],
  "team_size": "4-6",
  "status": "pending",
  "created_at": "2026-01-15T10:30:00",
  "reviewed_at": null,
  "reviewed_by": null,
  "rejection_reason": null,
  "user_id": null
}
```

**Error (404):** Solicitud no encontrada

---

### 3. Aprobar Solicitud

```
POST /admin/registration-requests/{request_id}/approve
```

**Request Body:** (opcional)

```json
{
  "send_notification": true
}
```

**Response (200):**

```json
{
  "success": true,
  "message": "Solicitud aprobada. Usuario creado.",
  "user": {
    "id": 456,
    "first_name": "María",
    "last_name": "González",
    "email": "maria@salon.com",
    "phone": "+1234567890",
    "user_type": "stylist"
  },
  "request": {
    "id": 123,
    "status": "approved",
    "reviewed_at": "2026-01-15T14:00:00"
  }
}
```

**Errores:**

| Status | Descripción |
|--------|-------------|
| 404 | Solicitud no encontrada |
| 400 | Solicitud ya fue procesada (no está pending) |
| 409 | Email o teléfono ya registrado (usuario se registró por otro medio) |

---

### 4. Rechazar Solicitud

```
POST /admin/registration-requests/{request_id}/reject
```

**Request Body:**

```json
{
  "reason": "No cumple con los requisitos para ser distribuidor.",
  "send_notification": true
}
```

**Response (200):**

```json
{
  "success": true,
  "message": "Solicitud rechazada.",
  "request": {
    "id": 123,
    "status": "rejected",
    "rejection_reason": "No cumple con los requisitos para ser distribuidor.",
    "reviewed_at": "2026-01-15T14:00:00"
  }
}
```

**Errores:**

| Status | Descripción |
|--------|-------------|
| 404 | Solicitud no encontrada |
| 400 | Solicitud ya fue procesada |

---

## Contadores Rápidos (Dashboard)

### 5. Obtener Contadores

```
GET /admin/registration-requests/stats
```

**Response (200):**

```json
{
  "pending": 12,
  "approved": 156,
  "rejected": 8,
  "total": 176
}
```

---

## Modelo de Datos

### RegistrationRequest

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID interno (no exponer al usuario) |
| `request_code` | string | Código público (ej: `REQ-X7K9M2`) |
| `first_name` | string | Nombre |
| `last_name` | string | Apellido |
| `email` | string | Email |
| `phone` | string | Teléfono |
| `whatsapp_phone` | string? | WhatsApp (opcional) |
| `birthdate` | date? | Fecha de nacimiento |
| `estimated_monthly_purchase` | float? | Compra mensual estimada (USD) |
| `notes` | string? | Notas adicionales del solicitante |
| `business_types` | string[] | Tipos de negocio (ver valores abajo) |
| `services_offered` | string[] | Servicios que ofrece (ver valores abajo) |
| `frequent_products` | string[] | Productos frecuentes (ver valores abajo) |
| `team_size` | string? | Tamaño del equipo: `solo`, `2-3`, `4-6`, `7+` |
| `status` | string | `pending` \| `approved` \| `rejected` |
| `created_at` | datetime | Fecha de solicitud |
| `reviewed_at` | datetime? | Fecha de revisión |
| `reviewed_by` | object? | Admin que revisó |
| `rejection_reason` | string? | Razón del rechazo |
| `user_id` | int? | ID del usuario creado (si aprobado) |

### Valores para Campos de Perfil de Negocio

**business_types** (Tipo de negocio - puede marcar varios):
| Valor | Descripción |
|-------|-------------|
| `independent_stylist` | Estilista independiente |
| `salon` | Salón de belleza |
| `barbershop` | Barbería |
| `student` | Estudiante de cosmetología |
| `distributor` | Distribuidor / reventa |
| `other` | Otro |

**services_offered** (Servicios que ofrece - puede marcar varios):
| Valor | Descripción |
|-------|-------------|
| `coloring` | Coloración |
| `bleaching` | Decoloración |
| `straightening` | Alisados / Botox / Keratina |
| `treatments` | Tratamientos capilares |
| `cuts_styling` | Cortes y estilizado |
| `other` | Otro |

**frequent_products** (Productos que compra frecuentemente - puede marcar varios):
| Valor | Descripción |
|-------|-------------|
| `dyes` | Tintes |
| `peroxides` | Peróxidos / Reveladores |
| `bleaches` | Decolorantes |
| `treatments` | Tratamientos / reconstructores |
| `professional_shampoo` | Shampoo profesional |

**team_size** (Cantidad de estilistas - selección única):
| Valor | Descripción |
|-------|-------------|
| `solo` | Solo yo |
| `2-3` | 2 – 3 estilistas |
| `4-6` | 4 – 6 estilistas |
| `7+` | 7 o más estilistas |

---

## Estados del Flujo

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼                               ▼
    ┌─────────────┐                 ┌─────────────┐
    │  approved   │                 │  rejected   │
    └─────────────┘                 └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ User creado │
    └─────────────┘
```

---

## Notificaciones (Opcional)

Si `send_notification: true`:

**Aprobación:**
- Email al usuario: "Tu solicitud ha sido aprobada. Ya puedes iniciar sesión."

**Rechazo:**
- Email al usuario: "Tu solicitud no fue aprobada. Razón: {reason}"

---

## Ejemplos de Uso

### Listar solo pendientes

```bash
curl -X GET "https://api.wholesale.landa.com/admin/registration-requests?status=pending" \
  -H "Authorization: Bearer {token}"
```

### Aprobar solicitud

```bash
curl -X POST "https://api.wholesale.landa.com/admin/registration-requests/123/approve" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"send_notification": true}'
```

### Rechazar solicitud

```bash
curl -X POST "https://api.wholesale.landa.com/admin/registration-requests/123/reject" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Documentación incompleta", "send_notification": true}'
```

---

## Estado de Implementación

| Endpoint | Estado |
|----------|--------|
| `GET /admin/registration-requests` | ✅ Implementado |
| `GET /admin/registration-requests/{id}` | ✅ Implementado |
| `POST /admin/registration-requests/{id}/approve` | ✅ Implementado |
| `POST /admin/registration-requests/{id}/reject` | ✅ Implementado |
| `GET /admin/registration-requests/stats` | ✅ Implementado |

---

*Última actualización: Enero 2026*
