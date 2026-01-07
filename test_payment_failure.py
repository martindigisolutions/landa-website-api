#!/usr/bin/env python3
"""
Script para probar el flujo de pago fallido
Simula una orden que falla después de 10 segundos
"""
import time
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order
import stripe
from dotenv import load_dotenv
import os

load_dotenv('.env.dev')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def test_payment_failure(order_id: int, wait_seconds: int = 10):
    """
    Simula un pago fallido para una orden existente
    
    Args:
        order_id: ID de la orden a probar
        wait_seconds: Segundos a esperar antes de disparar el fallo
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            print(f"[ERROR] Order {order_id} not found")
            return
        
        print("="*60)
        print(f"TEST: Payment Failure for Order #{order.id}")
        print("="*60)
        
        print(f"\n[INITIAL STATE]")
        print(f"  Status: {order.status}")
        print(f"  Payment Status: {order.payment_status}")
        print(f"  PaymentIntent ID: {order.stripe_payment_intent_id}")
        
        if not order.stripe_payment_intent_id:
            print(f"\n[ERROR] Order {order_id} doesn't have a Stripe PaymentIntent ID")
            print(f"        This order was not created with Stripe payment method")
            return
        
        if order.status == "paid":
            print(f"\n[WARNING] Order is already paid. Cannot simulate failure.")
            print(f"          Use an order with status 'processing_payment'")
            return
        
        print(f"\n[WAITING {wait_seconds} seconds before simulating failure...]")
        for i in range(wait_seconds, 0, -1):
            print(f"  {i}...", end="", flush=True)
            time.sleep(1)
        print(" 0!")
        
        print(f"\n[SIMULATING PAYMENT FAILURE]")
        print(f"  PaymentIntent ID: {order.stripe_payment_intent_id}")
        
        # Option 1: Cancel PaymentIntent via API (this will trigger webhook)
        print(f"\n[OPTION 1: Cancel PaymentIntent via Stripe API]")
        print(f"  This will cancel the PaymentIntent, which should trigger a webhook")
        response = input("  Cancel PaymentIntent via Stripe API? (y/n): ")
        if response.lower() == 'y':
            try:
                pi = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
                if pi.status == "succeeded":
                    print(f"  [WARNING] PaymentIntent is already succeeded, cannot cancel")
                    print(f"  [INFO] Updating order directly to payment_failed instead...")
                    order.status = "payment_failed"
                    order.payment_status = "failed"
                    db.commit()
                    print(f"  [OK] Order #{order.id} updated to payment_failed")
                elif pi.status in ["requires_payment_method", "requires_confirmation", "requires_action"]:
                    # Cancel the PaymentIntent
                    canceled_pi = stripe.PaymentIntent.cancel(order.stripe_payment_intent_id)
                    print(f"  [OK] PaymentIntent canceled: {canceled_pi.status}")
                    print(f"  [INFO] Webhook should arrive shortly to update order status")
                    print(f"  [INFO] If webhook doesn't arrive, order will be updated directly...")
                    time.sleep(2)  # Wait a bit for webhook
                    db.refresh(order)
                    if order.status != "payment_failed":
                        print(f"  [INFO] Webhook didn't update order, updating directly...")
                        order.status = "payment_failed"
                        order.payment_status = "failed"
                        db.commit()
                        print(f"  [OK] Order #{order.id} updated to payment_failed")
                else:
                    print(f"  [INFO] PaymentIntent status: {pi.status}")
                    print(f"  [INFO] Updating order directly to payment_failed...")
                    order.status = "payment_failed"
                    order.payment_status = "failed"
                    db.commit()
                    print(f"  [OK] Order #{order.id} updated to payment_failed")
            except Exception as e:
                print(f"  [ERROR] Failed to cancel PaymentIntent: {e}")
                print(f"  [INFO] Updating order directly instead...")
                order.status = "payment_failed"
                order.payment_status = "failed"
                db.commit()
                print(f"  [OK] Order #{order.id} updated to payment_failed")
        else:
            # Option 2: Direct update (simpler for testing)
            print(f"\n[OPTION 2: Direct Update (Testing Only)]")
            response2 = input("  Update order directly to 'payment_failed'? (y/n): ")
            if response2.lower() == 'y':
                order.status = "payment_failed"
                order.payment_status = "failed"
                db.commit()
                print(f"  [OK] Order #{order.id} updated to payment_failed")
            else:
                print(f"\n[OPTION 3: Manual Stripe CLI]")
                print(f"  The Stripe CLI override syntax doesn't work reliably.")
                print(f"  Instead, you can:")
                print(f"  1. Go to Stripe Dashboard → PaymentIntents")
                print(f"  2. Find PaymentIntent: {order.stripe_payment_intent_id}")
                print(f"  3. Cancel it manually (if not already succeeded)")
                print(f"  4. Or use: stripe payment_intents cancel {order.stripe_payment_intent_id}")
        
        print(f"\n[FINAL STATE]")
        db.refresh(order)
        print(f"  Status: {order.status}")
        print(f"  Payment Status: {order.payment_status}")
        
        print(f"\n[VERIFICATION]")
        if order.status == "payment_failed":
            print(f"  [SUCCESS] Order correctly marked as payment_failed")
        else:
            print(f"  [PENDING] Order status: {order.status}")
            print(f"           Waiting for webhook to update it...")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def create_test_order_with_stripe():
    """
    Crea una orden de prueba con Stripe para luego probar el fallo
    """
    print("="*60)
    print("CREATE TEST ORDER WITH STRIPE")
    print("="*60)
    print("\n[INFO] This will create a test order that you can then test failure with")
    print("       Use the test_stripe_payment_flow.py script instead for full flow")
    print("\n[RECOMMENDATION]")
    print("  1. Create an order normally through the frontend")
    print("  2. Note the order ID")
    print("  3. Run this script with that order ID to test failure")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_payment_failure.py <order_id> [wait_seconds]")
        print("\nExample:")
        print("  python test_payment_failure.py 80 10")
        print("  (Tests order 80, waits 10 seconds before simulating failure)")
        sys.exit(1)
    
    try:
        order_id = int(sys.argv[1])
        wait_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        test_payment_failure(order_id, wait_seconds)
    except ValueError:
        print(f"[ERROR] Invalid order ID: {sys.argv[1]}")
        sys.exit(1)

