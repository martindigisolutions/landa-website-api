# Terraform - AWS App Runner Infrastructure

Este directorio contiene la infraestructura como código para desplegar la API en AWS App Runner.

## 📁 Estructura

```
terraform/
├── modules/
│   └── apprunner/           # Módulo reutilizable
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/                 # Configuración de desarrollo
│   │   └── main.tf
│   └── prod/                # Configuración de producción
│       └── main.tf
└── README.md
```

## 🌍 Ambientes

| Ambiente | AWS Account | Rama Git | ECR Repository |
|----------|-------------|----------|----------------|
| Dev | 775681068353 | `dev` | landa-beauty-api-dev-api |
| Prod | 553938786984 | `main` | landa-beauty-api |

## 🚀 Despliegue Inicial

### 1. Prerequisitos

- Terraform >= 1.0
- AWS CLI configurado con perfiles `dev-account` y `default`
- Docker instalado

### 2. Desplegar Dev

```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```

### 3. Desplegar Prod

```bash
cd terraform/environments/prod
terraform init
terraform plan
terraform apply
```

### 4. Push Inicial de Docker Image

Después del `terraform apply`, necesitas subir la primera imagen:

```bash
# Para Dev
cd ../../..  # volver a la raíz del proyecto

# Login a ECR
aws ecr get-login-password --region us-west-2 --profile dev-account | docker login --username AWS --password-stdin 775681068353.dkr.ecr.us-west-2.amazonaws.com

# Build y push
docker build -t landa-api .
docker tag landa-api:latest 775681068353.dkr.ecr.us-west-2.amazonaws.com/landa-beauty-api-dev-api:latest
docker push 775681068353.dkr.ecr.us-west-2.amazonaws.com/landa-beauty-api-dev-api:latest
```

Para Prod (usa profile default y account 553938786984).

## 🔄 CI/CD Automático

Una vez configurado GitHub Actions, los deploys son automáticos:

```
Push a rama 'dev'  → Build → ECR Dev  → App Runner Dev  auto-deploy
Push a rama 'main' → Build → ECR Prod → App Runner Prod auto-deploy
```

### Configurar GitHub Secrets

Ve a: GitHub → Settings → Secrets and variables → Actions → New repository secret

**Secrets para Dev:**
| Secret | Valor |
|--------|-------|
| `DEV_AWS_ACCOUNT_ID` | `775681068353` |
| `DEV_AWS_ACCESS_KEY_ID` | Tu access key de dev |
| `DEV_AWS_SECRET_ACCESS_KEY` | Tu secret key de dev |
| `DEV_ECR_REPOSITORY` | `landa-beauty-api-dev-api` |

**Secrets para Prod:**
| Secret | Valor |
|--------|-------|
| `PROD_AWS_ACCOUNT_ID` | `553938786984` |
| `PROD_AWS_ACCESS_KEY_ID` | Tu access key de prod |
| `PROD_AWS_SECRET_ACCESS_KEY` | Tu secret key de prod |
| `PROD_ECR_REPOSITORY` | `landa-beauty-api` |

### Crear IAM User para GitHub Actions

En cada cuenta AWS, crea un usuario IAM con estos permisos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
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

## 🔧 Configuración de Variables de Entorno

Las variables de entorno sensibles (DATABASE_URL, SECRET_KEY, etc.) se configuran manualmente en la consola de App Runner:

1. Ve a AWS Console → App Runner → Tu servicio
2. Click en "Configuration"
3. En "Environment variables", agrega:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`

## 📊 Monitoreo

```bash
# Ver estado del servicio (dev)
aws apprunner list-services --profile dev-account --region us-west-2

# Ver logs
aws apprunner list-operations --service-arn <ARN> --profile dev-account --region us-west-2
```

## 🗑️ Destruir Infraestructura

```bash
# Dev
cd terraform/environments/dev
terraform destroy

# Prod
cd terraform/environments/prod
terraform destroy
```

