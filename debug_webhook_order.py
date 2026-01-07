#!/usr/bin/env python3
"""
Debug script to check why order wasn't updated by webhook
"""
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Order
import stripe
from dotenv import load_dotenv
import os

load_dotenv('.env.dev')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def check_order(order_id: int):
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            print(f"Order {order_id} not found")
            return
        
        print(f"="*60)
        print(f"ORDER #{order.id}")
        print(f"="*60)
        print(f"Status: {order.status}")
        print(f"Payment Status: {order.payment_status}")
        print(f"Stripe PaymentIntent ID: {order.stripe_payment_intent_id}")
        
        if order.stripe_payment_intent_id:
            try:
                pi = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
                print(f"\n[STRIPE PAYMENTINTENT]")
                print(f"  ID: {pi.id}")
                print(f"  Status: {pi.status}")
                print(f"  Amount: ${pi.amount / 100:.2f}")
                print(f"  Metadata: {pi.metadata}")
                
                if pi.status == "succeeded":
                    print(f"\n[PROBLEMA]")
                    print(f"  PaymentIntent en Stripe: succeeded")
                    print(f"  Orden en DB: {order.status}")
                    print(f"  [ACCION] El webhook deberia haber actualizado la orden")
                    print(f"  [VERIFICAR] Logs del servidor para ver si el webhook encontro la orden")
                else:
                    print(f"\n[INFO] PaymentIntent status: {pi.status}")
                    
            except Exception as e:
                print(f"\n[ERROR] No se pudo recuperar PaymentIntent: {e}")
        
        print(f"\n[VERIFICACION]")
        print(f"  Buscar en logs del servidor:")
        print(f"    - 'Processing payment_intent.succeeded event'")
        print(f"    - 'Order not found for PaymentIntent {order.stripe_payment_intent_id}'")
        print(f"    - 'Updating order #{order.id}'")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_webhook_order.py <order_id>")
        sys.exit(1)
    
    try:
        order_id = int(sys.argv[1])
        check_order(order_id)
    except ValueError:
        print(f"Invalid order ID: {sys.argv[1]}")

