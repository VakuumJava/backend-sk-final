#!/usr/bin/env python3
"""
Test assignment API directly with HTTP requests
"""

import requests
import json

def test_assignment_api():
    base_url = "http://127.0.0.1:8000"
    order_id = 484362
    master_id = 2  # Based on previous debug output
    
    # Get token first (you'll need to replace with actual credentials)
    print("🔐 Getting authentication token...")
    
    # Try to login as super admin or curator
    login_data = {
        "email": "admin@test.com",  # Replace with actual admin email
        "password": "admin123"      # Replace with actual password
    }
    
    try:
        login_response = requests.post(f"{base_url}/login/", json=login_data)
        print(f"Login response status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get('token')
            print(f"✅ Got token: {token[:20]}...")
            
            # Now test assignment
            print(f"\n🔧 Testing assignment of order {order_id} to master {master_id}")
            
            assignment_data = {
                "assigned_master": master_id
            }
            
            headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
            }
            
            assign_response = requests.patch(
                f"{base_url}/assign/{order_id}/", 
                json=assignment_data, 
                headers=headers
            )
            
            print(f"Assignment response status: {assign_response.status_code}")
            print(f"Assignment response: {assign_response.text}")
            
            if assign_response.status_code == 400:
                print("❌ Bad Request - checking error details...")
                try:
                    error_data = assign_response.json()
                    print(f"Error details: {error_data}")
                except:
                    print("Could not parse error JSON")
            
        else:
            print(f"❌ Login failed: {login_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the Django server running?")
        print("   Try: cd /path/to/backend && python manage.py runserver")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_assignment_api()
