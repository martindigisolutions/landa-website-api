# Landa Beauty Supply - Backend API (FastAPI)

Este proyecto expone una API REST con autenticación basada en tokens JWT para autenticación de usuarios y gestión de productos.

## 🔧 Requisitos

- Python 3.10 o superior
- `pip` o `conda`
- Entorno virtual (recomendado)
- Frontend corriendo en: `http://localhost:3000` (por defecto para Next.js)

## 📦 Instalación

1. Clona este repositorio o navega a tu carpeta de backend.
2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate   # En Windows
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Verifica que el archivo de base de datos SQLite (`products.db`) existe, o que se crea con `Base.metadata.create_all()`.

## 🚀 Ejecutar el servidor local

Ejecuta el servidor de desarrollo con recarga automática:

```bash
python -m uvicorn main:app --reload
```

Por defecto, la API estará disponible en:

```
http://127.0.0.1:8000
```

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

- `POST /register`: Registrar nuevo usuario
- `POST /login`: Iniciar sesión y obtener token
- `GET /products`: Obtener productos (requiere token)

## 📁 Estructura relevante

```
main.py              # API principal
products.db          # Base de datos SQLite
requirements.txt     # Paquetes necesarios
```

## ✅ Notas

- La imagen del producto se almacena como nombre `.webp` en `image_url`.
- Los tokens expiran en 1 año.
- `has_variants` indica si el producto tiene variantes activas en la DB de Django.