# Comparación de Infraestructura: DEV vs PROD

## Resumen Ejecutivo

| Aspecto | DEV | PROD | Notas |
|---------|-----|------|-------|
| **Estado Backend** | Local (comentado) | S3 + DynamoDB | PROD usa remote state |
| **VPC** | Default VPC | Default VPC | Ambos usan VPC por defecto |
| **Internet Gateway** | ❌ No configurado | ✅ Configurado | PROD tiene IGW y ruta |
| **Security Group Egress** | ❌ No configurado | ✅ HTTPS/HTTP configurado | PROD tiene reglas para internet |
| **VPC Connector** | ❌ No existe | ✅ Configurado | PROD usa VPC Connector para RDS privado |
| **RDS Acceso** | Público (`publicly_accessible = true`) | Privado (`publicly_accessible = false`) | PROD más seguro |
| **Secrets Manager** | ❌ No usa | ✅ Usa | PROD usa Secrets Manager |
| **CloudWatch Alarms** | ❌ No configurado | ✅ Configurado | PROD tiene monitoreo |
| **SNS Alerts** | ❌ No configurado | ✅ Configurado | PROD tiene alertas por email |

---

## Diferencias Detalladas

### 1. Backend de Terraform

**DEV:**
```hcl
# Optional: Remote state in S3
# backend "s3" {
#   bucket  = "landa-terraform-state"
#   key     = "dev/apprunner.tfstate"
#   region  = "us-west-2"
#   profile = "dev-account"
# }
```
- ❌ Backend comentado (usa estado local)
- ⚠️ No hay bloqueo de estado compartido

**PROD:**
```hcl
backend "s3" {
  bucket         = "landa-terraform-state-prod"
  key            = "prod/apprunner.tfstate"
  region         = "us-west-2"
  encrypt        = true
  dynamodb_table = "landa-terraform-locks"
}
```
- ✅ Backend S3 configurado
- ✅ Encriptación habilitada
- ✅ DynamoDB para bloqueo de estado

---

### 2. Configuración de Red (VPC/Internet)

**DEV:**
- ❌ No tiene configuración de Internet Gateway
- ❌ No tiene Security Group para VPC Connector
- ❌ No tiene VPC Connector
- ❌ No tiene reglas de egress para internet

**PROD:**
- ✅ Internet Gateway configurado (data source)
- ✅ Ruta a internet (`0.0.0.0/0`) configurada
- ✅ Security Group con reglas de egress:
  - HTTPS (443) → `0.0.0.0/0`
  - HTTP (80) → `0.0.0.0/0`
  - PostgreSQL (5432) → VPC CIDR
- ✅ VPC Connector configurado

**Impacto:** PROD puede acceder a APIs externas (Stripe, GRT API), DEV no puede.

---

### 3. App Runner Configuration

**DEV:**
```hcl
module "apprunner" {
  # ...
  extra_env_vars = var.create_rds ? {
    DATABASE_URL = module.rds[0].database_url
  } : {}
  # NO usa Secrets Manager
  # NO usa VPC Connector
}
```

**PROD:**
```hcl
module "apprunner" {
  # ...
  runtime_environment_secrets = var.use_secrets_manager && var.create_rds ? {
    DATABASE_URL = aws_secretsmanager_secret.database_url[0].arn
  } : {}
  
  secrets_manager_arns = var.use_secrets_manager && var.create_rds ? [
    aws_secretsmanager_secret.database_url[0].arn
  ] : []
  
  vpc_connector_arn = var.create_rds && var.use_vpc_connector ? 
    aws_apprunner_vpc_connector.main[0].arn : null
}
```

**Diferencias:**
- DEV: Variables de entorno en texto plano
- PROD: Usa Secrets Manager para `DATABASE_URL`
- PROD: Usa VPC Connector para acceso privado a RDS

---

### 4. RDS Configuration

**DEV:**
```hcl
module "rds" {
  # ...
  allowed_cidr_blocks = ["0.0.0.0/0"]  # Acceso desde cualquier IP
  publicly_accessible = true           # RDS público
  multi_az            = false
  deletion_protection = false
  skip_final_snapshot = true
  backup_retention_period = 1           # 1 día de backups
}
```

**PROD:**
```hcl
module "rds" {
  # ...
  allowed_cidr_blocks        = var.use_vpc_connector ? [] : [data.aws_vpc.default.cidr_block]
  allowed_security_group_ids = var.use_vpc_connector ? [aws_security_group.apprunner.id] : []
  publicly_accessible        = false    # RDS privado
  multi_az                = var.rds_multi_az
  deletion_protection     = true       # Protección contra eliminación
  skip_final_snapshot     = false
  backup_retention_period  = 30        # 30 días de backups
  auto_minor_version_upgrade = true
}
```

**Diferencias:**
- **Seguridad:** DEV es público, PROD es privado
- **Backups:** DEV 1 día, PROD 30 días
- **Protección:** DEV sin protección, PROD con `deletion_protection`
- **Acceso:** DEV desde cualquier IP, PROD solo desde Security Group

---

### 5. Recursos de App Runner

**DEV:**
- CPU: `1024` (1 vCPU)
- Memory: `2048` (2 GB)
- Min Instances: `1`
- Max Instances: `3`
- Log Level: `debug`

**PROD:**
- CPU: `1024` (1 vCPU) - **IGUAL**
- Memory: `2048` (2 GB) - **IGUAL**
- Min Instances: `1` - **IGUAL**
- Max Instances: `5` - **MÁS**
- Log Level: `info`

**Nota:** Ambos tienen los mismos recursos base, PROD puede escalar más.

---

### 6. Monitoreo y Alertas

**DEV:**
- ❌ No tiene CloudWatch Alarms
- ❌ No tiene SNS Topics
- ❌ No tiene alertas por email

**PROD:**
- ✅ CloudWatch Alarm: High Error Rate (4xx)
- ✅ CloudWatch Alarm: Server Errors (5xx)
- ✅ CloudWatch Alarm: RDS CPU High
- ✅ SNS Topic para alertas
- ✅ Email subscription configurado

---

### 7. Secrets Manager

**DEV:**
- ❌ No usa Secrets Manager
- Variables de entorno en texto plano

**PROD:**
- ✅ Secrets Manager para `DATABASE_URL`
- ⚠️ `app_secrets` comentado (en período de recuperación)
- Variables sensibles en Secrets Manager

---

## Problemas Identificados en PROD

1. **Internet Gateway y Rutas:**
   - ✅ Configurado correctamente
   - ✅ Ruta a internet existe

2. **Security Group:**
   - ✅ Reglas de egress para HTTPS/HTTP configuradas
   - ✅ Regla para RDS configurada

3. **VPC Connector:**
   - ✅ Configurado
   - ⚠️ Usa subnets que pueden no tener ruta a internet

4. **Secrets Manager:**
   - ⚠️ `app_secrets` en período de recuperación (30 días)
   - ⚠️ Variables de Stripe están en texto plano en lugar de Secrets Manager

---

## Recomendaciones para Recrear PROD

1. **Asegurar acceso a internet:**
   - ✅ Internet Gateway configurado
   - ✅ Ruta a internet configurada
   - ✅ Security Group con egress rules

2. **Secrets Manager:**
   - Esperar a que expire el período de recuperación de `app_secrets`
   - O usar un nombre diferente temporalmente
   - Mover `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` a Secrets Manager

3. **VPC Connector:**
   - Verificar que las subnets tengan ruta a internet
   - Asegurar que las subnets sean públicas o tengan NAT Gateway

4. **Configuración de App Runner:**
   - Agregar `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` a `runtime_environment_secrets`
   - Actualizar `secrets_manager_arns` para incluir `app_secrets`

---

## Checklist para Recrear PROD

- [ ] Verificar que Internet Gateway existe y está configurado
- [ ] Verificar que route table tiene ruta a `0.0.0.0/0`
- [ ] Verificar que Security Group tiene reglas de egress (HTTPS/HTTP)
- [ ] Verificar que subnets del VPC Connector tienen acceso a internet
- [ ] Configurar Secrets Manager para `app_secrets` (o usar nombre diferente)
- [ ] Agregar `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` a Secrets Manager
- [ ] Actualizar `runtime_environment_secrets` en módulo App Runner
- [ ] Verificar que RDS está configurado como privado
- [ ] Verificar que VPC Connector está configurado
- [ ] Probar conexión a Stripe API
- [ ] Probar cálculo de taxes (GRT API)
