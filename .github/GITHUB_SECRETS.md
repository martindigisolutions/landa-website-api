# 🔐 GitHub Secrets Configuration

Para que el CI/CD automático funcione, necesitas configurar los siguientes secrets en GitHub.

## 📍 Dónde Configurarlos

1. Ve a tu repositorio en GitHub: https://github.com/martindigisolutions/landa-website-api
2. Click en **Settings** (pestaña)
3. En el menú izquierdo: **Secrets and variables** → **Actions**
4. Click en **New repository secret**

## 🔑 Secrets Requeridos

### Ambiente: Development (rama `dev`)

| Secret Name | Description | Valor |
|-------------|-------------|-------|
| `DEV_AWS_ACCOUNT_ID` | AWS Account ID de desarrollo | `775681068353` |
| `DEV_AWS_ACCESS_KEY_ID` | Access Key del usuario IAM | *(del usuario creado abajo)* |
| `DEV_AWS_SECRET_ACCESS_KEY` | Secret Key del usuario IAM | *(del usuario creado abajo)* |
| `DEV_ECR_REPOSITORY` | Nombre del repositorio ECR | `landa-beauty-api-dev-api` |

### Ambiente: Production (rama `main`)

| Secret Name | Description | Valor |
|-------------|-------------|-------|
| `PROD_AWS_ACCOUNT_ID` | AWS Account ID de producción | `553938786984` |
| `PROD_AWS_ACCESS_KEY_ID` | Access Key del usuario IAM | *(del usuario creado abajo)* |
| `PROD_AWS_SECRET_ACCESS_KEY` | Secret Key del usuario IAM | *(del usuario creado abajo)* |
| `PROD_ECR_REPOSITORY` | Nombre del repositorio ECR | `landa-beauty-api-api` |

---

## 👤 Crear Usuario IAM para GitHub Actions

Repite estos pasos en **cada cuenta AWS** (dev y prod):

### Paso 1: Crear la Policy

1. AWS Console → **IAM** → **Policies** → **Create policy**
2. Click en pestaña **JSON**
3. Pega este contenido:

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

4. Click **Next**
5. Configurar:
   - **Policy name:** `GitHubActionsECRPush`
   - **Description:** `Permite a GitHub Actions subir imágenes Docker a ECR`
6. Click **Create policy**

### Paso 2: Crear el Usuario IAM

1. AWS Console → **IAM** → **Users** → **Create user**
2. Configurar:
   - **User name:** `github-actions-ecr`
3. Click **Next**
4. En **Set permissions**:
   - Selecciona **Attach policies directly**
   - Busca y selecciona: `GitHubActionsECRPush`
5. Click **Next** → **Create user**

### Paso 3: Crear Access Keys

1. Click en el usuario recién creado: `github-actions-ecr`
2. Pestaña **Security credentials**
3. En **Access keys** → **Create access key**
4. Selecciona: **Application running outside AWS**
5. Click **Next** → **Create access key**
6. **⚠️ IMPORTANTE:** Copia inmediatamente:
   - `Access key ID` → Usar como `DEV_AWS_ACCESS_KEY_ID` o `PROD_AWS_ACCESS_KEY_ID`
   - `Secret access key` → Usar como `DEV_AWS_SECRET_ACCESS_KEY` o `PROD_AWS_SECRET_ACCESS_KEY`

---

## ✅ Checklist Final

Después de configurar todo, verifica que tienes estos 8 secrets en GitHub:

```
Repository secrets:
├── DEV_AWS_ACCOUNT_ID ............ 775681068353
├── DEV_AWS_ACCESS_KEY_ID ......... AKIA...
├── DEV_AWS_SECRET_ACCESS_KEY ..... (oculto)
├── DEV_ECR_REPOSITORY ............ landa-beauty-api-dev-api
├── PROD_AWS_ACCOUNT_ID ........... 553938786984
├── PROD_AWS_ACCESS_KEY_ID ........ AKIA...
├── PROD_AWS_SECRET_ACCESS_KEY .... (oculto)
└── PROD_ECR_REPOSITORY ........... landa-beauty-api-api
```

---

## 🧪 Probar el Workflow

1. Haz un cambio pequeño en el código
2. Push a la rama `dev`
3. Ve a GitHub → **Actions** → Verás el workflow ejecutándose
4. En ~3-5 minutos la imagen se sube a ECR
5. App Runner detecta la nueva imagen y hace auto-deploy (~3 min más)

---

## 🔒 Seguridad

- ❌ **Nunca** compartas las Access Keys
- ❌ **Nunca** las subas al repositorio
- ✅ Usa usuarios IAM con **permisos mínimos**
- ✅ Rota las keys periódicamente
- ✅ Elimina keys que no uses

