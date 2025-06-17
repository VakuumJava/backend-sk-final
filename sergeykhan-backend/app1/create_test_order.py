#!/usr/bin/env python3
"""
Create a new test order for assignment testing
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import Order

def create_test_order():
    print("🔧 Creating new test order...")
    
    order = Order.objects.create(
        client_name="Test Assignment Client",
        client_phone="+7 999 888 77 66",
        description="Test order for assignment debugging",
        address="Test Address, 123",
        estimated_cost=1000.00,
        status="новый"
    )
    
    print(f"✅ Created test order: ID = {order.id}")
    print(f"   Status: {order.status}")
    print(f"   Client: {order.client_name}")
    
    return order.id

if __name__ == "__main__":
    order_id = create_test_order()
