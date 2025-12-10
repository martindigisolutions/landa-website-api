# Categories API

## Endpoints Públicos (Frontend)

### GET /categories

Obtiene todas las categorías para mostrar filtros en el frontend. Solo devuelve grupos con `show_in_filters=true`.

**Headers:**
- `Accept-Language: en` para inglés
- `Accept-Language: es` para español (default)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Tipo de producto",
    "slug": "tipo-de-producto",
    "icon": "package",
    "show_in_filters": true,
    "categories": [
      {
        "id": 1,
        "name": "Tintes",
        "slug": "tintes",
        "color": "#007bff",
        "icon": null
      }
    ]
  }
]
```

### GET /products (con filtro de categoría)

Ahora puedes filtrar productos por categoría:

```
GET /products?category=tintes
GET /products?category_group=tipo-de-producto
GET /products?category=tintes&brand=Kuul
```

**Parámetros de filtro:**
- `category` - Slug de la categoría (ej: "tintes", "shampoos")
- `category_group` - Slug del grupo (ej: "tipo-de-producto", "marca")

---

# Categories API - Admin Endpoints

## Estructura de Categorías

Las categorías tienen dos niveles:
- **Grupo** (CategoryGroup): El padre, ej: "Tipo de producto", "Marca"
- **Categoría** (Category): El hijo, ej: "Tintes", "Shampoos", "Kuul"

---

## Endpoints

### GET /admin/categories

Obtiene todas las categorías agrupadas.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Tipo de producto",
    "name_en": "Product Type",
    "slug": "tipo-de-producto",
    "icon": "package",
    "show_in_filters": true,
    "display_order": 0,
    "categories": [
      {
        "id": 1,
        "name": "Tintes",
        "name_en": "Hair Dyes",
        "slug": "tintes",
        "color": "#007bff",
        "icon": null,
        "display_order": 0
      },
      {
        "id": 2,
        "name": "Shampoos",
        "name_en": "Shampoos",
        "slug": "shampoos",
        "color": "#17a2b8",
        "icon": null,
        "display_order": 0
      }
    ]
  }
]
```

---

## Enviar Categorías en Productos

### POST /admin/products - Crear producto con categorías

```json
{
  "name": "Tinte Profesional Kuul",
  "regular_price": 15.99,
  "stock": 100,
  "is_in_stock": true,
  "brand": "Kuul",
  "categories": [
    {
      "group": "Tipo de producto",
      "group_en": "Product Type",
      "group_slug": "tipo-de-producto",
      "group_icon": "package",
      "group_show_in_filters": true,
      "name": "Tintes",
      "name_en": "Hair Dyes",
      "slug": "tintes",
      "color": "#007bff"
    }
  ]
}
```

### PUT /admin/products/{id} - Actualizar categorías de un producto

```json
{
  "categories": [
    {
      "group": "Tipo de producto",
      "group_en": "Product Type",
      "group_slug": "tipo-de-producto",
      "group_icon": "package",
      "group_show_in_filters": true,
      "name": "Shampoos",
      "name_en": "Shampoos",
      "slug": "shampoos",
      "color": "#17a2b8"
    }
  ]
}
```

> **Nota:** Al enviar `categories`, se reemplazan TODAS las categorías existentes del producto.

### Quitar todas las categorías de un producto

```json
{
  "categories": []
}
```

### Múltiples categorías en un producto

```json
{
  "categories": [
    {
      "group": "Tipo de producto",
      "group_slug": "tipo-de-producto",
      "name": "Tintes",
      "slug": "tintes",
      "color": "#007bff"
    },
    {
      "group": "Marca",
      "group_slug": "marca",
      "name": "Kuul",
      "slug": "kuul",
      "color": "#28a745"
    }
  ]
}
```

### Mínimo requerido (solo campos obligatorios)

```json
{
  "categories": [
    {
      "group": "Tipo de producto",
      "group_slug": "tipo-de-producto",
      "name": "Tintes",
      "slug": "tintes"
    }
  ]
}
```

---

## Campos de CategoryInput

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `group` | string | ✅ | Nombre del grupo en español |
| `group_slug` | string | ✅ | Slug único del grupo (URL-friendly) |
| `group_en` | string | ❌ | Nombre del grupo en inglés |
| `group_icon` | string | ❌ | Nombre del icono (ej: "package", "tag") |
| `group_show_in_filters` | boolean | ❌ | Mostrar en filtros del frontend (default: true) |
| `group_display_order` | int | ❌ | Orden de visualización del grupo (default: 0) |
| `name` | string | ✅ | Nombre de la categoría en español |
| `slug` | string | ✅ | Slug único de la categoría (URL-friendly) |
| `name_en` | string | ❌ | Nombre de la categoría en inglés |
| `color` | string | ❌ | Color hexadecimal (ej: "#007bff") |
| `icon` | string | ❌ | Icono específico de la categoría |
| `display_order` | int | ❌ | Orden de visualización de la categoría (default: 0) |

---

## Response de Producto con Categorías

Cuando obtienes un producto (GET /admin/products/{id}), las categorías vienen así:

```json
{
  "id": 1,
  "name": "Tinte Profesional Kuul",
  "regular_price": 15.99,
  "categories": [
    {
      "id": 1,
      "name": "Tintes",
      "name_en": "Hair Dyes",
      "slug": "tintes",
      "color": "#007bff",
      "icon": null,
      "display_order": 0,
      "group_id": 1,
      "group_name": "Tipo de producto",
      "group_name_en": "Product Type",
      "group_slug": "tipo-de-producto",
      "group_icon": "package",
      "group_show_in_filters": true
    }
  ]
}
```

---

## Notas Importantes

1. **Creación automática**: Las categorías y grupos se crean automáticamente si no existen (basado en el `slug`).

2. **Actualización automática**: Si una categoría/grupo ya existe, se actualiza con la nueva información enviada.

3. **Slugs únicos**: Los slugs deben ser únicos y URL-friendly (sin espacios, minúsculas, guiones).

4. **Reemplazo total**: Al enviar `categories` en un update, se reemplazan TODAS las categorías anteriores del producto.

5. **Scope requerido**: Necesitas el scope `products:read` para GET categories y `products:write` para crear/actualizar productos con categorías.

