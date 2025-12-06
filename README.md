# Landa Beauty Supply - Backend API (FastAPI)

Este proyecto expone una API REST con autenticación basada en tokens JWT para autenticación de usuarios, gestión de productos y procesamiento de pagos con Stripe.

## 🔧 Requisitos

- Python 3.10 o superior
- `pip` o `conda`
- Entorno virtual (recomendado)
- Frontend corriendo en: `http://localhost:3000` (por defecto para Next.js)
- Stripe CLI (para desarrollo local con webhooks)

## 📦 Instalación

1. Clona este repositorio o navega a tu carpeta de backend.
2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate   # En Windows
   source .venv/bin/activate  # En Linux/Mac
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Configura las variables de entorno (ver sección de configuración).

5. Ejecuta las migraciones:

   ```bash
   alembic upgrade head
   ```

## ⚙️ Configuración

Crea un archivo `.env.dev` en la raíz del proyecto con las siguientes variables:

```env
# Email Configuration
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@example.com
EMAIL_PASSWORD=your-email-password
EMAIL_FROM=noreply@example.com

# Frontend URLs
FRONTEND_RESET_URL=http://localhost:3000/reset-password

# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# Password Reset
PASSWORD_RESET_MAX_REQUESTS_PER_HOUR=3

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
```

## 🚀 Ejecutar el servidor local

Ejecuta el servidor de desarrollo con recarga automática:

```bash
python -m uvicorn main:app --reload
```

Por defecto, la API estará disponible en:

```
http://127.0.0.1:8000
```

---

## 💳 Integración con Stripe

### Configuración Inicial

1. **Crear cuenta en Stripe**: [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)

2. **Obtener claves API**:
   - Ve a [Stripe Dashboard → API Keys](https://dashboard.stripe.com/apikeys)
   - Copia la **Secret key** → `STRIPE_SECRET_KEY`
   - Asegúrate de estar en modo **Test** para desarrollo

### Stripe CLI para Desarrollo Local

Los webhooks de Stripe no pueden llegar directamente a `localhost`. Usamos Stripe CLI para reenviar eventos localmente.

#### 1. Instalar Stripe CLI

**Windows (con Scoop):**
```powershell
scoop install stripe
```

**Windows (descarga directa):**
- Descarga desde: [https://github.com/stripe/stripe-cli/releases](https://github.com/stripe/stripe-cli/releases)
- Extrae y agrega al PATH

**Mac:**
```bash
brew install stripe/stripe-cli/stripe
```

**Linux:**
```bash
# Debian/Ubuntu
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee -a /etc/apt/sources.list.d/stripe.list
sudo apt update
sudo apt install stripe
```

#### 2. Autenticarse con Stripe

```bash
stripe login
```

Se abrirá el navegador para autorizar. Una vez autorizado, verás:

```
Your pairing code is: xxxx-xxxx-xxxx-xxxx
Press Enter to open the browser...
Done! The Stripe CLI is configured.
```

#### 3. Iniciar el Listener de Webhooks

En una terminal separada, ejecuta:

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

Verás algo como:

```
Ready! Your webhook signing secret is whsec_xxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ Importante**: Copia el `whsec_xxx` y actualiza tu `.env.dev`:

```env
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxx
```

#### 4. Flujo de Desarrollo Completo

Abre 2 terminales:

**Terminal 1 - Servidor FastAPI:**
```bash
.\.venv\Scripts\activate
python -m uvicorn main:app --reload
```

**Terminal 2 - Stripe CLI:**
```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

### Endpoints de Stripe

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/stripe/create-payment-intent` | Crear Payment Intent para una orden |
| POST | `/stripe/confirm-payment` | Confirmar estado del pago |
| POST | `/stripe/webhook` | Recibir eventos de Stripe |

#### POST /stripe/create-payment-intent

Crea un Payment Intent para procesar el pago.

**Request:**
```json
{
    "order_id": "20",
    "session_id": "abc123"
}
```

**Response:**
```json
{
    "client_secret": "pi_xxx_secret_xxx",
    "payment_intent_id": "pi_xxx"
}
```

#### POST /stripe/confirm-payment

Confirma el estado del pago después de que el usuario completa el formulario.

**Request:**
```json
{
    "order_id": "20",
    "payment_intent_id": "pi_xxx",
    "session_id": "abc123"
}
```

**Response:**
```json
{
    "status": "paid",
    "order_id": "20"
}
```

### Probar Pagos

Usa estas tarjetas de prueba en modo Test:

| Número | Resultado |
|--------|-----------|
| `4242 4242 4242 4242` | ✅ Pago exitoso |
| `4000 0000 0000 0002` | ❌ Tarjeta rechazada |
| `4000 0000 0000 3220` | 🔐 Requiere 3D Secure |
| `4000 0000 0000 9995` | ❌ Fondos insuficientes |

- **Fecha de expiración**: Cualquier fecha futura (ej: 12/34)
- **CVC**: Cualquier 3 dígitos (ej: 123)
- **ZIP**: Cualquier código postal (ej: 12345)

### Probar Webhooks Manualmente

Con Stripe CLI puedes disparar eventos de prueba:

```bash
# Simular pago exitoso
stripe trigger payment_intent.succeeded

# Simular pago fallido
stripe trigger payment_intent.payment_failed

# Simular reembolso
stripe trigger charge.refunded
```

---

## 🔐 Autenticación

1. Primero regístrate con el endpoint:

   ```
   POST /register
   Content-Type: application/json
   Body:
   {
     "username": "your_user",
     "password": "your_pass"
   }
   ```

2. Luego inicia sesión en:

   ```
   POST /login
   Content-Type: application/x-www-form-urlencoded
   Body:
   username=your_user&password=your_pass
   ```

   ✅ Respuesta:

   ```json
   {
     "access_token": "your.jwt.token",
     "token_type": "bearer"
   }
   ```

3. Usa el token en llamadas autenticadas (por ejemplo `/products`):

   ```
   Authorization: Bearer your.jwt.token
   ```

## 🌐 CORS para desarrollo

Se ha habilitado CORS para permitir llamadas desde:

```
http://localhost:3000
```

Esto permite integrar fácilmente el frontend en Next.js durante desarrollo local.

## 🧪 Endpoints disponibles

### Autenticación
- `POST /register`: Registrar nuevo usuario
- `POST /login`: Iniciar sesión y obtener token

### Productos
- `GET /products`: Obtener productos
- `GET /brands`: Obtener marcas

### Checkout
- `POST /checkout/`: Iniciar sesión de checkout
- `POST /checkout/options`: Obtener métodos de pago y envío
- `POST /checkout/order`: Crear orden
- `POST /checkout/order/confirm-manual-payment`: Confirmar pago manual
- `GET /checkout/order/{order_id}/payment-details`: Detalles de pago
- `GET /checkout/orders`: Listar órdenes

### Stripe
- `POST /stripe/create-payment-intent`: Crear Payment Intent
- `POST /stripe/confirm-payment`: Confirmar pago
- `POST /stripe/webhook`: Webhook de Stripe

## 📁 Estructura del proyecto

```
├── main.py                 # API principal
├── config.py               # Configuración y variables de entorno
├── database.py             # Conexión a base de datos
├── models.py               # Modelos SQLAlchemy
├── security.py             # Utilidades de seguridad
├── requirements.txt        # Dependencias
├── alembic/                # Migraciones de base de datos
│   └── versions/           # Scripts de migración
├── routers/                # Endpoints de la API
│   ├── auth.py             # Autenticación
│   ├── products.py         # Productos
│   ├── checkout_router.py  # Checkout
│   └── stripe_router.py    # Stripe
├── services/               # Lógica de negocio
│   ├── auth_service.py
│   ├── product_service.py
│   ├── checkout_service.py
│   └── stripe_service.py
├── schemas/                # Schemas Pydantic
│   ├── auth.py
│   ├── product.py
│   ├── checkout.py
│   └── stripe.py
└── api_db.sqlite3          # Base de datos SQLite
```

## 📖 Documentación Interactiva

Con el servidor corriendo, accede a:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## ✅ Notas

- La imagen del producto se almacena como nombre `.webp` en `image_url`.
- Los tokens JWT expiran en 1 año.
- `has_variants` indica si el producto tiene variantes activas.
- Los pagos con Stripe requieren el webhook secret para funcionar correctamente.
- En producción, configura el webhook en el Dashboard de Stripe apuntando a tu dominio.
