# Guía de Despliegue - Terraform Producción

**Última actualización:** 2026-01-05

Esta guía te lleva paso a paso para desplegar la infraestructura de producción de forma segura.

---

## 📋 Prerequisitos

1. **AWS CLI configurado** con un profile (default o personalizado)
2. **Terraform >= 1.0** instalado
3. **Permisos IAM** suficientes para crear recursos
4. **Credenciales de base de datos** listas

---

## 🚀 Paso 1: Configurar Remote State Backend

El remote state backend permite:
- ✅ Compartir estado entre miembros del equipo
- ✅ State locking (evita conflictos)
- ✅ Versionado del estado
- ✅ Encriptación automática

### Opción A: Usar Script Automático (Recomendado)

```bash
cd terraform/environments/prod

# Hacer el script ejecutable (Linux/Mac)
chmod +x setup-backend.sh

# Ejecutar (ajusta AWS_PROFILE si es necesario)
AWS_PROFILE=default ./setup-backend.sh
```

### Opción B: Crear Manualmente

```bash
# Crear bucket S3
aws s3 mb s3://landa-terraform-state-prod --region us-west-2

# Habilitar versionado
aws s3api put-bucket-versioning \
  --bucket landa-terraform-state-prod \
  --versioning-configuration Status=Enabled

# Habilitar encriptación
aws s3api put-bucket-encryption \
  --bucket landa-terraform-state-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
    }]
  }'

# Crear tabla DynamoDB
aws dynamodb create-table \
  --table-name landa-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2
```

### Verificar Backend

El backend ya está configurado en `main.tf`. Si prefieres no usarlo inicialmente, comenta el bloque `backend "s3"`.

---

## 🔐 Paso 2: Configurar Variables

1. **Copiar el archivo de ejemplo:**
   ```bash
   cd terraform/environments/prod
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Editar `terraform.tfvars`** con tus valores:
   ```hcl
   # RDS Configuration
   create_rds = true
   db_name     = "landa_prod"
   db_username = "landa_admin"
   db_password = "TuPasswordMuySeguro123!"  # ⚠️ CAMBIAR

   # Infrastructure
   use_secrets_manager = true
   use_vpc_connector   = true
   alert_email         = "tu-email@landabeautysupply.com"
   ```

3. **⚠️ IMPORTANTE:** Agregar `terraform.tfvars` a `.gitignore`:
   ```bash
   echo "terraform.tfvars" >> .gitignore
   ```

---

## 🏗️ Paso 3: Inicializar Terraform

```bash
cd terraform/environments/prod

# Inicializar Terraform
terraform init

# Si ya tienes estado local y quieres migrar a S3:
terraform init -migrate-state
```

---

## 📊 Paso 4: Revisar Plan

**SIEMPRE revisa el plan antes de aplicar:**

```bash
terraform plan

# Guardar plan en archivo para revisión
terraform plan -out=tfplan
terraform show tfplan
```

**Verifica:**
- ✅ Recursos que se van a crear
- ✅ Costos estimados
- ✅ Configuración de seguridad (RDS privado, SSL, etc.)

---

## 🚀 Paso 5: Aplicar Infraestructura

```bash
# Aplicar cambios
terraform apply

# O usar el plan guardado
terraform apply tfplan
```

**Tiempo estimado:** 10-15 minutos (RDS tarda más)

**Durante el despliegue:**
- Se creará ECR repository
- Se creará App Runner service
- Se creará RDS instance (si `create_rds = true`)
- Se creará VPC Connector (si `use_vpc_connector = true`)
- Se crearán Secrets Manager secrets
- Se crearán CloudWatch alarms

---

## 🔐 Paso 6: Configurar Secrets

Después de `terraform apply`, configura los secrets en Secrets Manager:

### Opción A: Usar Script

```bash
chmod +x setup-secrets.sh
./setup-secrets.sh
```

### Opción B: Manualmente

```bash
# Obtener ARN del secret
SECRET_ARN=$(terraform output -raw app_secrets_arn)

# Crear JSON con secrets
cat > secrets.json <<EOF
{
  "SECRET_KEY": "tu-jwt-secret-key-32-caracteres-minimo",
  "STRIPE_SECRET_KEY": "sk_live_...",
  "STRIPE_WEBHOOK_SECRET": "whsec_..."
}
EOF

# Subir a Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ARN" \
  --secret-string file://secrets.json

# Limpiar
rm secrets.json
```

### Opción C: Usar Variables de Entorno (Temporal)

Si prefieres no usar Secrets Manager inicialmente:
1. Edita `terraform.tfvars`: `use_secrets_manager = false`
2. Los secrets se pasarán como variables de entorno (menos seguro)

---

## 🔗 Paso 7: Configurar VPC Connector (Si RDS es Privado)

Si `use_vpc_connector = true`, el VPC Connector se crea automáticamente.

**Verificar conexión:**
1. App Runner debe poder conectarse a RDS a través del VPC Connector
2. El Security Group de RDS permite conexiones desde el Security Group de App Runner

**Si hay problemas de conexión:**
```bash
# Verificar Security Groups
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=landa-beauty-api*" \
  --query 'SecurityGroups[*].[GroupId,GroupName,Description]'

# Verificar VPC Connector
terraform output vpc_connector_arn
```

---

## 📦 Paso 8: Push Primera Imagen Docker

```bash
# Obtener comando de login
terraform output ecr_login_command

# Ejecutar el comando (copia y pega la salida)
# Ejemplo:
# aws ecr get-login-password --region us-west-2 --profile default | docker login --username AWS --password-stdin 553938786984.dkr.ecr.us-west-2.amazonaws.com

# Obtener URL del repositorio
ECR_URL=$(terraform output -raw ecr_repository_url)

# Build y push
docker build -t landa-api .
docker tag landa-api:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest
```

**App Runner detectará automáticamente el push y desplegará la nueva versión.**

---

## ✅ Paso 9: Verificar Despliegue

### 1. Verificar App Runner

```bash
# Obtener URL del servicio
terraform output service_url

# Probar health check
curl $(terraform output -raw service_url)/api/health
```

**Respuesta esperada:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "Landa Beauty Supply API",
    "version": "1.0.2"
  }
}
```

### 2. Verificar RDS

```bash
# Obtener endpoint
terraform output rds_endpoint

# Probar conexión (desde una instancia EC2 o local con VPN)
psql -h $(terraform output -raw rds_endpoint) -U landa_admin -d landa_prod
```

### 3. Verificar CloudWatch Alarms

```bash
# Listar alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix landa-beauty-api \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output table
```

### 4. Verificar Secrets Manager

```bash
# Listar secrets
aws secretsmanager list-secrets \
  --filters Key=name,Values=landa-beauty-api \
  --query 'SecretList[*].[Name,ARN]' \
  --output table
```

---

## 📧 Paso 10: Configurar Alertas por Email

1. **Verificar suscripción SNS:**
   ```bash
   terraform output sns_topic_arn
   ```

2. **Revisar tu email:** Deberías haber recibido un email de confirmación de SNS

3. **Confirmar suscripción:** Haz click en el link del email

4. **Probar alerta:**
   ```bash
   # Enviar mensaje de prueba
   aws sns publish \
     --topic-arn $(terraform output -raw sns_topic_arn) \
     --message "Test alert from Terraform" \
     --subject "Test Alert"
   ```

---

## 🔄 Actualizaciones Futuras

### Actualizar Infraestructura

```bash
cd terraform/environments/prod

# Ver cambios
terraform plan

# Aplicar
terraform apply
```

### Actualizar Secrets

```bash
# Usar script
./setup-secrets.sh

# O manualmente
aws secretsmanager put-secret-value \
  --secret-id <SECRET_ARN> \
  --secret-string '{"KEY":"value"}'
```

### Actualizar Aplicación

```bash
# Build y push nueva imagen
docker build -t landa-api .
docker tag landa-api:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest

# App Runner detectará y desplegará automáticamente
```

---

## 🛠️ Troubleshooting

### Error: "Backend configuration changed"

```bash
# Si cambiaste el backend, migra el estado
terraform init -migrate-state
```

### Error: "RDS connection timeout"

1. Verificar que VPC Connector está activo
2. Verificar Security Groups permiten conexión
3. Verificar que RDS está en la misma VPC

```bash
# Verificar VPC Connector
aws apprunner list-vpc-connectors

# Verificar Security Groups
terraform output  # Buscar security_group_id
```

### Error: "Secrets Manager access denied"

1. Verificar IAM role de App Runner tiene permisos
2. Verificar que el secret existe
3. Verificar que el ARN es correcto

```bash
# Verificar IAM policy
aws iam get-role-policy \
  --role-name landa-beauty-api-apprunner-instance-role \
  --policy-name landa-beauty-api-apprunner-secrets-policy
```

### App Runner no inicia

1. Verificar logs en CloudWatch
2. Verificar health check endpoint existe
3. Verificar variables de entorno/secrets

```bash
# Ver logs
aws logs tail /aws/apprunner/landa-beauty-api-api --follow
```

---

## 🗑️ Destruir Infraestructura

**⚠️ CUIDADO: Esto eliminará TODOS los recursos**

```bash
# Revisar qué se eliminará
terraform plan -destroy

# Destruir (requiere confirmación)
terraform destroy

# Si RDS tiene deletion_protection, deshabilitarlo primero:
# Editar terraform.tfvars: deletion_protection = false
# terraform apply
# terraform destroy
```

---

## 📊 Costos Estimados

Ver `docs/TERRAFORM_SECURITY_COST_REVIEW.md` para detalles de costos.

**Resumen:**
- App Runner: ~$30-50/mes
- RDS: ~$12/mes
- VPC Connector: ~$7/mes
- Secrets Manager: ~$1/mes
- CloudWatch: ~$5/mes
- **Total: ~$55-75/mes**

---

## 📚 Documentación Relacionada

- `docs/TERRAFORM_SECURITY_COST_REVIEW.md` - Revisión de seguridad y costos
- `docs/TERRAFORM_CHANGES_SUMMARY.md` - Resumen de cambios aplicados
- `terraform/README.md` - Documentación general de Terraform

---

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs de CloudWatch
2. Verifica la configuración en `terraform.tfvars`
3. Revisa los outputs de Terraform: `terraform output`
4. Consulta la documentación de AWS App Runner y RDS

