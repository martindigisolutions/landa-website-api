#!/usr/bin/env python3
"""
Script para verificar qué variables de entorno están configuradas
"""
import os
from dotenv import load_dotenv

# Cargar .env.dev
env_file = os.getenv("ENV_FILE", ".env.dev")
load_dotenv(env_file)

print("="*60)
print("VERIFICACIÓN DE VARIABLES DE ENTORNO")
print("="*60)
print(f"\nArchivo cargado: {env_file}")
print(f"¿Existe el archivo? {os.path.exists(env_file)}")
print("\n" + "="*60)

# Variables requeridas para Stripe
stripe_vars = {
    "STRIPE_SECRET_KEY": {
        "required": True,
        "description": "Clave secreta de Stripe (sk_test_... para desarrollo)",
        "where": "Stripe Dashboard → API Keys → Secret key"
    },
    "STRIPE_WEBHOOK_SECRET": {
        "required": True,
        "description": "Secret del webhook (whsec_...)",
        "where": "Stripe CLI: stripe listen --forward-to localhost:8000/stripe/webhook"
    }
}

# Otras variables importantes
other_vars = {
    "SECRET_KEY": {
        "required": True,
        "description": "Clave secreta para JWT (mínimo 32 caracteres)",
        "where": "Genera una clave segura"
    },
    "DATABASE_URL": {
        "required": False,
        "description": "URL de conexión a la base de datos",
        "where": "Auto-configurado si usas Secrets Manager"
    }
}

print("\n[STRIPE CONFIGURATION]")
print("-" * 60)
all_ok = True

for var_name, info in stripe_vars.items():
    value = os.getenv(var_name, "")
    is_set = bool(value)
    
    if is_set:
        # Mostrar solo los primeros caracteres por seguridad
        if "SECRET" in var_name or "KEY" in var_name:
            display_value = f"{value[:20]}..." if len(value) > 20 else "***"
        else:
            display_value = value
        
        print(f"[OK] {var_name}: SET")
        print(f"   Valor: {display_value}")
    else:
        print(f"[MISSING] {var_name}: NOT SET")
        print(f"   Descripción: {info['description']}")
        print(f"   Dónde obtener: {info['where']}")
        if info['required']:
            all_ok = False
    
    print()

print("\n[OTRAS VARIABLES IMPORTANTES]")
print("-" * 60)

for var_name, info in other_vars.items():
    value = os.getenv(var_name, "")
    is_set = bool(value)
    
    if is_set:
        if "SECRET" in var_name or "KEY" in var_name or "PASSWORD" in var_name:
            display_value = f"{value[:20]}..." if len(value) > 20 else "***"
        else:
            display_value = value
        
        print(f"[OK] {var_name}: SET")
        print(f"   Valor: {display_value}")
    else:
        status = "[WARNING]" if info['required'] else "[INFO]"
        print(f"{status} {var_name}: NOT SET")
        if info['required']:
            print(f"   Descripción: {info['description']}")
            print(f"   Dónde obtener: {info['where']}")
            all_ok = False
    
    print()

print("="*60)
print("INSTRUCCIONES")
print("="*60)

if not all_ok:
    print("\n[PASOS PARA CONFIGURAR]")
    print("\n1. Crea o edita el archivo .env.dev en la raíz del proyecto")
    print("\n2. Para STRIPE_SECRET_KEY:")
    print("   - Ve a: https://dashboard.stripe.com/apikeys")
    print("   - Asegúrate de estar en modo TEST")
    print("   - Copia la 'Secret key' (empieza con sk_test_)")
    print("   - Agrega a .env.dev: STRIPE_SECRET_KEY=sk_test_...")
    
    print("\n3. Para STRIPE_WEBHOOK_SECRET:")
    print("   - Abre una terminal")
    print("   - Ejecuta: stripe listen --forward-to localhost:8000/stripe/webhook")
    print("   - Copia el 'webhook signing secret' (empieza con whsec_)")
    print("   - Agrega a .env.dev: STRIPE_WEBHOOK_SECRET=whsec_...")
    
    print("\n4. Ejemplo de .env.dev:")
    print("   STRIPE_SECRET_KEY=sk_test_51SbST7R7tmWYSwkU...")
    print("   STRIPE_WEBHOOK_SECRET=whsec_da66f9e00362d772e902f11e59e7220a51384bdeff071af91cb2d62ba83144b2")
    
    print("\n5. Reinicia el servidor FastAPI después de cambiar .env.dev")
else:
    print("\n[OK] Todas las variables requeridas estan configuradas!")
    print("\n[PRÓXIMOS PASOS]")
    print("1. Asegúrate de que el Stripe CLI esté corriendo:")
    print("   stripe listen --forward-to localhost:8000/stripe/webhook")
    print("2. Verifica que el STRIPE_WEBHOOK_SECRET coincida con el del CLI")
    print("3. Si cambias el CLI, actualiza el secret en .env.dev")

print("\n" + "="*60)

