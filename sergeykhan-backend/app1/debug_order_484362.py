#!/usr/bin/env python3
"""
Debug script to test assignment API with order 484362
"""

import os
import sys
import django
import requests
import json

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from django.contrib.auth import get_user_model
from api1.models import CustomUser, Order

User = get_user_model()

def debug_order_484362():
    print("Debugging order 484362 assignment...")
    
    try:
        # Check if order exists
        order = Order.objects.get(id=484362)
        print(f"✅ Order {order.id} found:")
        print(f"   Status: {order.status}")
        print(f"   Current master: {order.assigned_master}")
        print(f"   Client: {order.client_name}")
        
        # Get available masters
        masters = CustomUser.objects.filter(role='master')
        print(f"\n📋 Available masters ({masters.count()}):")
        for master in masters[:5]:  # Show first 5
            print(f"   ID: {master.id}, Email: {master.email}")
        
        if masters.exists():
            # Try to simulate assignment
            test_master = masters.first()
            print(f"\n🔧 Testing assignment to master {test_master.id} ({test_master.email})")
            
            # Check what data would be sent
            assignment_data = {
                'assigned_master': test_master.id
            }
            print(f"   Assignment data: {assignment_data}")
            
            # Check if order status allows assignment
            allowed_statuses = ['новый', 'в обработке']
            if order.status in allowed_statuses:
                print(f"   ✅ Order status '{order.status}' allows assignment")
            else:
                print(f"   ❌ Order status '{order.status}' does not allow assignment")
                print(f"   Allowed statuses: {allowed_statuses}")
        
    except Order.DoesNotExist:
        print(f"❌ Order 484362 not found")
        
        # Show some existing orders
        orders = Order.objects.all().order_by('-id')[:10]
        print(f"\n📋 Recent orders:")
        for order in orders:
            print(f"   ID: {order.id}, Status: {order.status}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_order_484362()
