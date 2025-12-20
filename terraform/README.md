# 🚀 Terraform - AWS App Runner (desde GitHub)

Configuración de Terraform para desplegar la API directamente desde GitHub a AWS App Runner.

## 📋 Prerequisitos

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [AWS CLI](https://aws.amazon.com/cli/) configurado con credenciales
- Repositorio en GitHub

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS                                  │
│                                                              │
│  ┌─────────────┐         ┌─────────────────┐                │
│  │   GitHub    │────────▶│   App Runner    │                │
│  │ (tu código) │  push   │   (API)         │                │
│  └─────────────┘         └────────┬────────┘                │
│                                   │                          │
│                    ┌──────────────┼──────────────┐          │
│                    ▼              ▼              ▼          │
│              ┌──────────┐  ┌───────────┐  ┌──────────┐     │
│              │   SSM    │  │    RDS    │  │  Stripe  │     │
│              │ (secrets)│  │(PostgreSQL)│  │  (API)   │     │
│              └──────────┘  └───────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Despliegue

### Paso 1: Crear conexión de GitHub en AWS

**IMPORTANTE**: Esto debe hacerse ANTES de ejecutar Terraform.

1. Ve a **AWS Console** → **App Runner** → **GitHub connections**
2. Click **"Create connection"**
3. Nombre: `github-connection` (o el que prefieras)
4. Click **"Install another"** para autorizar GitHub
5. Selecciona tu cuenta/organización de GitHub
6. **Copia el ARN** de la conexión (lo necesitarás)

### Paso 2: Configurar variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars`:

```hcl
# Pega el ARN de la conexión de GitHub
github_connection_arn = "arn:aws:apprunner:us-east-1:123456789:connection/github-connection/abc123"
github_repository_url = "https://github.com/tu-usuario/landa-website-api"
github_branch         = "main"

# Tus secrets
database_url = "postgresql://user:pass@host:5432/db"
secret_key   = "tu-clave-secreta-jwt"
# ... etc
```

### Paso 3: Ejecutar Terraform

```bash
# Inicializar
terraform init

# Ver plan
terraform plan

# Aplicar
terraform apply
```

### Paso 4: Verificar

```bash
# Obtener URL
terraform output app_runner_url

# Probar health check
curl $(terraform output -raw health_check_url)
```

## 📦 Recursos Creados

| Recurso | Descripción |
|---------|-------------|
| `aws_apprunner_service` | Servicio de App Runner conectado a GitHub |
| `aws_apprunner_auto_scaling_configuration_version` | Configuración de auto-scaling |
| `aws_iam_role` | Rol IAM para acceso a SSM |
| `aws_ssm_parameter` (x4) | Secrets en SSM Parameter Store |

## 🔄 Despliegues Automáticos

Con `auto_deploy = true` (por defecto), cada push a la rama configurada desplegará automáticamente.

```bash
# Desde tu máquina local
git add .
git commit -m "Nueva feature"
git push origin main

# App Runner detecta el push y despliega automáticamente 🚀
```

## 🔐 Manejo de Secrets

### Opción 1: SSM Parameter Store (Recomendado)

```hcl
use_ssm_secrets = true
database_url    = "postgresql://..."
secret_key      = "..."
```

Los secrets se guardan encriptados en SSM y App Runner los lee automáticamente.

### Opción 2: Variables directas en App Runner Console

```hcl
use_ssm_secrets = false
```

Luego configura las variables manualmente en AWS Console → App Runner → Tu servicio → Configuration.

## 🗑️ Destruir

```bash
terraform destroy
```

## 💡 Comandos Útiles

```bash
# Ver outputs
terraform output

# Ver URL de la API
terraform output app_runner_url

# Ver estado
terraform show

# Actualizar sin recrear
terraform apply -auto-approve
```

## 📊 Costos Estimados

| Servicio | Costo Aproximado |
|----------|------------------|
| App Runner | ~$25-50/mes (1 vCPU, 2GB, tráfico bajo) |
| SSM Parameters | Gratis (hasta 10,000) |
| **Total** | **~$25-50/mes** |

## ⚠️ Notas

1. La conexión de GitHub debe crearse manualmente primero
2. El primer despliegue toma ~5 minutos
3. Los secrets en `terraform.tfvars` nunca deben subirse a git
4. Para múltiples ambientes, usa workspaces: `terraform workspace new staging`
