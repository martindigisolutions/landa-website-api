#!/usr/bin/env python3
"""
Script para verificar qué cuenta de Stripe está asociada con cada key
y detectar inconsistencias
"""
import os
import sys
from dotenv import load_dotenv

# Cargar .env.dev
load_dotenv('.env.dev')

print("="*60)
print("VERIFICACION DE CUENTAS DE STRIPE")
print("="*60)

secret_key = os.getenv('STRIPE_SECRET_KEY', '')

if not secret_key:
    print("[ERROR] STRIPE_SECRET_KEY no configurada")
    sys.exit(1)

print(f"\n[BACKEND - Secret Key]")
print("-" * 60)
print(f"Key: {secret_key[:30]}...")

try:
    import stripe
    stripe.api_key = secret_key
    
    # Obtener información de la cuenta asociada con la secret key
    account = stripe.Account.retrieve()
    
    print(f"\n[INFO] Cuenta asociada con STRIPE_SECRET_KEY:")
    print(f"  Account ID: {account.id}")
    print(f"  Email: {getattr(account, 'email', 'N/A')}")
    print(f"  Display Name: {getattr(account, 'display_name', 'N/A')}")
    print(f"  Business Profile Name: {getattr(account.business_profile, 'name', 'N/A') if hasattr(account, 'business_profile') else 'N/A'}")
    
    backend_account_id = account.id
    
    print(f"\n[STRIPE CLI]")
    print("-" * 60)
    print("Ejecuta este comando para ver la cuenta del CLI:")
    print("  stripe config --list")
    print("\nO verifica en la salida de 'stripe login'")
    print("  La cuenta del CLI debe ser: " + backend_account_id)
    
    print(f"\n[VERIFICACION]")
    print("-" * 60)
    print("Si el Account ID del CLI es diferente a:")
    print(f"  {backend_account_id}")
    print("\nEntonces hay un problema:")
    print("  - Los webhooks del CLI seran de una cuenta diferente")
    print("  - Los PaymentIntents creados con la secret key seran de otra cuenta")
    print("  - Los eventos no coincidiran")
    
    print(f"\n[SOLUCION]")
    print("-" * 60)
    print("1. Verifica que el CLI este conectado a la cuenta correcta:")
    print(f"   stripe login --account {backend_account_id}")
    print("\n2. O reconecta el CLI a la cuenta correcta:")
    print("   stripe login")
    print("   (Asegurate de iniciar sesion con la cuenta correcta)")
    
    print(f"\n[VERIFICAR EN DASHBOARD]")
    print("-" * 60)
    print("1. Ve a: https://dashboard.stripe.com/account")
    print(f"2. Verifica que el Account ID sea: {backend_account_id}")
    print("3. Si es diferente, necesitas usar las keys de esa cuenta")
    
except ImportError:
    print("[ERROR] Stripe no esta instalado. Instala con: pip install stripe")
    sys.exit(1)
except stripe.error.AuthenticationError as e:
    print(f"[ERROR] Secret key invalida: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)

