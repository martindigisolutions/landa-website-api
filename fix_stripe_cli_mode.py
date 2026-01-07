#!/usr/bin/env python3
"""
Script para verificar y ayudar a configurar el modo correcto de Stripe CLI
"""
import os
from dotenv import load_dotenv

load_dotenv('.env.dev')

print("="*60)
print("VERIFICACION DE MODO STRIPE")
print("="*60)

secret_key = os.getenv('STRIPE_SECRET_KEY', '')

if secret_key:
    if 'test' in secret_key.lower():
        print(f"\n[BACKEND]")
        print("-" * 60)
        print("[OK] Backend esta en modo TEST (sandbox)")
        print(f"     Key: {secret_key[:30]}...")
        print("\n[STRIPE CLI]")
        print("-" * 60)
        print("El CLI debe estar en modo TEST tambien")
        print("\n[VERIFICAR]")
        print("-" * 60)
        print("Ejecuta: stripe config --list")
        print("Busca la seccion [default] y verifica:")
        print("  - Debe usar test_mode_api_key (no live_mode_api_key)")
        print("  - account_id debe ser acct_1SbST7R7tmWYSwkU")
        print("\n[SI EL CLI ESTA EN MODO LIVE]")
        print("-" * 60)
        print("1. Cierra el listener actual (Ctrl+C)")
        print("2. Ejecuta: stripe logout")
        print("3. Ejecuta: stripe login")
        print("4. Asegurate de estar en modo TEST en el navegador")
        print("5. Verifica: stripe config --list")
        print("6. Reinicia: stripe listen --forward-to localhost:8000/stripe/webhook")
    else:
        print("[WARNING] Backend parece estar en modo LIVE")
        print("          Key: " + secret_key[:30] + "...")
else:
    print("[ERROR] STRIPE_SECRET_KEY no configurada")

print("\n" + "="*60)

