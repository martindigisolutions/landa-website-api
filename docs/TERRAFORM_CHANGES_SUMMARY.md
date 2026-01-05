# Resumen de Cambios Aplicados - Terraform Producción

**Fecha:** 2026-01-05  
**Estado:** ✅ Cambios Críticos Aplicados

---

## ✅ CAMBIOS APLICADOS

### 1. **Seguridad RDS - RDS Privado** ✅

**Archivo:** `terraform/environments/prod/main.tf`

**Cambios:**
- ✅ Cambiado `publicly_accessible = false` (antes: `true`)
- ✅ Cambiado `allowed_cidr_blocks = [data.aws_vpc.default.cidr_block]` (antes: `["0.0.0.0/0"]`)

**Impacto:** RDS ahora solo es accesible desde dentro de la VPC, no desde internet.

**⚠️ IMPORTANTE:** Para que App Runner pueda conectarse a RDS privado, necesitarás:
- Opción 1: Usar VPC Connector (recomendado)
- Opción 2: Hacer RDS público temporalmente solo para App Runner (menos seguro)

---

### 2. **SSL Forzado en RDS** ✅

**Archivo:** `terraform/modules/rds/main.tf`

**Cambios:**
- ✅ Agregado `aws_db_parameter_group` con `rds.force_ssl = 1`
- ✅ RDS ahora fuerza conexiones SSL/TLS

**Impacto:** Todas las conexiones a RDS deben usar SSL.

**⚠️ IMPORTANTE:** Asegúrate de que tu aplicación use `sslmode=require` en la conexión:
```
postgresql://user:pass@host/db?sslmode=require
```

---

### 3. **Optimizaciones de Costo** ✅

**Archivo:** `terraform/environments/prod/main.tf`

**Cambios:**
- ✅ CPU: `1024` → `512` (0.5 vCPU)
- ✅ Memory: `2048` → `1024` (1GB)
- ✅ Max Instances: `10` → `5`
- ✅ RDS Instance: `db.t3.small` → `db.t3.micro`
- ✅ RDS Storage: `50GB` → `20GB` inicial
- ✅ RDS Max Storage: `200GB` → `100GB`
- ✅ Backup Retention: `7` → `30` días

**Ahorro Estimado:** ~$20-37/mes

---

### 4. **Auto Minor Version Upgrade** ✅

**Archivo:** `terraform/modules/rds/main.tf` y `terraform/modules/rds/variables.tf`

**Cambios:**
- ✅ Agregado `auto_minor_version_upgrade = true` para RDS
- ✅ Agregada variable `auto_minor_version_upgrade` al módulo

**Impacto:** RDS se actualizará automáticamente con parches de seguridad menores.

---

### 5. **Tags Mejorados** ✅

**Archivo:** `terraform/environments/prod/main.tf`

**Cambios:**
- ✅ Agregados tags: `CostCenter`, `BillingCode`, `Environment`

**Impacto:** Mejor tracking de costos en AWS.

---

## ⚠️ CAMBIOS PENDIENTES (CRÍTICOS)

### 1. **Secrets Manager** 🔴 CRÍTICO

**Estado:** ❌ NO APLICADO

**Razón:** Requiere cambios significativos en cómo se pasan secrets a App Runner.

**Acción Requerida:**
1. Crear secrets en AWS Secrets Manager manualmente o con Terraform
2. Modificar App Runner para usar `runtime_environment_secrets` en lugar de `runtime_environment_variables`
3. Actualizar la aplicación para leer desde Secrets Manager

**Archivos a Modificar:**
- `terraform/modules/apprunner/main.tf`
- Crear nuevo recurso `aws_secretsmanager_secret`

---

### 2. **Remote State Backend** 🔴 CRÍTICO

**Estado:** ❌ NO APLICADO (comentado)

**Razón:** Requiere crear bucket S3 y tabla DynamoDB primero.

**Acción Requerida:**
1. Crear bucket S3: `landa-terraform-state-prod`
2. Crear tabla DynamoDB: `landa-terraform-locks`
3. Descomentar el bloque `backend "s3"` en `terraform/environments/prod/main.tf`
4. Ejecutar `terraform init -migrate-state`

**Comandos:**
```bash
# Crear bucket S3
aws s3 mb s3://landa-terraform-state-prod --region us-west-2

# Habilitar versionado
aws s3api put-bucket-versioning \
  --bucket landa-terraform-state-prod \
  --versioning-configuration Status=Enabled

# Crear tabla DynamoDB
aws dynamodb create-table \
  --table-name landa-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2
```

---

### 3. **CloudWatch Alarms y SNS** 🟡 ALTO

**Estado:** ❌ NO APLICADO

**Razón:** Requiere crear recursos adicionales.

**Acción Requerida:**
- Crear SNS topic para alertas
- Crear CloudWatch alarms para errores, latencia, etc.
- Suscribir email al SNS topic

---

## 📋 CHECKLIST PRE-DESPLIEGUE

### Antes de `terraform apply`:

- [ ] ✅ RDS configurado como privado
- [ ] ✅ SSL forzado en RDS
- [ ] ✅ Recursos optimizados para costo
- [ ] ⚠️ **Crear bucket S3 para remote state**
- [ ] ⚠️ **Crear tabla DynamoDB para state locking**
- [ ] ⚠️ **Configurar Secrets Manager (o usar env vars temporalmente)**
- [ ] ⚠️ **Verificar que DATABASE_URL use `sslmode=require`**
- [ ] ⚠️ **Planificar cómo App Runner se conectará a RDS privado (VPC Connector)**

### Después de `terraform apply`:

- [ ] Configurar secrets en App Runner (manual o Secrets Manager)
- [ ] Probar conexión a RDS desde App Runner
- [ ] Verificar health check funciona
- [ ] Configurar CloudWatch alarms
- [ ] Configurar SNS para alertas
- [ ] Documentar credenciales y endpoints

---

## 🔧 CONFIGURACIÓN ADICIONAL NECESARIA

### 1. VPC Connector para App Runner → RDS

Si RDS es privado, App Runner necesita VPC Connector:

```terraform
# Agregar a terraform/environments/prod/main.tf
resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.project_name}-vpc-connector"
  subnets            = data.aws_subnets.default.ids
  security_groups    = [aws_security_group.apprunner.id]
}

# Actualizar App Runner para usar VPC Connector
module "apprunner" {
  # ...
  vpc_connector_arn = aws_apprunner_vpc_connector.main.arn
}
```

**Costo:** ~$7/mes

---

### 2. Security Group para App Runner

```terraform
resource "aws_security_group" "apprunner" {
  name        = "${var.project_name}-apprunner-sg"
  description = "Security group for App Runner VPC Connector"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  tags = var.tags
}
```

---

## 📊 COSTOS ESTIMADOS

### Configuración Optimizada:
- **App Runner:** ~$30-50/mes (1-5 instancias, 0.5 vCPU, 1GB)
- **RDS db.t3.micro:** ~$7.50/mes
- **RDS Storage (20GB):** ~$1.60/mes
- **RDS Backups (30 días):** ~$3/mes
- **ECR Storage:** ~$1/mes
- **CloudWatch Logs:** ~$5/mes
- **VPC Connector (si necesario):** ~$7/mes
- **Secrets Manager:** ~$1/mes
- **S3 + DynamoDB (state):** ~$0.50/mes

**Total Estimado:** ~$57-75/mes

**Ahorro vs Configuración Original:** ~$20-37/mes

---

## 🚀 PRÓXIMOS PASOS

1. **Revisar este documento** y verificar que todos los cambios sean apropiados
2. **Crear recursos de infraestructura** (S3, DynamoDB) para remote state
3. **Decidir sobre Secrets Manager** vs variables de entorno (temporal)
4. **Planificar VPC Connector** si RDS será privado
5. **Ejecutar `terraform plan`** para revisar cambios
6. **Aplicar cambios** en ambiente de staging primero
7. **Probar conexión** App Runner → RDS
8. **Configurar alertas** (CloudWatch + SNS)

---

## 📚 DOCUMENTACIÓN RELACIONADA

- `docs/TERRAFORM_SECURITY_COST_REVIEW.md` - Revisión completa de seguridad y costos
- `terraform/README.md` - Documentación de Terraform
- `PRODUCTION_DEPLOYMENT.md` - Guía de despliegue a producción

