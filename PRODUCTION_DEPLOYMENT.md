# 🚀 Guía de Despliegue a Producción

Este documento contiene todos los pasos necesarios para desplegar el ambiente de producción después de probar en dev.

---

## 📋 Contexto del Proyecto

### Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                martindigisolutions/landa-website-api             │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
                      │ push to dev           │ push to main
                      ▼                       ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│         GitHub Actions          │ │         GitHub Actions          │
│    Build & Push Docker Image    │ │    Build & Push Docker Image    │
└─────────────────┬───────────────┘ └─────────────────┬───────────────┘
                  │                                   │
                  ▼                                   ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│      ECR (Dev Account)          │ │      ECR (Prod Account)         │
│         775681068353            │ │         553938786984            │
└─────────────────┬───────────────┘ └─────────────────┬───────────────┘
                  │                                   │
                  │ auto-deploy                       │ auto-deploy
                  ▼                                   ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│       App Runner (Dev)          │ │       App Runner (Prod)         │
│  izt8cc3pe8.us-west-2           │ │      (pendiente crear)          │
└─────────────────┬───────────────┘ └─────────────────┬───────────────┘
                  │                                   │
                  ▼                                   ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│      RDS PostgreSQL (Dev)       │ │      RDS PostgreSQL (Prod)      │
│  landa-beauty-api-dev-db        │ │      (pendiente crear)          │
│  db.t3.micro - $15/mes          │ │  db.t3.small - $25-30/mes       │
└─────────────────────────────────┘ └─────────────────────────────────┘
```

### Cuentas AWS

| Ambiente | Account ID | AWS Profile | Rama Git |
|----------|------------|-------------|----------|
| **Dev** | `775681068353` | `dev-account` | `dev` |
| **Prod** | `553938786984` | `default` | `main` |

### URLs Actuales (Dev)

| Servicio | URL |
|----------|-----|
| API Health | https://izt8cc3pe8.us-west-2.awsapprunner.com/api/health |
| RDS Endpoint | `landa-beauty-api-dev-db.c3wogscakv5t.us-west-2.rds.amazonaws.com:5432` |
| ECR Repository | `775681068353.dkr.ecr.us-west-2.amazonaws.com/landa-beauty-api-dev-api` |

---

## 💰 Costos Estimados de Producción

| Servicio | Configuración | Costo Mensual |
|----------|---------------|---------------|
| RDS PostgreSQL | db.t3.small, Single-AZ | ~$25-30/mes |
| RDS PostgreSQL | db.t3.small, Multi-AZ | ~$50-60/mes |
| App Runner | 1 vCPU, 2GB RAM, 1 instancia | ~$5-10/mes |
| App Runner | Escalado (por uso) | Variable |
| **Total Mínimo** | | **~$30-40/mes** |
| **Total con Multi-AZ** | | **~$55-70/mes** |

---

## 🔧 Pre-requisitos

### 1. GitHub Secrets Configurados

Los siguientes secrets deben estar configurados en GitHub (Settings → Secrets → Actions):

**Dev (ya configurados ✅):**
- `DEV_AWS_ACCOUNT_ID` = `775681068353`
- `DEV_AWS_ACCESS_KEY_ID` = (del usuario `github-actions-ecr`)
- `DEV_AWS_SECRET_ACCESS_KEY` = (del usuario `github-actions-ecr`)
- `DEV_ECR_REPOSITORY` = `landa-beauty-api-dev-api`

**Prod (PENDIENTE ❌):**
- `PROD_AWS_ACCOUNT_ID` = `553938786984`
- `PROD_AWS_ACCESS_KEY_ID` = (crear usuario IAM)
- `PROD_AWS_SECRET_ACCESS_KEY` = (crear usuario IAM)
- `PROD_ECR_REPOSITORY` = `landa-beauty-api-api`

### 2. Usuario IAM en Cuenta de Producción

Crear en la cuenta de producción (`553938786984`):

1. **IAM → Policies → Create policy**
   - Name: `GitHubActionsECRPush`
   - JSON:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "ECRAuth",
         "Effect": "Allow",
         "Action": "ecr:GetAuthorizationToken",
         "Resource": "*"
       },
       {
         "Sid": "ECRPush",
         "Effect": "Allow",
         "Action": [
           "ecr:BatchCheckLayerAvailability",
           "ecr:GetDownloadUrlForLayer",
           "ecr:BatchGetImage",
           "ecr:PutImage",
           "ecr:InitiateLayerUpload",
           "ecr:UploadLayerPart",
           "ecr:CompleteLayerUpload"
         ],
         "Resource": "arn:aws:ecr:us-west-2:*:repository/landa-beauty-api*"
       }
     ]
   }
   ```

2. **IAM → Users → Create user**
   - Name: `github-actions-ecr`
   - Attach policy: `GitHubActionsECRPush`
   - Create Access Key → Application outside AWS
   - **Guardar las credenciales**

---

## 📝 Pasos para Desplegar Producción

### Paso 1: Crear archivo de variables

```powershell
cd "d:\Martin Digital Solutions\Landa Beauty Supply\landa-website-api\terraform\environments\prod"
copy terraform.tfvars.example terraform.tfvars
```

### Paso 2: Editar terraform.tfvars

Editar `terraform/environments/prod/terraform.tfvars`:

```hcl
# ============================================
# PROD Environment Variables
# ============================================

create_rds = true

# Database credentials - USAR PASSWORD SEGURO
db_name     = "landa_prod"
db_username = "landa_admin"
db_password = "TU_PASSWORD_SEGURO_AQUI"  # Sin caracteres especiales problemáticos

# Configuración RDS
rds_instance_class = "db.t3.small"   # Más potente que dev
rds_multi_az       = false           # true para alta disponibilidad (~2x costo)
```

### Paso 3: Inicializar Terraform

```powershell
cd "d:\Martin Digital Solutions\Landa Beauty Supply\landa-website-api\terraform\environments\prod"
terraform init
```

### Paso 4: Ver el plan

```powershell
terraform plan
```

Deberías ver que se crearán:
- ECR Repository
- IAM Roles (2)
- Security Group
- DB Subnet Group
- RDS Instance
- Auto Scaling Configuration
- App Runner Service

### Paso 5: Aplicar (crear infraestructura)

```powershell
terraform apply
```

**Tiempo estimado:** ~10-15 minutos (RDS toma tiempo)

### Paso 6: Subir primera imagen Docker

El App Runner necesita una imagen inicial. Opciones:

**Opción A: Push manual (primera vez)**

```powershell
# Login a ECR de producción
aws ecr get-login-password --region us-west-2 --profile default | docker login --username AWS --password-stdin 553938786984.dkr.ecr.us-west-2.amazonaws.com

# Build
cd "d:\Martin Digital Solutions\Landa Beauty Supply\landa-website-api"
docker build -t landa-api .

# Tag y Push
docker tag landa-api:latest 553938786984.dkr.ecr.us-west-2.amazonaws.com/landa-beauty-api-api:latest
docker push 553938786984.dkr.ecr.us-west-2.amazonaws.com/landa-beauty-api-api:latest
```

**Opción B: Merge a main (si GitHub Actions ya está configurado)**

```bash
git checkout main
git merge dev
git push origin main
```

### Paso 7: Configurar GitHub Secrets

En GitHub → Settings → Secrets → Actions, agregar:

| Secret | Valor |
|--------|-------|
| `PROD_AWS_ACCOUNT_ID` | `553938786984` |
| `PROD_AWS_ACCESS_KEY_ID` | Del usuario IAM creado |
| `PROD_AWS_SECRET_ACCESS_KEY` | Del usuario IAM creado |
| `PROD_ECR_REPOSITORY` | `landa-beauty-api-api` |

### Paso 8: Verificar despliegue

```powershell
# Obtener la URL del servicio
cd "d:\Martin Digital Solutions\Landa Beauty Supply\landa-website-api\terraform\environments\prod"
terraform output service_url

# Test health check
curl [URL]/api/health
```

---

## 🔄 Flujo de CI/CD Después del Setup

Una vez configurado todo:

```
Push a rama 'main' 
    → GitHub Actions detecta el push
    → Build Docker image
    → Push a ECR (prod)
    → App Runner detecta nueva imagen
    → Auto-deploy (~3 min)
```

---

## 🗂️ Estructura de Archivos Terraform

```
terraform/
├── modules/
│   ├── apprunner/          # App Runner + ECR
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── rds/                # PostgreSQL RDS
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/                # ✅ YA DESPLEGADO
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── terraform.tfvars.example
│   └── prod/               # ❌ PENDIENTE
│       ├── main.tf
│       ├── terraform.tfvars.example
│       └── (crear terraform.tfvars)
```

---

## ⚠️ Notas Importantes

1. **NO commitear terraform.tfvars** - Contiene passwords
2. **El archivo .gitignore ya excluye:**
   - `*.tfvars` (excepto `.example`)
   - `*.tfstate`
   - `.terraform/`

3. **Variables de entorno sensibles en App Runner:**
   - `DATABASE_URL` - Se configura automáticamente desde Terraform
   - `SECRET_KEY` - Configurar manualmente en App Runner Console
   - `STRIPE_SECRET_KEY` - Configurar manualmente en App Runner Console
   - `STRIPE_WEBHOOK_SECRET` - Configurar manualmente en App Runner Console

4. **Para configurar secrets manualmente en App Runner:**
   - AWS Console → App Runner → Tu servicio → Configuration
   - Environment variables → Add

---

## 🔙 Rollback

Si algo sale mal:

```powershell
cd "d:\Martin Digital Solutions\Landa Beauty Supply\landa-website-api\terraform\environments\prod"
terraform destroy
```

**CUIDADO:** Esto eliminará RDS y todos los datos. Asegúrate de tener backup.

---

## 📞 Contacto y Referencias

- **Repositorio:** https://github.com/martindigisolutions/landa-website-api
- **GitHub Actions:** `.github/workflows/deploy.yml`
- **Documentación de Secrets:** `.github/GITHUB_SECRETS.md`

---

*Documento creado: Diciembre 2024*
*Última actualización: Al desplegar producción*
