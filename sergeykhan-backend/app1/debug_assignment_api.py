#!/usr/bin/env python3
"""
Debug script to check what the assignment API actually returns
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

def debug_assignment_api():
    # Create test data
    print("Creating test data...")
    
    # Create curator
    curator = CustomUser.objects.create_user(
        email='debug_curator@test.com',
        password='testpass123',
        role='curator'
    )
    
    # Create master
    master = CustomUser.objects.create_user(
        email='debug_master@test.com',
        password='testpass123',
        role='master'
    )
    
    # Create order
    order = Order.objects.create(
        client_name="Debug Test Client",
        client_phone="+7 999 123 45 67",
        description="Debug test order",
        address="Debug Address",
        estimated_cost=500.00,
        status="новый"  # Russian for "new"
    )
    
    print(f"Created order {order.id}, master {master.id}, curator {curator.email}")
    
    # Get token
    from rest_framework.authtoken.models import Token
    token, created = Token.objects.get_or_create(user=curator)
    print(f"Token: {token.key}")
    
    # Test assignment
    base_url = "http://localhost:8000"
    headers = {
        'Authorization': f'Token {token.key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'assigned_master': master.id
    }
    
    print(f"\nAssigning order {order.id} to master {master.id}...")
    print(f"Request data: {data}")
    
    try:
        response = requests.patch(f"{base_url}/assign/{order.id}/", headers=headers, json=data)
        print(f"Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"Parsed JSON: {json.dumps(response_data, indent=2, default=str)}")
            except:
                print("Response is not JSON")
        
    except Exception as e:
        print(f"Request failed: {e}")
        
    # Clean up
    print("\nCleaning up...")
    order.delete()
    master.delete()
    curator.delete()

if __name__ == "__main__":
    debug_assignment_api()
