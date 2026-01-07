#!/usr/bin/env python3
"""
Verificación detallada de la orden 74
"""
import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order
from dotenv import load_dotenv

load_dotenv('.env.dev')

def check_order_74():
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == 74).first()
        
        if not order:
            print("[ERROR] Order 74 not found")
            return
        
        print("="*60)
        print("ORDER #74 - Detailed Check")
        print("="*60)
        
        print(f"\n[ORDER INFO]")
        print(f"  Status: {order.status}")
        print(f"  Payment Status: {order.payment_status}")
        print(f"  Payment Method: {order.payment_method}")
        print(f"  Total: ${order.total:.2f}")
        print(f"  Created At: {order.created_at}")
        print(f"  Paid At: {order.paid_at}")
        print(f"  Stripe PaymentIntent ID: {order.stripe_payment_intent_id}")
        
        if order.stripe_payment_intent_id:
            print(f"\n[STRIPE API CHECK]")
            print("-" * 60)
            
            try:
                import stripe
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                
                pi = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
                
                print(f"  PaymentIntent Status: {pi.status}")
                print(f"  Amount: ${pi.amount / 100:.2f}")
                print(f"  Currency: {pi.currency}")
                print(f"  Created: {pi.created}")
                
                if pi.status == "succeeded":
                    print(f"\n  [OK] PaymentIntent succeeded in Stripe!")
                    print(f"  [WARNING] But order payment_status is still '{order.payment_status}'")
                    print(f"  [ACTION] The webhook 'payment_intent.succeeded' should update this")
                    print(f"  [INFO] Last webhook received was 'charge.updated' (not the right one)")
                elif pi.status == "requires_payment_method":
                    print(f"\n  [INFO] PaymentIntent requires payment method")
                    print(f"  [INFO] Customer needs to complete payment")
                elif pi.status == "requires_confirmation":
                    print(f"\n  [INFO] PaymentIntent requires confirmation")
                elif pi.status == "processing":
                    print(f"\n  [INFO] PaymentIntent is processing")
                elif pi.status == "requires_action":
                    print(f"\n  [INFO] PaymentIntent requires action (3D Secure, etc.)")
                else:
                    print(f"\n  [INFO] PaymentIntent status: {pi.status}")
                
                # Check latest charge
                if hasattr(pi, 'latest_charge') and pi.latest_charge:
                    try:
                        charge = stripe.Charge.retrieve(pi.latest_charge)
                        print(f"\n  [CHARGE INFO]")
                        print(f"    Charge ID: {charge.id}")
                        print(f"    Charge Status: {charge.status}")
                        print(f"    Paid: {charge.paid}")
                        print(f"    Captured: {charge.captured}")
                    except:
                        pass
                
            except Exception as e:
                print(f"  [ERROR] Could not retrieve PaymentIntent: {e}")
        
        print(f"\n[WEBHOOK STATUS]")
        print("-" * 60)
        print("  The webhook 'charge.updated' was received (200 OK)")
        print("  But the code only processes:")
        print("    - payment_intent.succeeded")
        print("    - payment_intent.payment_failed")
        print("    - charge.refunded")
        print("\n  [ACTION] Need to trigger 'payment_intent.succeeded' webhook")
        print("  Or wait for Stripe to send it automatically")
        
        print(f"\n[RECOMMENDATION]")
        print("-" * 60)
        if order.stripe_payment_intent_id:
            print("  1. Check if payment was completed in Stripe Dashboard")
            print("  2. If payment succeeded, trigger webhook manually:")
            print(f"     stripe trigger payment_intent.succeeded --override payment_intent:id={order.stripe_payment_intent_id}")
            print("  3. Or wait for Stripe to send the webhook automatically")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_order_74()

