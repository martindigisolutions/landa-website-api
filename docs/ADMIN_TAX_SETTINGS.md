# Configuración de Taxes - Admin Dashboard

## Resumen

El sistema de cálculo de impuestos es dinámico y se basa en la dirección de entrega o la dirección de la tienda (para órdenes de pickup).

### Flujo de Cálculo

```
┌─────────────────────────────────────────────────────────────┐
│                     GET /cart                                │
│                                                              │
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

---

## Settings Requeridos

### Grupo 1: Dirección de la Tienda

| Key | Tipo | Valor Ejemplo | Descripción |
|-----|------|---------------|-------------|
| `store_street_number` | string | `"4001"` | Número de calle |
| `store_street_name` | string | `"Central"` | Nombre de calle |
| `store_street_suffix` | string | `"Ave"` | Sufijo (Ave, St, Blvd, Dr, etc.) |
| `store_street_direction` | string | `"NE"` | Dirección post (NE, NW, SE, SW) - opcional |
| `store_city` | string | `"Albuquerque"` | Ciudad |
| `store_state` | string | `"NM"` | Estado (código de 2 letras) |
| `store_zipcode` | string | `"87108"` | Código postal (5 dígitos) |

### Grupo 2: Configuración de Impuestos

| Key | Tipo | Valor Ejemplo | Descripción |
|-----|------|---------------|-------------|
| `tax_enabled` | boolean | `true` | Habilitar/deshabilitar cálculo de taxes |
| `tax_calculation_method` | string | `"grt_api"` | Método de cálculo (ver opciones abajo) |
| `tax_fixed_rate` | number | `8.25` | Tasa fija en % (solo si method = `fixed_rate`) |
| `tax_apply_to_shipping` | boolean | `false` | Si el shipping debe pagar impuestos |

#### Opciones para `tax_calculation_method`

| Valor | Descripción |
|-------|-------------|
| `grt_api` | Usa la API de New Mexico GRT (https://grt.edacnm.org) |
| `fixed_rate` | Usa la tasa fija definida en `tax_fixed_rate` |
| `none` | No cobra impuestos |

---

## UI Sugerida

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Configuración de Tienda                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📍 DIRECCIÓN DE LA TIENDA                                  │
│  Esta dirección se usa para calcular impuestos en órdenes   │
│  de pickup.                                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │  Número de Calle          Nombre de Calle           │    │
│  │  ┌──────────────┐         ┌─────────────────────┐   │    │
│  │  │ 4001         │         │ Central             │   │    │
│  │  └──────────────┘         └─────────────────────┘   │    │
│  │                                                      │    │
│  │  Sufijo                   Dirección                 │    │
│  │  ┌──────────────┐         ┌─────────────────────┐   │    │
│  │  │ Ave       ▼  │         │ NE              ▼   │   │    │
│  │  └──────────────┘         └─────────────────────┘   │    │
│  │  Opciones: Ave, St,       Opciones: N, S, E, W,     │    │
│  │  Blvd, Dr, Rd, Ln, Ct     NE, NW, SE, SW, (vacío)   │    │
│  │                                                      │    │
│  │  Ciudad                   Estado                    │    │
│  │  ┌──────────────────┐     ┌─────────────────────┐   │    │
│  │  │ Albuquerque      │     │ NM              ▼   │   │    │
│  │  └──────────────────┘     └─────────────────────┘   │    │
│  │                                                      │    │
│  │  Código Postal                                      │    │
│  │  ┌──────────────┐                                   │    │
│  │  │ 87108        │                                   │    │
│  │  └──────────────┘                                   │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  💰 CONFIGURACIÓN DE IMPUESTOS                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │  ┌───┐                                              │    │
│  │  │ ✓ │  Habilitar cálculo de impuestos              │    │
│  │  └───┘                                              │    │
│  │                                                      │    │
│  │  Método de cálculo:                                  │    │
│  │  ┌───┐                                              │    │
│  │  │ ● │  API GRT (New Mexico)                        │    │
│  │  └───┘  Calcula automáticamente basado en dirección │    │
│  │         Solo funciona para direcciones en NM        │    │
│  │                                                      │    │
│  │  ┌───┐                                              │    │
│  │  │ ○ │  Tasa fija                                   │    │
│  │  └───┘  ┌─────────────┐                             │    │
│  │         │ 8.25        │ %                           │    │
│  │         └─────────────┘                             │    │
│  │                                                      │    │
│  │  ┌───┐                                              │    │
│  │  │ ○ │  Sin impuestos                               │    │
│  │  └───┘                                              │    │
│  │                                                      │    │
│  │  ───────────────────────────────────────────        │    │
│  │                                                      │    │
│  │  ┌───┐                                              │    │
│  │  │   │  Aplicar impuestos al costo de envío         │    │
│  │  └───┘                                              │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│                          ┌─────────────────────────┐        │
│                          │  💾 Guardar Cambios     │        │
│                          └─────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Endpoints API

### Obtener Settings

```http
GET /admin/settings
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "settings": [
      {"key": "store_street_number", "value": "4001", "value_type": "string"},
      {"key": "store_street_name", "value": "Central", "value_type": "string"},
      {"key": "store_street_suffix", "value": "Ave", "value_type": "string"},
      {"key": "store_street_direction", "value": "NE", "value_type": "string"},
      {"key": "store_city", "value": "Albuquerque", "value_type": "string"},
      {"key": "store_state", "value": "NM", "value_type": "string"},
      {"key": "store_zipcode", "value": "87108", "value_type": "string"},
      {"key": "tax_enabled", "value": "true", "value_type": "boolean"},
      {"key": "tax_calculation_method", "value": "grt_api", "value_type": "string"},
      {"key": "tax_fixed_rate", "value": "0", "value_type": "number"},
      {"key": "tax_apply_to_shipping", "value": "false", "value_type": "boolean"}
    ]
  }
}
```

### Actualizar Settings (bulk)

```http
PUT /admin/settings
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "settings": [
    {"key": "store_street_number", "value": "4001"},
    {"key": "store_street_name", "value": "Central"},
    {"key": "store_street_suffix", "value": "Ave"},
    {"key": "store_street_direction", "value": "NE"},
    {"key": "store_city", "value": "Albuquerque"},
    {"key": "store_state", "value": "NM"},
    {"key": "store_zipcode", "value": "87108"},
    {"key": "tax_enabled", "value": "true"},
    {"key": "tax_calculation_method", "value": "grt_api"},
    {"key": "tax_fixed_rate", "value": "0"},
    {"key": "tax_apply_to_shipping", "value": "false"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "data": {
    "updated_count": 11
  }
}
```

### Actualizar Setting Individual

```http
PUT /admin/settings/{key}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "value": "8.5"
}
```

---

## Validaciones Sugeridas

### Frontend

| Campo | Validación |
|-------|------------|
| `store_street_number` | Requerido, alfanumérico |
| `store_street_name` | Requerido, min 2 caracteres |
| `store_street_suffix` | Opcional, dropdown con opciones |
| `store_street_direction` | Opcional, dropdown con opciones |
| `store_city` | Requerido, min 2 caracteres |
| `store_state` | Requerido, dropdown de estados US |
| `store_zipcode` | Requerido, 5 dígitos |
| `tax_fixed_rate` | 0-100, máximo 4 decimales |

### Opciones para Dropdowns

**Sufijos de calle:**
```
Ave, St, Blvd, Dr, Rd, Ln, Ct, Way, Pl, Cir, Pkwy, Hwy
```

**Direcciones:**
```
(vacío), N, S, E, W, NE, NW, SE, SW
```

**Estados (US):**
```
AL, AK, AZ, AR, CA, CO, CT, DE, FL, GA, HI, ID, IL, IN, IA, KS, KY, LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM, NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA, WV, WI, WY
```

---

## Respuesta del Carrito (campos de tax)

Cuando se llama a `GET /cart`, la respuesta incluirá:

```json
{
  "success": true,
  "data": {
    "items": [...],
    "subtotal": 100.00,
    "shipping_fee": 8.00,
    "tax": 7.88,
    "tax_rate": 7.875,
    "tax_source": "grt_api",
    "total": 115.88,
    ...
  }
}
```

### Campos de Tax

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tax` | number | Monto de impuesto en dólares |
| `tax_rate` | number | Tasa de impuesto aplicada (%) |
| `tax_source` | string | Origen del cálculo |

### Valores de `tax_source`

| Valor | Significado |
|-------|-------------|
| `grt_api` | Calculado via API de New Mexico GRT |
| `fixed_rate` | Usando tasa fija configurada |
| `none` | No se cobran impuestos |
| `store_rate` | Usando la dirección de tienda (pickup) |

---

## Notas de Implementación

### API GRT de New Mexico

- **URL:** https://grt.edacnm.org/api/by_address
- **Método:** GET
- **Solo funciona para direcciones en New Mexico**
- **Retorna `tax_rate` como porcentaje (ej: 7.875)**

Ejemplo de llamada:
```
GET https://grt.edacnm.org/api/by_address?street_number=4001&street_name=Central&street_suffix=Ave&street_post_directional=NE&city=Albuquerque&zipcode=87108
```

Respuesta:
```json
{
  "results": [{
    "street_number": "4001",
    "street_name": "Central",
    "street_suffix": "Ave",
    "street_post_directional": "NE",
    "city": "Albuquerque",
    "zipcode": "87108",
    "tax_rate": 7.875,
    "success": true,
    "county": "Bernalillo"
  }]
}
```

### Extensibilidad Futura

El campo `tax_calculation_method` permite agregar nuevos métodos:

| Método Futuro | Descripción |
|---------------|-------------|
| `ca_cdtfa_api` | API de California (cuando se expanda) |
| `tx_comptroller_api` | API de Texas |
| `avalara` | Integración con Avalara (servicio de terceros) |

---

## Preguntas Frecuentes

**¿Qué pasa si la API GRT no encuentra la dirección?**
> El sistema usará la tasa fija configurada como fallback. Si no hay tasa fija, no se cobrarán impuestos para esa orden.

**¿Se cobran impuestos fuera de New Mexico?**
> Por ahora no. El `tax_calculation_method: grt_api` solo funciona para NM. Para otros estados, el sistema retorna tax = 0.

**¿Los impuestos se calculan sobre el shipping?**
> Depende de la configuración `tax_apply_to_shipping`. Por defecto es `false`.
