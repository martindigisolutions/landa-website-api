# 🚀 Deployment Guide - AWS App Runner

Esta guía explica cómo desplegar la API de Landa Beauty Supply en AWS App Runner.

## 📋 Prerequisitos

- Cuenta de AWS
- AWS CLI configurado (opcional, para despliegue via CLI)
- Docker instalado (para pruebas locales)
- Base de datos PostgreSQL (AWS RDS recomendado para producción)

## 🐳 Probar Localmente con Docker

### 1. Construir la imagen

```bash
docker build -t landa-api .
```

### 2. Ejecutar el contenedor

```bash
docker run -p 8080:8080 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=sqlite:///./api_db.sqlite3 \
  -e ALLOWED_ORIGINS=http://localhost:3000 \
  landa-api
```

### 3. Usar Docker Compose (recomendado)

```bash
docker-compose up --build
```

### 4. Verificar que funciona

```bash
curl http://localhost:8080/api/health
```

Respuesta esperada:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "Landa Beauty Supply API",
    "version": "1.0.0"
  }
}
```

---

## ☁️ Despliegue en AWS App Runner

### Opción A: Desde GitHub con Runtime Python (RECOMENDADA) ⭐

La forma más simple. App Runner lee el `apprunner.yaml` y despliega automáticamente.

1. **Ir a AWS App Runner Console**
   - https://console.aws.amazon.com/apprunner

2. **Crear servicio**
   - Source: **"Source code repository"**
   - Conectar tu repositorio de GitHub
   - Branch: `main` (o tu branch de producción)

3. **Configuración de Build**
   - Configuration source: **"Use a configuration file"** ← App Runner lee `apprunner.yaml`
   - (Alternativamente: "Configure all settings here" → Python 3.11 → `pip install -r requirements.txt` → `python main.py` → Port 8080)

4. **Configurar variables de entorno** (ver sección abajo)

5. **Crear servicio**

App Runner desplegará automáticamente en cada push a tu rama.

### Opción B: Imagen Docker desde ECR

Para tener control total sobre la imagen que se despliega:

1. **Crear repositorio en ECR**

```bash
aws ecr create-repository --repository-name landa-api
```

2. **Autenticarse en ECR**

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

3. **Construir y subir la imagen**

```bash
# Construir
docker build -t landa-api .

# Taggear
docker tag landa-api:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/landa-api:latest

# Subir
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/landa-api:latest
```

4. **Crear servicio en App Runner**
   - Source: "Container registry"
   - Provider: "Amazon ECR"
   - Seleccionar la imagen

5. **Configurar variables de entorno** (ver sección abajo)

---

## 🔐 Variables de Entorno Requeridas

Configura estas variables en App Runner Console → Service Settings → Configure service → Environment variables:

### Obligatorias

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Clave secreta para JWT (32+ caracteres) | `your-super-secret-key-here-min-32-chars` |
| `ALLOWED_ORIGINS` | URLs del frontend (separadas por coma) | `https://landabeautysupply.com,https://www.landabeautysupply.com` |

### Stripe (para pagos)

| Variable | Descripción |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Clave secreta de Stripe (`sk_live_xxx`) |
| `STRIPE_WEBHOOK_SECRET` | Secret del webhook (`whsec_xxx`) |

### Email (para recuperación de contraseña)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `EMAIL_HOST` | Servidor SMTP | `smtp.gmail.com` |
| `EMAIL_PORT` | Puerto SMTP | `587` |
| `EMAIL_USERNAME` | Usuario SMTP | `noreply@example.com` |
| `EMAIL_PASSWORD` | Contraseña SMTP | `app-password` |
| `EMAIL_FROM` | Email remitente | `Landa Beauty <noreply@landabeauty.com>` |
| `FRONTEND_RESET_URL` | URL de reset password | `https://landabeautysupply.com/reset-password` |

### Admin OAuth2 (opcional)

| Variable | Descripción |
|----------|-------------|
| `ADMIN_CLIENT_ID` | ID del cliente admin |
| `ADMIN_CLIENT_SECRET` | Secret del cliente admin |

### Otras

| Variable | Descripción | Default |
|----------|-------------|---------|
| `PORT` | Puerto del servidor | `8080` |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `LOG_LEVEL` | Nivel de logs | `info` |
| `WHOLESALE_FRONTEND_URL` | URL frontend wholesale | - |

---

## 🔧 Configuración de App Runner Recomendada

### Instancia

- **CPU**: 1 vCPU (escalar según tráfico)
- **Memory**: 2 GB (mínimo recomendado)
- **Auto scaling**: 
  - Min: 1 instancia
  - Max: 10 instancias
  - Concurrencia: 100 requests

### Health Check

- **Protocol**: HTTP
- **Path**: `/api/health`
- **Interval**: 10 segundos
- **Timeout**: 5 segundos
- **Healthy threshold**: 1
- **Unhealthy threshold**: 5

### Networking

- **Public access**: Enabled (para API pública)
- Para conectar con RDS en VPC privada, configurar VPC Connector

---

## 🗄️ Base de Datos PostgreSQL (RDS)

### Crear instancia RDS

1. Ir a AWS RDS Console
2. Crear base de datos:
   - Engine: PostgreSQL 15
   - Template: Free tier (dev) o Production
   - Instance: db.t3.micro (dev) o db.t3.small+ (prod)
   - Storage: 20 GB gp3

3. Configurar conectividad:
   - VPC: Default o tu VPC
   - Public access: No (usar VPC Connector en App Runner)
   - Security group: Permitir puerto 5432 desde App Runner

### Connection string

```
postgresql://username:password@endpoint:5432/database_name
```

---

## 🔄 CI/CD Automático

App Runner puede configurarse para desplegar automáticamente cuando:

1. **Desde GitHub**: Push a la rama configurada
2. **Desde ECR**: Nueva imagen publicada

### GitHub Actions (ejemplo)

```yaml
name: Deploy to App Runner

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push
        run: |
          docker build -t ${{ secrets.ECR_REGISTRY }}/landa-api:${{ github.sha }} .
          docker push ${{ secrets.ECR_REGISTRY }}/landa-api:${{ github.sha }}
          docker tag ${{ secrets.ECR_REGISTRY }}/landa-api:${{ github.sha }} ${{ secrets.ECR_REGISTRY }}/landa-api:latest
          docker push ${{ secrets.ECR_REGISTRY }}/landa-api:latest
```

---

## 🔍 Troubleshooting

### La aplicación no inicia

1. Verificar logs en App Runner Console
2. Revisar que todas las variables de entorno estén configuradas
3. Verificar conexión a la base de datos

### Error de conexión a base de datos

1. Verificar que el Security Group permita conexiones desde App Runner
2. Si usas VPC Connector, verificar la configuración de subnets
3. Probar la connection string localmente

### Health check falla

1. Verificar que el endpoint `/api/health` responda
2. Revisar logs para errores de inicio
3. Aumentar el timeout del health check

---

## 📊 Monitoreo

- **CloudWatch Logs**: Logs automáticos de App Runner
- **CloudWatch Metrics**: CPU, memoria, requests
- **X-Ray**: Tracing distribuido (opcional)

---

## 💰 Costos Estimados

- **App Runner**: ~$0.064/vCPU-hora + $0.007/GB-hora
- **RDS PostgreSQL**: Desde $12/mes (db.t3.micro)
- **ECR**: $0.10/GB-mes de almacenamiento

Para un API con tráfico bajo-medio: **~$25-50/mes**
