# Revisión de Seguridad y Costos - Infraestructura Terraform

**Fecha de Revisión:** 2026-01-05  
**Ambiente:** Producción  
**Revisor:** AI Assistant

---

## 📋 Resumen Ejecutivo

Esta revisión identifica **problemas críticos de seguridad** y oportunidades de **optimización de costos** en la infraestructura de Terraform antes del despliegue a producción.

### ⚠️ Problemas Críticos Encontrados: 8
### 💰 Optimizaciones de Costo: 5
### 🔧 Mejoras Recomendadas: 12

---

## 🔴 PROBLEMAS CRÍTICOS DE SEGURIDAD

### 1. **RDS Públicamente Accesible con CIDR Abierto** ⚠️ CRÍTICO

**Ubicación:** `terraform/environments/prod/main.tf:85-86`

```terraform
allowed_cidr_blocks = ["0.0.0.0/0"]  # ❌ MUY INSEGURO
publicly_accessible = true
```

**Problema:**
- RDS está expuesto a internet con acceso desde cualquier IP
- Cualquier persona puede intentar conectarse a la base de datos
- Riesgo de ataques de fuerza bruta y acceso no autorizado

**Impacto:** 🔴 CRÍTICO - La base de datos está completamente expuesta

**Solución:**
```terraform
# Opción 1: VPC Endpoint (RECOMENDADO para App Runner)
allowed_cidr_blocks = [data.aws_vpc.default.cidr_block]  # Solo VPC
publicly_accessible = false

# Opción 2: Security Group específico para App Runner
# Crear VPC endpoint o usar VPC Connector
```

**Costo adicional:** ~$7-10/mes por VPC endpoint (si es necesario)

---

### 2. **Secrets en Variables de Entorno en Texto Plano** ⚠️ CRÍTICO

**Ubicación:** `terraform/modules/apprunner/main.tf:107-116`

```terraform
runtime_environment_variables = {
  DATABASE_URL = module.rds[0].database_url  # ❌ Password en texto plano
  SECRET_KEY = var.secret_key                 # ❌ En texto plano
}
```

**Problema:**
- Las contraseñas y secretos están en variables de entorno visibles
- Cualquiera con acceso a App Runner puede ver estos valores
- No hay rotación automática de secretos
- Logs pueden contener estos valores

**Impacto:** 🔴 CRÍTICO - Exposición de credenciales sensibles

**Solución:**
```terraform
# Usar AWS Secrets Manager o SSM Parameter Store
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}-secrets"
}

# En App Runner, usar secrets en lugar de env vars
source_configuration {
  image_repository {
    image_configuration {
      runtime_environment_secrets = {
        DATABASE_URL = aws_secretsmanager_secret.app_secrets.arn
        SECRET_KEY   = aws_secretsmanager_secret.secret_key.arn
      }
    }
  }
}
```

**Costo adicional:** ~$0.40/mes por secret en Secrets Manager

---

### 3. **Password de Base de Datos en Terraform State** ⚠️ ALTO

**Ubicación:** `terraform/modules/rds/main.tf:65`

```terraform
password = var.db_password  # Se guarda en terraform.tfstate
```

**Problema:**
- El password se guarda en el estado de Terraform (terraform.tfstate)
- Si el estado se compromete, el password está expuesto
- No hay rotación automática

**Solución:**
```terraform
# Usar AWS Secrets Manager para generar y rotar passwords
resource "aws_db_instance" "main" {
  # ...
  manage_master_user_password = true
  master_user_secret {
    kms_key_id = aws_kms_key.rds.arn
  }
}
```

**Costo adicional:** $0 (incluido en RDS)

---

### 4. **Falta de Encriptación en Tránsito para RDS** ⚠️ MEDIO

**Ubicación:** `terraform/modules/rds/main.tf:60`

```terraform
storage_encrypted = true  # ✅ Encriptación en reposo
# ❌ Falta: enforce_ssl = true
```

**Problema:**
- No se fuerza SSL/TLS para conexiones a RDS
- Conexiones pueden ser interceptadas
- Datos sensibles pueden ser expuestos

**Solución:**
```terraform
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-pg"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

resource "aws_db_instance" "main" {
  # ...
  db_parameter_group_name = aws_db_parameter_group.main.name
}
```

**Costo adicional:** $0

---

### 5. **IAM Roles sin Principio de Menor Privilegio** ⚠️ MEDIO

**Ubicación:** `terraform/modules/apprunner/main.tf:73-90`

**Problema:**
- El rol de instancia de App Runner no tiene políticas definidas
- Podría tener permisos excesivos si se agregan políticas más adelante
- No hay políticas específicas para los recursos que necesita

**Solución:**
```terraform
# Crear política específica solo para lo que necesita
resource "aws_iam_role_policy" "apprunner_instance" {
  name = "${var.project_name}-apprunner-policy"
  role = aws_iam_role.apprunner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:secretsmanager:*:*:secret:${var.project_name}*",
          "arn:aws:ssm:*:*:parameter/${var.project_name}/*"
        ]
      }
    ]
  })
}
```

**Costo adicional:** $0

---

### 6. **Health Check Path Puede No Existir** ⚠️ MEDIO

**Ubicación:** `terraform/modules/apprunner/main.tf:136`

```terraform
path = "/api/health"  # ¿Existe este endpoint?
```

**Problema:**
- Si el endpoint `/api/health` no existe, App Runner marcará el servicio como no saludable
- El servicio no iniciará correctamente

**Verificación necesaria:**
- Confirmar que existe el endpoint `/api/health` o `/health` en la aplicación

**Solución:**
```python
# En main.py o routers
@router.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Costo adicional:** $0

---

### 7. **Falta de Backup Automático para RDS** ⚠️ MEDIO

**Ubicación:** `terraform/modules/rds/main.tf:74-75`

```terraform
backup_retention_period = var.backup_retention_period  # Default: 7 días
backup_window = "03:00-04:00"  # Ventana fija
```

**Problema:**
- Solo 7 días de retención puede ser insuficiente para producción
- No hay copias de seguridad cross-region
- No hay automatización de restauración

**Solución:**
```terraform
backup_retention_period = 30  # 30 días para producción
copy_tags_to_snapshot = true

# Opcional: Habilitar backup cross-region
resource "aws_db_instance_automated_backups_replication" "cross_region" {
  source_db_instance_arn = aws_db_instance.main.arn
  kms_key_id             = aws_kms_key.backup.arn
}
```

**Costo adicional:** ~$5-10/mes por storage adicional de backups

---

### 8. **Falta de Remote State Backend** ⚠️ MEDIO

**Ubicación:** `terraform/environments/prod/main.tf:15-21`

```terraform
# backend "s3" {
#   # Comentado - estado local
# }
```

**Problema:**
- El estado de Terraform se guarda localmente
- Riesgo de pérdida del estado
- No hay bloqueo de estado (state locking)
- Múltiples personas pueden modificar simultáneamente

**Solución:**
```terraform
terraform {
  backend "s3" {
    bucket         = "landa-terraform-state-prod"
    key            = "prod/apprunner.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "landa-terraform-locks"  # Para state locking
  }
}
```

**Costo adicional:** ~$0.50/mes (S3 + DynamoDB)

---

## 💰 OPTIMIZACIONES DE COSTOS

### 1. **RDS Instance Class - Reducir Tamaño Inicial**

**Actual:** `db.t3.small` (~$15/mes)  
**Recomendado:** `db.t3.micro` (~$7.50/mes) para empezar

**Justificación:**
- Para una API pequeña/mediana, `db.t3.micro` es suficiente inicialmente
- RDS puede escalar automáticamente si es necesario
- Puedes cambiar a `db.t3.small` cuando el tráfico aumente

**Ahorro:** ~$7.50/mes (~$90/año)

**Código:**
```terraform
variable "rds_instance_class" {
  default = "db.t3.micro"  # Empezar pequeño
}
```

---

### 2. **App Runner - Reducir CPU/Memory Inicial**

**Actual:** `cpu = "1024"`, `memory = "2048"`  
**Recomendado:** `cpu = "512"`, `memory = "1024"` para empezar

**Justificación:**
- App Runner escala automáticamente
- Puedes empezar con menos recursos y aumentar si es necesario
- Para una API Python/FastAPI, 512 CPU y 1GB RAM suele ser suficiente

**Ahorro:** ~$20-30/mes (~$240-360/año)

**Código:**
```terraform
variable "cpu" {
  default = "512"  # Empezar con 0.5 vCPU
}

variable "memory" {
  default = "1024"  # Empezar con 1GB
}
```

---

### 3. **Auto-Scaling - Ajustar Límites**

**Actual:** `min_instances = 1`, `max_instances = 10`  
**Recomendado:** `min_instances = 1`, `max_instances = 5`

**Justificación:**
- 10 instancias máximas es excesivo para empezar
- Con 5 instancias puedes manejar ~500-1000 requests/segundo
- Puedes aumentar el límite cuando sea necesario

**Ahorro:** Potencial de $50-100/mes si se alcanza el máximo (depende del tráfico)

**Código:**
```terraform
variable "max_instances" {
  default = 5  # Reducir de 10 a 5
}
```

---

### 4. **RDS Storage - Optimizar Autoscaling**

**Actual:** `allocated_storage = 50GB`, `max_allocated_storage = 200GB`  
**Recomendado:** `allocated_storage = 20GB`, `max_allocated_storage = 100GB`

**Justificación:**
- 50GB inicial es mucho para empezar
- gp3 storage es más barato y eficiente
- El autoscaling cubrirá el crecimiento

**Ahorro:** ~$3-5/mes en storage no utilizado

**Código:**
```terraform
allocated_storage     = 20   # Empezar con 20GB
max_allocated_storage = 100  # Máximo 100GB
```

---

### 5. **ECR Lifecycle Policy - Ya Implementado ✅**

**Ubicación:** `terraform/modules/apprunner/main.tf:22-41`

**Estado:** ✅ Ya tiene política de lifecycle (mantiene últimas 5 imágenes)

**Costo:** $0.10/GB/mes para imágenes almacenadas

---

## 🔧 MEJORAS RECOMENDADAS

### 1. **Agregar CloudWatch Alarms**

```terraform
resource "aws_cloudwatch_metric_alarm" "app_runner_errors" {
  alarm_name          = "${var.project_name}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4xx"
  namespace           = "AWS/AppRunner"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "Alert when error rate is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

**Costo:** $0.10/alarm/mes

---

### 2. **Agregar VPC Connector para App Runner → RDS**

```terraform
resource "aws_apprunner_vpc_connector" "main" {
  vpc_connector_name = "${var.project_name}-vpc-connector"
  subnets            = var.subnet_ids
  security_groups    = [aws_security_group.apprunner.id]
}
```

**Costo:** ~$0.01/hora (~$7/mes)

---

### 3. **Habilitar Multi-AZ para RDS en Producción**

```terraform
multi_az = true  # Para alta disponibilidad
```

**Costo adicional:** ~$15/mes (duplica el costo de RDS)

**Recomendación:** Habilitar solo si es crítico para el negocio

---

### 4. **Agregar WAF para Protección DDoS**

```terraform
resource "aws_wafv2_web_acl" "main" {
  name  = "${var.project_name}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    action {
      block {}
    }
  }
}
```

**Costo:** ~$5/mes + $1/million requests

---

### 5. **Agregar KMS para Encriptación de Secrets**

```terraform
resource "aws_kms_key" "secrets" {
  description = "KMS key for app secrets"
  enable_key_rotation = true
}
```

**Costo:** $1/mes por clave

---

### 6. **Agregar Tags de Costo**

```terraform
tags = merge(var.tags, {
  CostCenter    = "Engineering"
  BillingCode   = "LAND-API-PROD"
  Owner         = "devops@landabeautysupply.com"
})
```

**Costo:** $0 (ayuda a trackear costos)

---

### 7. **Configurar Log Retention**

```terraform
resource "aws_cloudwatch_log_group" "apprunner" {
  name              = "/aws/apprunner/${var.project_name}"
  retention_in_days = 30  # Reducir de default (never expire)
}
```

**Ahorro:** ~$5-10/mes en logs antiguos

---

### 8. **Agregar Database Connection Pooling**

**Recomendación:** Usar PgBouncer o RDS Proxy

```terraform
resource "aws_db_proxy" "main" {
  name                   = "${var.project_name}-proxy"
  engine_family          = "POSTGRESQL"
  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db.arn
  }
}
```

**Costo:** ~$15/mes (pero reduce carga en RDS)

---

### 9. **Habilitar Performance Insights para RDS**

```terraform
performance_insights_enabled = true
performance_insights_retention_period = 7  # días
```

**Costo:** $0 para db.t3.micro, ~$10/mes para instancias más grandes

---

### 10. **Agregar SNS para Alertas**

```terraform
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "devops@landabeautysupply.com"
}
```

**Costo:** $0 (primeros 100,000 notificaciones/mes gratis)

---

### 11. **Configurar Auto Minor Version Upgrade**

```terraform
auto_minor_version_upgrade = true  # Para RDS
```

**Costo:** $0 (mejora seguridad sin costo)

---

### 12. **Agregar Resource Limits**

```terraform
# En App Runner, configurar límites de recursos
resource "aws_apprunner_service" "api" {
  # ...
  instance_configuration {
    cpu    = var.cpu
    memory = var.memory
  }
}
```

**Costo:** $0 (previene costos inesperados)

---

## 📊 ESTIMACIÓN DE COSTOS MENSUALES

### Configuración Actual (Estimada):
- **App Runner:** ~$50-80/mes (1-10 instancias, 1 vCPU, 2GB RAM)
- **RDS db.t3.small:** ~$15/mes
- **RDS Storage (50GB gp3):** ~$4/mes
- **RDS Backups (7 días):** ~$2/mes
- **ECR Storage:** ~$1/mes
- **CloudWatch Logs:** ~$5-10/mes
- **Total Estimado:** ~$77-112/mes

### Configuración Optimizada (Recomendada):
- **App Runner:** ~$30-50/mes (1-5 instancias, 0.5 vCPU, 1GB RAM)
- **RDS db.t3.micro:** ~$7.50/mes
- **RDS Storage (20GB gp3):** ~$1.60/mes
- **RDS Backups (30 días):** ~$3/mes
- **ECR Storage:** ~$1/mes
- **CloudWatch Logs:** ~$5/mes
- **Secrets Manager:** ~$1/mes
- **VPC Endpoint (si necesario):** ~$7/mes
- **Total Estimado:** ~$57-75/mes

**Ahorro Potencial:** ~$20-37/mes (~$240-444/año)

---

## ✅ CHECKLIST PRE-DESPLIEGUE

### Seguridad:
- [ ] Cambiar RDS a `publicly_accessible = false`
- [ ] Restringir `allowed_cidr_blocks` a VPC solamente
- [ ] Mover secrets a AWS Secrets Manager
- [ ] Habilitar SSL forzado en RDS
- [ ] Configurar IAM roles con menor privilegio
- [ ] Habilitar encriptación KMS para secrets
- [ ] Configurar remote state backend en S3
- [ ] Agregar WAF para protección DDoS

### Costos:
- [ ] Reducir RDS a `db.t3.micro` inicialmente
- [ ] Reducir App Runner a 512 CPU / 1GB RAM
- [ ] Reducir `max_instances` a 5
- [ ] Reducir RDS storage inicial a 20GB
- [ ] Configurar log retention (30 días)
- [ ] Agregar tags de costo

### Operaciones:
- [ ] Configurar CloudWatch alarms
- [ ] Configurar SNS para alertas
- [ ] Verificar que existe endpoint `/health`
- [ ] Configurar backup retention (30 días)
- [ ] Habilitar auto minor version upgrade
- [ ] Documentar proceso de despliegue

---

## 🚨 PRIORIDADES

### 🔴 CRÍTICO (Hacer ANTES de producción):
1. Cambiar RDS a privado (`publicly_accessible = false`)
2. Mover secrets a Secrets Manager
3. Configurar remote state backend
4. Verificar endpoint `/health` existe

### 🟡 ALTO (Hacer en primera semana):
5. Habilitar SSL forzado en RDS
6. Configurar IAM con menor privilegio
7. Agregar CloudWatch alarms
8. Optimizar costos (reducir recursos iniciales)

### 🟢 MEDIO (Hacer cuando sea posible):
9. Agregar WAF
10. Habilitar Multi-AZ (si es crítico)
11. Configurar VPC Connector
12. Agregar RDS Proxy

---

## 📝 PRÓXIMOS PASOS

1. **Crear archivo de correcciones:** `terraform/environments/prod/main.tf.fixed`
2. **Implementar cambios críticos de seguridad**
3. **Aplicar optimizaciones de costo**
4. **Probar en ambiente de staging primero**
5. **Documentar cambios y procedimientos**

---

## 📚 Referencias

- [AWS App Runner Pricing](https://aws.amazon.com/apprunner/pricing/)
- [RDS Pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

