#!/usr/bin/env python3
"""
Debug script to check what fields the workload API actually returns
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
from api1.models import CustomUser

User = get_user_model()

def debug_workload_api():
    # Try to get a token for a curator
    print("Checking for existing curators...")
    curators = CustomUser.objects.filter(role='curator')
    if curators.exists():
        curator = curators.first()
        print(f"Found curator: {curator.email}")
        
        # Create a token for this curator
        from django.contrib.auth import authenticate
        from rest_framework.authtoken.models import Token
        
        # Try to create/get token
        token, created = Token.objects.get_or_create(user=curator)
        print(f"Token {'created' if created else 'retrieved'}: {token.key}")
        
        # Make API request
        base_url = "http://localhost:8000"
        headers = {'Authorization': f'Token {token.key}'}
        
        print("\nTesting /api/workload/masters/ endpoint...")
        try:
            response = requests.get(f"{base_url}/api/workload/masters/", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Number of masters: {len(data)}")
                if data:
                    print("First master data structure:")
                    print(json.dumps(data[0], indent=2, default=str))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")
            
        print("\nTesting /api/masters/workload/all/ endpoint...")
        try:
            response = requests.get(f"{base_url}/api/masters/workload/all/", headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Number of masters: {len(data)}")
                if data:
                    print("First master data structure:")
                    print(json.dumps(data[0], indent=2, default=str))
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")
    else:
        print("No curators found. Creating one...")
        curator = CustomUser.objects.create_user(
            email='debug@test.com',
            password='testpass123',
            role='curator'
        )
        print(f"Created curator: {curator.email}")
        debug_workload_api()

if __name__ == "__main__":
    debug_workload_api()
