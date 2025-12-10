# API - Productos Similares y Frecuentemente Comprados Juntos

## Resumen

Dos campos para relacionar productos:
- **`similar_products`**: Productos similares al producto actual
- **`frequently_bought_together`**: Productos comprados frecuentemente juntos

---

## Admin API (POST/PUT)

### Crear/Actualizar producto con productos relacionados

```json
{
  "seller_sku": "12345",
  "name": "Tinte Kuul Rubio Claro 90ml",
  "regular_price": 15.99,
  "brand": "Kuul",
  
  "similar_products": ["12346", "12347", "12348"],
  "frequently_bought_together": ["12360", "12361"]
}
```

### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `similar_products` | `Array<string>` | Lista de `seller_sku` de productos similares |
| `frequently_bought_together` | `Array<string>` | Lista de `seller_sku` de productos comprados juntos |

### Notas importantes

- Los arrays contienen **solo el `seller_sku`** como string
- **No hay límite** en la cantidad de elementos
- Los `seller_sku` referenciados **pueden no existir** aún
- Los campos son opcionales (pueden venir vacíos `[]` o no incluirse)
- **NO se valida** si los SKUs existen al guardar

---

## Frontend API (GET)

### GET /products (lista)

En la lista de productos, los campos `similar_products` y `frequently_bought_together` vienen **vacíos** (por performance):

```json
{
  "results": [
    {
      "id": 1,
      "name": "Tinte Kuul",
      "similar_products": [],
      "frequently_bought_together": []
    }
  ]
}
```

### GET /products/{id} (detalle)

En el detalle de un producto, los campos vienen **resueltos** con la información completa de cada producto:

```json
{
  "id": 1,
  "name": "Tinte Kuul Rubio Claro 90ml",
  "similar_products": [
    {
      "id": 2,
      "seller_sku": "12346",
      "name": "Tinte Kuul Rubio Medio 90ml",
      "regular_price": 15.99,
      "sale_price": null,
      "image_url": "https://...",
      "is_in_stock": true,
      "brand": "Kuul"
    }
  ],
  "frequently_bought_together": [
    {
      "id": 10,
      "seller_sku": "12360",
      "name": "Peróxido 20 Vol",
      "regular_price": 8.99,
      "sale_price": 7.99,
      "image_url": "https://...",
      "is_in_stock": true,
      "brand": "Kuul"
    }
  ]
}
```

---

## Comportamiento

| Escenario | Resultado |
|-----------|-----------|
| Producto referenciado **existe** y está en stock | ✅ Se muestra |
| Producto referenciado **NO existe** | ⏭️ Se ignora |
| Producto existe pero **sin stock** | ⏭️ Se ignora |
| Producto se **publica después** | ✅ Aparece automáticamente |
| Producto se **elimina/desactiva** | ✅ Desaparece automáticamente |
| Array viene **vacío** `[]` | ✅ Se guarda vacío |

---

## Ejemplo completo

### Se envía (Admin):

```json
{
  "seller_sku": "1001",
  "name": "Tinte Kuul 6.0",
  "similar_products": ["1002", "1003", "1004", "1005"],
  "frequently_bought_together": ["2001", "2002", "2003"]
}
```

### Se muestra (Frontend) - solo existen 1002, 1003 y 2001:

```json
{
  "seller_sku": "1001",
  "name": "Tinte Kuul 6.0",
  "similar_products": [
    { "seller_sku": "1002", "name": "Tinte Kuul 7.0", "regular_price": 15.99, ... },
    { "seller_sku": "1003", "name": "Tinte Kuul 5.0", "regular_price": 15.99, ... }
  ],
  "frequently_bought_together": [
    { "seller_sku": "2001", "name": "Peróxido 20 Vol", "regular_price": 8.99, ... }
  ]
}
```

Los productos 1004, 1005, 2002 y 2003 no aparecen porque no existen aún. Cuando se publiquen, aparecerán automáticamente.

---

## Admin Response

En el admin (`GET /admin/products`), los campos vienen como **arrays de SKUs** (sin resolver):

```json
{
  "id": 1,
  "name": "Tinte Kuul 6.0",
  "similar_products": ["1002", "1003", "1004", "1005"],
  "frequently_bought_together": ["2001", "2002", "2003"]
}
```

Esto permite ver exactamente lo que se guardó, incluyendo SKUs que aún no existen.

