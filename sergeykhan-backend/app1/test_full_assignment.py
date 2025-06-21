#!/usr/bin/env python3
"""
Test full assignment flow
"""

import requests
import json

def test_full_assignment_flow():
    base_url = "http://127.0.0.1:8000"
    
    # Test login
    print("🔐 Testing login...")
    login_data = {"email": "admin@test.com", "password": "admin123"}
    
    login_response = requests.post(f"{base_url}/login/", json=login_data)
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json().get('token')
    print(f"✅ Login successful, token: {token[:20]}...")
    
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    # Test various assignment scenarios
    test_cases = [
        {
            "name": "Basic assignment (no slot)",
            "order_id": 484364,  # Updated to new test order
            "data": {"assigned_master": 2}
        },
        {
            "name": "Assignment with invalid master",
            "order_id": 484364,
            "data": {"assigned_master": 999}
        },
        {
            "name": "Assignment with slot data",
            "order_id": 484364,
            "data": {
                "assigned_master": 2,
                "scheduled_date": "2025-06-20",
                "scheduled_time": "10:00:00"
            }
        },
        {
            "name": "Assignment with malformed data",
            "order_id": 484364,
            "data": {
                "assigned_master": 2,
                "masterId": 3,  # This extra field might cause issues
                "scheduled_date": "2025-06-20",
                "scheduled_time": "10:00:00"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Data: {test_case['data']}")
        
        response = requests.patch(
            f"{base_url}/assign/{test_case['order_id']}/",
            json=test_case['data'],
            headers=headers
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")
        else:
            print(f"   ✅ Success")

if __name__ == "__main__":
    test_full_assignment_flow()
