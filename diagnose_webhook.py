#!/usr/bin/env python3
"""
Script para diagnosticar por qué no llegan webhooks de Stripe
"""
import requests
import os
import sys
from config import STRIPE_WEBHOOK_SECRET, STRIPE_SECRET_KEY

def diagnose_webhook():
    """Diagnose webhook issues"""
    print("="*60)
    print("DIAGNOSTIC: Stripe Webhook Configuration")
    print("="*60)
    
    issues = []
    
    # 1. Check if server is running
    print("\n[1] Checking if FastAPI server is running...")
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=2)
        if response.status_code == 200:
            print("[OK] FastAPI server is running on http://localhost:8000")
        else:
            print(f"[WARNING] Server responded with status {response.status_code}")
            issues.append("Server returned non-200 status")
    except requests.exceptions.ConnectionError:
        print("[ERROR] FastAPI server is NOT running!")
        print("        Please start it with: python -m uvicorn main:app --reload")
        issues.append("Server not running")
    except Exception as e:
        print(f"[ERROR] Could not connect to server: {e}")
        issues.append(f"Connection error: {e}")
    
    # 2. Check webhook endpoint
    print("\n[2] Checking webhook endpoint accessibility...")
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
            print(f"     Response body: {response.text[:200]}")
            issues.append(f"Unexpected endpoint response: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to webhook endpoint")
        issues.append("Webhook endpoint not accessible")
    except Exception as e:
        print(f"[ERROR] Error testing endpoint: {e}")
        issues.append(f"Endpoint test error: {e}")
    
    # 3. Check webhook secret
    print("\n[3] Checking STRIPE_WEBHOOK_SECRET configuration...")
    if STRIPE_WEBHOOK_SECRET:
        print(f"[OK] STRIPE_WEBHOOK_SECRET is configured")
        print(f"     Secret: {STRIPE_WEBHOOK_SECRET[:20]}...")
        if not STRIPE_WEBHOOK_SECRET.startswith("whsec_"):
            print("[WARNING] Webhook secret should start with 'whsec_'")
            issues.append("Invalid webhook secret format")
    else:
        print("[ERROR] STRIPE_WEBHOOK_SECRET is NOT configured!")
        print("         You need to set it in your .env.dev file")
        print("         Get it from: stripe listen --forward-to localhost:8000/stripe/webhook")
        issues.append("Webhook secret not configured")
    
    # 4. Check Stripe secret key
    print("\n[4] Checking STRIPE_SECRET_KEY configuration...")
    if STRIPE_SECRET_KEY:
        print(f"[OK] STRIPE_SECRET_KEY is configured")
        print(f"     Key: {STRIPE_SECRET_KEY[:20]}...")
        if not (STRIPE_SECRET_KEY.startswith("sk_test_") or STRIPE_SECRET_KEY.startswith("sk_live_")):
            print("[WARNING] Stripe secret key format looks incorrect")
            issues.append("Invalid Stripe secret key format")
    else:
        print("[WARNING] STRIPE_SECRET_KEY is NOT configured!")
        issues.append("Stripe secret key not configured")
    
    # 5. Check if Stripe CLI is needed
    print("\n[5] Checking Stripe CLI setup...")
    print("[INFO] For local development, you need Stripe CLI running:")
    print("       1. Open a terminal")
    print("       2. Run: stripe listen --forward-to localhost:8000/stripe/webhook")
    print("       3. Copy the webhook secret (whsec_...) to your .env.dev file")
    print("       4. Restart your FastAPI server")
    
    # 6. Instructions
    print("\n" + "="*60)
    print("TROUBLESHOOTING STEPS")
    print("="*60)
    
    if issues:
        print("\n[ISSUES FOUND]")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n[FIXES]")
        
        if "Server not running" in str(issues):
            print("   1. Start FastAPI server:")
            print("      python -m uvicorn main:app --reload")
        
        if "Webhook secret not configured" in str(issues):
            print("   2. Get webhook secret from Stripe CLI:")
            print("      stripe listen --forward-to localhost:8000/stripe/webhook")
            print("      Copy the 'whsec_...' value to .env.dev as STRIPE_WEBHOOK_SECRET")
        
        if "Webhook endpoint not accessible" in str(issues):
            print("   3. Make sure the server is running and accessible")
    else:
        print("\n[OK] All basic checks passed!")
        print("\n[TO TEST WEBHOOKS]")
        print("   1. Make sure Stripe CLI is running:")
        print("      stripe listen --forward-to localhost:8000/stripe/webhook")
        print("   2. In another terminal, trigger a test event:")
        print("      stripe trigger payment_intent.succeeded")
        print("   3. You should see in Stripe CLI:")
        print("      --> payment_intent.succeeded [evt_...]")
        print("      <-- [200] POST http://localhost:8000/stripe/webhook [XXms]")
        print("   4. Check your FastAPI server logs for webhook processing")
    
    print("\n" + "="*60)
    
    return len(issues) == 0

if __name__ == "__main__":
    success = diagnose_webhook()
    sys.exit(0 if success else 1)

