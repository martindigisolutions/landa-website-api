#!/usr/bin/env python3
"""
Script para verificar el STRIPE_WEBHOOK_SECRET y compararlo con el CLI
"""
import os
from dotenv import load_dotenv

load_dotenv('.env.dev')

print("="*60)
print("VERIFICACION DE WEBHOOK SECRET")
print("="*60)

webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')

if webhook_secret:
    print(f"\n[OK] STRIPE_WEBHOOK_SECRET configurado en .env.dev")
    print(f"     Valor: {webhook_secret[:30]}...")
    print(f"     Longitud: {len(webhook_secret)} caracteres")
    print(f"     Formato: {'whsec_' if webhook_secret.startswith('whsec_') else 'NO EMPIEZA CON whsec_ (PROBLEMA!)'}")
else:
    print("\n[ERROR] STRIPE_WEBHOOK_SECRET NO CONFIGURADO en .env.dev")
    print("        Necesitas agregarlo al archivo .env.dev")

print("\n[STRIPE CLI]")
print("-" * 60)
print("Para obtener el secret actual del CLI:")
print("1. Asegurate de que el listener este corriendo:")
print("   stripe listen --forward-to localhost:8000/stripe/webhook")
print("\n2. El CLI mostrara algo como:")
print("   > Ready! Your webhook signing secret is whsec_...")
print("\n3. Copia ese whsec_... y actualiza .env.dev:")
print("   STRIPE_WEBHOOK_SECRET=whsec_...")
print("\n4. REINICIA el servidor FastAPI despues de actualizar")

print("\n[VERIFICACION]")
print("-" * 60)
print("El secret en .env.dev DEBE coincidir EXACTAMENTE con el del CLI")
print("Si no coinciden, veras el error:")
print("  'Invalid webhook signature: No signatures found matching...'")

print("\n[SOLUCION RAPIDA]")
print("-" * 60)
print("1. Ve a la terminal donde corre 'stripe listen'")
print("2. Busca la linea que dice 'Your webhook signing secret is whsec_...'")
print("3. Copia el whsec_... completo")
print("4. Actualiza .env.dev con ese valor")
print("5. REINICIA el servidor FastAPI (Ctrl+C y vuelve a iniciarlo)")

print("\n" + "="*60)

