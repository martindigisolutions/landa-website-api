#!/usr/bin/env python3
"""
Script to check order status and payment details
"""
import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order

def check_order(order_id: int):
    """Check order status and payment details"""
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            print(f"[ERROR] Order {order_id} not found")
            return
        
        print(f"\n{'='*60}")
        print(f"ORDER #{order.id} - Status Check")
        print(f"{'='*60}\n")
        
        # Basic order info
        print(f"Order Details:")
        print(f"   Status: {order.status}")
        print(f"   Payment Method: {order.payment_method or 'Not set'}")
        print(f"   Payment Status: {order.payment_status or 'Not set'}")
        print(f"   Shipping Method: {order.shipping_method or 'Not set'}")
        print(f"   Total: ${order.total:.2f}")
        print(f"   Created At: {order.created_at}")
        print(f"   Paid At: {order.paid_at or 'Not paid yet'}")
        
        # Stripe-specific info
        print(f"\nStripe Payment Info:")
        if order.stripe_payment_intent_id:
            print(f"   [OK] Stripe PaymentIntent ID: {order.stripe_payment_intent_id}")
        else:
            print(f"   [MISSING] No Stripe PaymentIntent ID found")
        
        # Analysis
        print(f"\nAnalysis:")
        
        if order.payment_method == "stripe":
            if order.stripe_payment_intent_id:
                if order.payment_status == "completed":
                    print(f"   [SUCCESS] Stripe payment completed successfully")
                    print(f"   [OK] PaymentIntent was created and confirmed")
                elif order.payment_status == "pending":
                    print(f"   [WARNING] Stripe payment is pending")
                    print(f"   [WARNING] PaymentIntent was created but not yet confirmed")
                    print(f"   This could mean:")
                    print(f"      - Payment is still being processed")
                    print(f"      - Webhook hasn't been received yet")
                    print(f"      - Payment failed but wasn't updated")
                elif order.payment_status == "failed":
                    print(f"   [FAILED] Stripe payment failed")
                else:
                    print(f"   [WARNING] Unknown payment status: {order.payment_status}")
            else:
                print(f"   [PROBLEM] Stripe payment method selected but no PaymentIntent ID")
                print(f"   This means:")
                print(f"      - STRIPE_SECRET_KEY was not configured when lock was created")
                print(f"      - PaymentIntent creation failed")
                print(f"      - Order was created before PaymentIntent was set up")
        elif order.payment_method in ["zelle", "cashapp", "venmo"]:
            print(f"   [INFO] Manual payment method: {order.payment_method}")
            print(f"   [INFO] Requires manual verification")
            if order.status == "pending_verification":
                print(f"   [OK] Status correctly set to 'pending_verification'")
            else:
                print(f"   [WARNING] Status is '{order.status}' (expected 'pending_verification')")
        else:
            print(f"   [WARNING] Unknown or missing payment method: {order.payment_method}")
        
        # Status check
        print(f"\nStatus Summary:")
        if order.status == "paid" and order.payment_status == "completed":
            print(f"   [SUCCESS] Order is fully paid and completed")
        elif order.status == "paid" and order.payment_status != "completed":
            print(f"   [WARNING] Order marked as 'paid' but payment_status is '{order.payment_status}'")
            print(f"   This might indicate a sync issue")
        elif order.status == "pending_payment":
            print(f"   [PENDING] Order is waiting for payment")
        elif order.status == "pending_verification":
            print(f"   [PENDING] Order is waiting for manual payment verification")
        else:
            print(f"   [INFO] Order status: {order.status}")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        print(f"[ERROR] Error checking order: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_order_status.py <order_id>")
        sys.exit(1)
    
    try:
        order_id = int(sys.argv[1])
        check_order(order_id)
    except ValueError:
        print(f"[ERROR] Invalid order ID: {sys.argv[1]}")
        sys.exit(1)

