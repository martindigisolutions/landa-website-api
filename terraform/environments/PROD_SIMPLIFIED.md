# PROD Simplificado - Basado en DEV

## Resumen de Cambios

He simplificado la configuración de PROD para que esté basada en DEV (que funciona correctamente), agregando solo las mejoras de seguridad necesarias.

## Diferencias Clave: DEV vs PROD (Simplificado)

### ✅ Lo que se MANTIENE igual a DEV (funciona bien):

1. **RDS Público** (`publicly_accessible = true`)
   - ✅ App Runner puede conectarse directamente sin VPC Connector
   - ✅ No requiere Security Groups complejos
   - ✅ No requiere reglas de egress para internet
   - ✅ Más simple y funciona

2. **Sin VPC Connector**
   - ✅ Menos complejidad
   - ✅ Menos puntos de fallo
   - ✅ App Runner tiene acceso a internet por defecto

3. **Sin Security Groups adicionales**
   - ✅ App Runner usa su configuración por defecto
   - ✅ RDS está protegido por Security Group del módulo RDS

### 🔒 Mejoras de Seguridad en PROD (vs DEV):

1. **Secrets Manager**
   - ✅ Variables sensibles en Secrets Manager (no texto plano)
   - ✅ `DATABASE_URL`, `SECRET_KEY`, `STRIPE_SECRET_KEY`, etc.

2. **RDS Security**
   - ✅ `allowed_cidr_blocks = [vpc_cidr]` (solo VPC, no `0.0.0.0/0`)
   - ✅ `deletion_protection = true` (previene borrado accidental)
   - ✅ `skip_final_snapshot = false` (mantiene snapshot al borrar)
   - ✅ `backup_retention_period = 30` días (vs 1 día en DEV)

3. **Monitoreo**
   - ✅ CloudWatch Alarms (4xx, 5xx, CPU RDS)
   - ✅ SNS Topic para alertas por email

4. **Configuración**
   - ✅ `log_level = "info"` (vs "debug" en DEV)
   - ✅ Orígenes permitidos solo para producción

## Lo que se ELIMINÓ de PROD (complejidad innecesaria):

1. ❌ **VPC Connector** - No necesario si RDS es público
2. ❌ **Security Group para App Runner** - No necesario sin VPC Connector
3. ❌ **Reglas de egress para internet** - App Runner ya tiene acceso por defecto
4. ❌ **Internet Gateway y Route Table** - No necesario sin VPC Connector
5. ❌ **RDS privado** - Funciona bien para DB, pero requiere VPC Connector que bloquea acceso a internet (Stripe, GRT API) a menos que se configuren reglas de egress explícitas

## Ventajas de este Enfoque:

1. ✅ **Simplicidad**: Menos recursos = menos puntos de fallo
2. ✅ **Funciona**: Basado en DEV que ya funciona correctamente
3. ✅ **Seguridad**: Mejoras donde importan (Secrets Manager, backups, monitoreo)
4. ✅ **Costo**: Menos recursos = menos costo
5. ✅ **Mantenibilidad**: Más fácil de entender y mantener

## ¿Por qué RDS Público en PROD?

**Nota importante:** RDS privado SÍ funcionaba para conectarse a la base de datos. El problema real era:

1. ✅ **RDS privado + VPC Connector** → App Runner se conecta bien a la DB
2. ❌ **Pero** → App Runner con VPC Connector NO tiene acceso a internet por defecto
3. ❌ **Resultado** → No puede conectarse a Stripe API, GRT API, etc.

**Solución anterior (compleja):**
- RDS privado + VPC Connector + Security Group con reglas de egress para HTTPS/HTTP
- Funciona, pero es más complejo y fácil olvidar configurar las reglas de egress

**Solución actual (simple):**
- RDS público → App Runner se conecta directamente (sin VPC Connector)
- App Runner tiene acceso a internet por defecto → Stripe, GRT API funcionan
- Más simple, menos puntos de fallo

## Seguridad del RDS Público:

Aunque RDS es `publicly_accessible = true`, está protegido por:

1. **Security Group**: Solo permite conexiones desde el CIDR de la VPC (no `0.0.0.0/0`)
2. **Credenciales**: Usuario/contraseña fuertes
3. **SSL/TLS**: Conexiones encriptadas
4. **Network ACLs**: Control adicional a nivel de VPC

Para mayor seguridad en el futuro, puedes:
- Cambiar a RDS privado + VPC Connector + reglas de egress explícitas para internet
- Usar AWS PrivateLink
- Implementar VPN o bastion host

## Próximos Pasos:

1. ✅ Ejecutar `terraform plan` para verificar cambios
2. ✅ Ejecutar `terraform apply` para aplicar
3. ✅ Verificar que App Runner puede conectarse a Stripe y GRT API
4. ✅ Verificar que RDS es accesible desde App Runner

