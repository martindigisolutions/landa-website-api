#!/usr/bin/env python3
"""
Script para probar que el webhook local está funcionando correctamente.
Este script verifica:
1. Que el servidor FastAPI esté corriendo
2. Que el endpoint /stripe/webhook esté accesible
3. Que el STRIPE_WEBHOOK_SECRET esté configurado
"""
import requests
import os
from config import STRIPE_WEBHOOK_SECRET

def test_webhook_endpoint():
    """Test if webhook endpoint is accessible"""
    print("="*60)
    print("TEST: Webhook Endpoint Local")
    print("="*60)
    
    # Check if server is running
    print("\n[STEP 1] Checking if FastAPI server is running...")
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=2)
        if response.status_code == 200:
            print("[OK] FastAPI server is running")
        else:
            print(f"[WARNING] Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] FastAPI server is NOT running!")
        print("        Please start it with: python -m uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        return False
    
    # Check webhook endpoint
    print("\n[STEP 2] Checking webhook endpoint...")
    try:
        # Try to access the endpoint (will fail without proper signature, but we can check if it exists)
        response = requests.post(
            "http://localhost:8000/stripe/webhook",
            json={"test": "data"},
            headers={"stripe-signature": "test"},
            timeout=2
        )
        # We expect 400 (bad signature) but that means the endpoint exists
        if response.status_code in [400, 401, 403]:
            print("[OK] Webhook endpoint exists and is responding")
            print(f"     Response: {response.status_code} (expected - signature validation)")
        else:
            print(f"[WARNING] Unexpected response: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to webhook endpoint")
        return False
    except Exception as e:
        print(f"[ERROR] Error testing endpoint: {e}")
        return False
    
    # Check webhook secret
    print("\n[STEP 3] Checking STRIPE_WEBHOOK_SECRET...")
    if STRIPE_WEBHOOK_SECRET:
        print(f"[OK] STRIPE_WEBHOOK_SECRET is configured")
        print(f"     Secret: {STRIPE_WEBHOOK_SECRET[:20]}...")
    else:
        print("[WARNING] STRIPE_WEBHOOK_SECRET is NOT configured!")
        print("         You need to set it in your .env.dev file")
        print("         Get it from: stripe listen --forward-to localhost:8000/stripe/webhook")
        return False
    
    # Instructions
    print("\n" + "="*60)
    print("SETUP INSTRUCTIONS")
    print("="*60)
    print("\nTo see webhook events in Stripe CLI, you need:")
    print("\n1. FastAPI server running:")
    print("   python -m uvicorn main:app --reload")
    print("\n2. Stripe CLI listening (in another terminal):")
    print("   stripe listen --forward-to localhost:8000/stripe/webhook")
    print("\n3. Trigger a test event:")
    print("   stripe trigger payment_intent.succeeded")
    print("\n4. You should see in the CLI:")
    print("   --> payment_intent.succeeded [evt_...]")
    print("   <-- [200] POST http://localhost:8000/stripe/webhook [XXms]")
    print("\n" + "="*60)
    
    return True

if __name__ == "__main__":
    test_webhook_endpoint()

