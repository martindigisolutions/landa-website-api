#!/usr/bin/env python3
"""
Script para verificar que las keys de Stripe están correctamente configuradas
y que coinciden entre backend y frontend
"""
import os
import sys
from dotenv import load_dotenv

# Cargar .env.dev
load_dotenv('.env.dev')

print("="*60)
print("VERIFICACION DE KEYS DE STRIPE")
print("="*60)

# Obtener keys del backend
secret_key = os.getenv('STRIPE_SECRET_KEY', '')
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

print("\n[BACKEND - .env.dev]")
print("-" * 60)

if secret_key:
    print(f"[OK] STRIPE_SECRET_KEY: {secret_key[:20]}...")
    print(f"     Tipo: {'TEST' if 'test' in secret_key else 'LIVE' if 'live' in secret_key else 'DESCONOCIDO'}")
else:
    print("[ERROR] STRIPE_SECRET_KEY: NO CONFIGURADA")
    sys.exit(1)

if webhook_secret:
    print(f"[OK] STRIPE_WEBHOOK_SECRET: {webhook_secret[:20]}...")
else:
    print("[WARNING] STRIPE_WEBHOOK_SECRET: NO CONFIGURADA")

# Intentar verificar la secret key con Stripe API
print("\n[VERIFICACION CON STRIPE API]")
print("-" * 60)

try:
    import stripe
    stripe.api_key = secret_key
    
    # Intentar crear un PaymentIntent de prueba
    intent = stripe.PaymentIntent.create(
        amount=100,  # $1.00
        currency='usd',
    )
    print(f"[OK] Secret key es valida")
    print(f"     PaymentIntent de prueba creado: {intent.id}")
    print(f"     Client Secret: {intent.client_secret[:30]}...")
    
    # Obtener información de la cuenta
    try:
        account = stripe.Account.retrieve()
        print(f"\n[INFO] Cuenta de Stripe:")
        print(f"     ID: {account.id}")
        print(f"     Email: {getattr(account, 'email', 'N/A')}")
    except:
        pass
    
    # Obtener la publishable key asociada
    print(f"\n[PUBLISHABLE KEY ASOCIADA]")
    print("-" * 60)
    print("Para obtener la Publishable Key:")
    print("1. Ve a: https://dashboard.stripe.com/apikeys")
    print("2. Asegurate de estar en modo TEST (si usas sk_test_)")
    print("3. Copia la 'Publishable key' (empieza con pk_test_)")
    print("4. Usala en el frontend como: NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY")
    
    # Verificar si hay una variable de publishable key en el backend (opcional)
    publishable_key = os.getenv('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY', '')
    if publishable_key:
        print(f"\n[FRONTEND KEY EN BACKEND]")
        print("-" * 60)
        print(f"[OK] NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY encontrada: {publishable_key[:20]}...")
        
        # Verificar que las keys coinciden (mismo proyecto)
        try:
            secret_prefix = secret_key.split('_')[2] if len(secret_key.split('_')) > 2 else None
            publishable_prefix = publishable_key.split('_')[2] if len(publishable_key.split('_')) > 2 else None
            
            if secret_prefix and publishable_prefix:
                if secret_prefix == publishable_prefix:
                    print(f"[OK] Las keys coinciden (mismo proyecto Stripe)")
                    print(f"     Prefijo comun: {secret_prefix}")
                else:
                    print(f"[WARNING] Las keys pueden ser de diferentes proyectos")
                    print(f"     Secret prefix: {secret_prefix}")
                    print(f"     Publishable prefix: {publishable_prefix}")
                    print(f"     [ACCION] Verifica que ambas keys son del mismo proyecto en Stripe Dashboard")
        except Exception as e:
            print(f"[INFO] No se pudo verificar coincidencia: {e}")
    else:
        print(f"\n[INFO] NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY no encontrada en .env.dev")
        print("       Esto es normal - la publishable key va en el frontend (.env.local)")
    
except ImportError:
    print("[ERROR] Stripe no esta instalado. Instala con: pip install stripe")
    sys.exit(1)
except stripe.error.AuthenticationError as e:
    print(f"[ERROR] Secret key invalida o no autorizada: {e}")
    sys.exit(1)
except stripe.error.StripeError as e:
    print(f"[ERROR] Error de Stripe: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("RESUMEN")
print("="*60)
print("\n[BACKEND (.env.dev)]")
print("  STRIPE_SECRET_KEY: [OK]" if secret_key else "  STRIPE_SECRET_KEY: [FALTA]")
print("  STRIPE_WEBHOOK_SECRET: [OK]" if webhook_secret else "  STRIPE_WEBHOOK_SECRET: [FALTA]")

print("\n[FRONTEND (.env.local)]")
print("  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: [VERIFICAR MANUALMENTE]")
print("  - Debe empezar con pk_test_ (desarrollo) o pk_live_ (produccion)")
print("  - Debe ser del mismo proyecto que la sk_test_ del backend")
print("  - Obtenerla de: https://dashboard.stripe.com/apikeys")

print("\n[PASOS SIGUIENTES]")
print("1. Ve a Stripe Dashboard -> API Keys")
print("2. Copia la Publishable key (pk_test_...)")
print("3. Agregala al frontend en .env.local:")
print("   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...")
print("4. Reinicia el servidor del frontend")
print("5. Verifica que Stripe.js se carga correctamente en el navegador")

print("\n" + "="*60)

