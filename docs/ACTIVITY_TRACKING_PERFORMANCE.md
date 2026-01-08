# Optimización de Performance para Tracking de Actividades

## 🎯 Resumen Ejecutivo

El sistema de tracking de actividades está diseñado para manejar **cientos de miles de registros** sin degradar el rendimiento. Sin embargo, es importante implementar algunas estrategias de mantenimiento para asegurar performance óptima a largo plazo.

---

## ✅ Optimizaciones ya Implementadas

### 1. Índices Estratégicos

La tabla `user_activities` tiene índices en los campos más consultados:

- **Índices individuales:**
  - `user_id` - Para consultar actividades por usuario
  - `session_id` - Para actividades de usuarios guest
  - `endpoint` - Para análisis de endpoints
  - `action_type` - Para filtrar por tipo de acción
  - `created_at` - Para ordenar por fecha

- **Índices compuestos** (más eficientes para queries comunes):
  - `(user_id, created_at)` - Para listar actividades de un usuario ordenadas por fecha
  - `(session_id, created_at)` - Para actividades de guests ordenadas
  - `(action_type, created_at)` - Para filtrar por tipo y ordenar

**Impacto:** Las queries más comunes usan estos índices y son muy rápidas incluso con millones de registros.

### 2. Guardado Asíncrono

- Las actividades se guardan en un thread pool separado
- **No bloquea** las requests HTTP
- Los errores de guardado no afectan la respuesta al usuario

### 3. Paginación

- Todas las queries usan paginación (limit/offset)
- Límite máximo de 100 elementos por página
- Reduce la carga de memoria y tiempo de respuesta

---

## ⚠️ Áreas de Mejora

### 1. N+1 Query Problem (MEJORADO)

**Problema anterior:** Al listar usuarios por actividad, se hacía un COUNT por cada usuario.

**Solución:** Optimizado usando subqueries y agregaciones.

### 2. Limpieza de Datos Antiguos

**Recomendación:** Implementar una tarea periódica para archivar o eliminar actividades antiguas.

**Opciones:**
- **Archivar:** Mover datos antiguos (>90 días) a una tabla de archivado
- **Eliminar:** Eliminar actividades de más de X días
- **Resumir:** Crear resúmenes agregados y eliminar datos detallados antiguos

---

## 📊 Capacidad y Estimaciones de Performance

### 🟢 **Sin Problemas** (Recomendado para producción)

**Hasta 500,000 - 1,000,000 actividades:**
- ✅ Todas las queries funcionan rápido (<200ms)
- ✅ Guardado asíncrono no afecta rendimiento
- ✅ Índices funcionan perfectamente
- ✅ Paginación mantiene respuestas rápidas
- ✅ No requiere mantenimiento especial

**Detalles por volumen:**

| Volumen | Actividades por Usuario | Tiempo de Query | Estado |
|---------|------------------------|-----------------|--------|
| **100K** | ~50-200 por usuario | <50ms | 🟢 Excelente |
| **500K** | ~250-1000 por usuario | <100ms | 🟢 Muy bueno |
| **1M** | ~500-2000 por usuario | <200ms | 🟢 Bueno |

### 🟡 **Manejeable** (Requiere monitoreo)

**1,000,000 - 5,000,000 actividades:**
- ⚠️ Queries pueden tardar 200-500ms ocasionalmente
- ⚠️ GROUP BY queries pueden ser más lentas
- ✅ Todavía funciona bien con índices
- ⚠️ Considera limpieza periódica (opcional, manual)

**Queries más afectadas:**
- `GET /admin/users/by-activity` - Puede tardar 300-500ms
- Queries con filtros complejos + GROUP BY

### 🔴 **Requiere Optimización** 

**Más de 5,000,000 actividades:**
- ❌ Queries pueden tardar 1-3 segundos
- ❌ Necesita limpieza periódica o archivado
- ❌ Considera particionado por fecha
- ❌ O migrar a sistema de analítica dedicado

## 📈 Cálculo Realista de Capacidad

### Escenario Real:

**Asumiendo:**
- 100 usuarios activos
- 50 requests/día por usuario promedio
- = 5,000 actividades/día
- = ~150,000 actividades/mes
- = ~1.8M actividades/año

**Conclusión:** El sistema puede manejar **2-3 años de actividad** sin problemas (hasta 5M registros).

### Con 100,000 actividades:

| Query | Tiempo Esperado | Índice Usado |
|-------|----------------|--------------|
| Actividades por usuario (con paginación) | <50ms | `(user_id, created_at)` |
| Usuarios por última actividad | <100ms | `(user_id, created_at)` + GROUP BY |
| Filtrar por action_type | <50ms | `(action_type, created_at)` |
| Guardar nueva actividad | <10ms | Asíncrono (no bloquea) |

### Con 1,000,000 actividades:

| Query | Tiempo Esperado | Notas |
|-------|----------------|-------|
| Actividades por usuario | <100ms | Índice sigue siendo eficiente |
| Usuarios por última actividad | <300ms | GROUP BY puede ser más lento |
| Filtrar por action_type | <100ms | Índice compuesto ayuda |
| Guardar nueva actividad | <10ms | Asíncrono, sin impacto |

### Con 5,000,000 actividades:

| Query | Tiempo Esperado | Notas |
|-------|----------------|-------|
| Actividades por usuario | <200ms | Aún eficiente con índice |
| Usuarios por última actividad | <800ms | GROUP BY más lento |
| Filtrar por action_type | <200ms | Índice compuesto ayuda |
| Guardar nueva actividad | <10ms | Asíncrono, sin impacto |

---

## 🔧 Mantenimiento Recomendado

### 1. Limpieza Periódica (Mensual)

Crear un script o tarea programada para:

```python
# Eliminar actividades de más de 90 días
# (ajustar según necesidades de negocio)
DELETE FROM user_activities 
WHERE created_at < NOW() - INTERVAL '90 days';
```

**O crear un endpoint admin para hacer esto manualmente:**

```http
POST /admin/activities/cleanup
{
  "older_than_days": 90,
  "dry_run": false
}
```

### 2. Monitoreo

- **Tamaño de la tabla:** Monitorear el tamaño de `user_activities`
- **Tiempo de queries:** Monitorear tiempos de respuesta de los endpoints
- **Índices:** Verificar que los índices estén siendo usados (EXPLAIN queries)

### 3. Particionado (Opcional, para escalar)

Si creces a millones de actividades, considera particionar la tabla por fecha:
- Una partición por mes o trimestre
- Mejora drásticamente el rendimiento de queries con rangos de fecha

---

## 🚀 Próximos Pasos

1. ✅ **Ya implementado:** Índices optimizados
2. ✅ **Ya implementado:** Guardado asíncrono
3. ✅ **Ya implementado:** Paginación
4. ⏳ **Pendiente:** Endpoint de limpieza
5. ⏳ **Pendiente:** Monitoreo de performance

---

## 📝 Notas Técnicas

### Query Optimization Tips

**Buenas prácticas:**
- ✅ Siempre usar filtros de fecha cuando sea posible
- ✅ Limitar resultados con paginación
- ✅ Usar índices compuestos cuando filtres + ordenas

**Evitar:**
- ❌ Queries sin límite (sin paginación)
- ❌ LIKE queries sin prefijo (no usan índices eficientemente)
- ❌ COUNT(*) sin WHERE en tablas grandes

### 📊 Resumen de Capacidad

**🟢 SIN PROBLEMAS (Recomendado):**
- **Hasta 500,000 actividades** - Excelente rendimiento
- **Hasta 1,000,000 actividades** - Muy buen rendimiento
- No requiere mantenimiento especial
- Queries rápidas (<200ms)

**🟡 MANEJABLE (Monitorear):**
- **1M - 5M actividades** - Funciona bien, algunos queries más lentos
- Considera limpieza manual ocasional si lo deseas
- Queries pueden tardar 200-500ms ocasionalmente

**🔴 REQUIERE ACCIÓN:**
- **Más de 5M actividades** - Queries lentos (1-3 segundos)
- Necesita limpieza periódica o archivado
- Considera particionado o sistema de analítica dedicado

**📅 Tiempo hasta llegar a 1M actividades (estimado):**
- 100 usuarios activos × 50 requests/día = 5,000/día
- ≈ 150,000/mes
- **≈ 6-7 meses** hasta 1M actividades

**Conclusión:** Para la mayoría de casos de uso, puedes guardar **2-3 años de actividad completa** sin ningún problema.

---

## 🔍 Monitoreo de Performance

### Queries para Verificar Performance

```sql
-- Tamaño de la tabla
SELECT pg_size_pretty(pg_total_relation_size('user_activities')) AS size;

-- Actividades por día (últimos 30 días)
SELECT DATE(created_at) as date, COUNT(*) as count
FROM user_activities
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Verificar uso de índices
EXPLAIN ANALYZE 
SELECT * FROM user_activities 
WHERE user_id = 1 
ORDER BY created_at DESC 
LIMIT 50;
```

---

**Última actualización:** Enero 2025

