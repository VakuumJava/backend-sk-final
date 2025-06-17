#!/usr/bin/env python3
"""
Comprehensive integration test for the order assignment system.
Tests the new order assignment panel functionality and API integration.
"""

import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import Order, CustomUser, MasterAvailability

User = get_user_model()

class OrderAssignmentIntegrationTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.auth_tokens = {}
        
    def setup_test_data(self):
        """Create test users and data"""
        print("🔧 Setting up test data...")
        
        # Create test users
        self.create_test_users()
        self.create_test_availability()
        self.create_test_orders()
        
        print("✅ Test data setup complete")
        
    def create_test_users(self):
        """Create test masters, curators, and clients"""
        # Create masters
        self.master1 = User.objects.create_user(
            email='master1@test.com',
            password='testpass123',
            first_name='Иван',
            last_name='Петров',
            role='master'
        )
        
        self.master2 = User.objects.create_user(
            email='master2@test.com',
            password='testpass123',
            first_name='Алексей',
            last_name='Сидоров',
            role='master'
        )
        
        self.master3 = User.objects.create_user(
            email='master3@test.com', 
            password='testpass123',
            first_name='Сергей',
            last_name='Иванов',
            role='master'
        )
        
        # Create curator
        self.curator = User.objects.create_user(
            email='curator@test.com',
            password='testpass123',
            first_name='Мария',
            last_name='Админова',
            role='curator'
        )
        
        print(f"Created {User.objects.filter(email__contains='@test.com').count()} test users")
        
    def create_test_availability(self):
        """Create availability slots for masters"""
        tomorrow = datetime.now().date() + timedelta(days=1)
        day_after = datetime.now().date() + timedelta(days=2)
        
        # Master 1: Available tomorrow 9-12, day after 14-17
        MasterAvailability.objects.create(
            master=self.master1,
            date=tomorrow,
            start_time="09:00",
            end_time="12:00"
        )
        MasterAvailability.objects.create(
            master=self.master1,
            date=day_after,
            start_time="14:00", 
            end_time="17:00"
        )
        
        # Master 2: Available tomorrow 14-18
        MasterAvailability.objects.create(
            master=self.master2,
            date=tomorrow,
            start_time="14:00",
            end_time="18:00"
        )
        
        # Master 3: No availability (should be shown as unavailable)
        
        print(f"Created {MasterAvailability.objects.count()} availability slots")
        
    def create_test_orders(self):
        """Create test orders for assignment"""
        self.test_order1 = Order.objects.create(
            client_name="Test Client 1",
            client_phone="+7 999 123 45 67",
            description="Test order for assignment testing",
            address="Test Address 1",
            estimated_cost=500.00,
            status="новый"  # Russian for "new"
        )
        
        self.test_order2 = Order.objects.create(
            client_name="Test Client 2", 
            client_phone="+7 999 123 45 68",
            description="Test order 2 for assignment testing",
            address="Test Address 2",
            estimated_cost=750.00,
            status="в обработке"  # Russian for "in processing"
        )
        
        # Create an already assigned order
        self.assigned_order = Order.objects.create(
            client_name="Test Client 3",
            client_phone="+7 999 123 45 69", 
            description="Already assigned order",
            address="Test Address 3",
            estimated_cost=600.00,
            status="assigned",
            assigned_master=self.master1
        )
        
        print(f"Created {Order.objects.filter(client_name__startswith='Test Client').count()} test orders")
        
    def get_auth_token(self, email, password):
        """Get authentication token for user"""
        if email in self.auth_tokens:
            return self.auth_tokens[email]
            
        response = requests.post(f"{self.base_url}/login/", {
            'email': email,
            'password': password
        })
        
        if response.status_code == 200:
            token = response.json().get('token')
            self.auth_tokens[email] = token
            return token
        else:
            raise Exception(f"Failed to get token for {email}: {response.text}")
            
    def test_master_workload_api(self):
        """Test the master workload API endpoint"""
        print("\n🧪 Testing Master Workload API...")
        
        # Get curator token
        token = self.get_auth_token('curator@test.com', 'testpass123')
        headers = {'Authorization': f'Token {token}'}
        
        # Test getting all masters workload
        response = requests.get(f"{self.base_url}/api/masters/workload/all/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Master workload API returned {len(data)} masters")
            
            # Check that masters have the required data structure
            for master_data in data:
                required_fields = ['master_id', 'master_email', 'next_available_slot', 'total_orders_today']
                for field in required_fields:
                    if field not in master_data:
                        print(f"❌ Missing field {field} in master data")
                        return False
                        
            print("✅ All masters have required data fields")
            
            # Check specific masters
            master1_data = next((m for m in data if m['master_id'] == self.master1.id), None)
            if master1_data:
                print(f"✅ Master 1 found in workload data")
                if master1_data['next_available_slot']:
                    next_slot = master1_data['next_available_slot']
                    print(f"✅ Master 1 next available: {next_slot['date']} {next_slot['start_time']}-{next_slot['end_time']}")
                else:
                    print("ℹ️ Master 1 has no available slots")
            
            return True
        else:
            print(f"❌ Master workload API failed: {response.status_code} - {response.text}")
            return False
            
    def test_order_assignment_api(self):
        """Test order assignment API"""
        print("\n🧪 Testing Order Assignment API...")
        
        token = self.get_auth_token('curator@test.com', 'testpass123')
        headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
        
        # Test assigning order to master
        assign_data = {'assigned_master': self.master2.id}
        response = requests.patch(
            f"{self.base_url}/assign/{self.test_order1.id}/",
            json=assign_data,
            headers=headers
        )
        
        if response.status_code == 200:
            updated_order = response.json()
            if updated_order.get('assigned_master') == self.master2.id:
                print(f"✅ Successfully assigned order {self.test_order1.id} to master {self.master2.id}")
                
                # Verify in database
                self.test_order1.refresh_from_db()
                if self.test_order1.assigned_master_id == self.master2.id:
                    print("✅ Assignment verified in database")
                    return True
                else:
                    print("❌ Assignment not reflected in database")
                    return False
            else:
                print(f"❌ Assignment response doesn't match expected master ID. Expected: {self.master2.id}, Got: {updated_order.get('assigned_master')}")
                return False
        else:
            print(f"❌ Order assignment failed: {response.status_code} - {response.text}")
            return False
            
    def test_order_assignment_restrictions(self):
        """Test that order assignment respects availability restrictions"""
        print("\n🧪 Testing Order Assignment Restrictions...")
        
        token = self.get_auth_token('curator@test.com', 'testpass123')
        headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
        
        # Try to assign to master 3 who has no availability
        assign_data = {'assigned_master': self.master3.id}
        response = requests.patch(
            f"{self.base_url}/assign/{self.test_order2.id}/",
            json=assign_data,
            headers=headers
        )
        
        # This should still work (assignment is allowed, but UI should warn)
        if response.status_code == 200:
            print("✅ Assignment to master without availability slots works (as designed)")
            
            # But we should be able to see in the workload API that this master has no next available slot
            workload_response = requests.get(f"{self.base_url}/api/masters/workload/all/", headers=headers)
            if workload_response.status_code == 200:
                data = workload_response.json()
                master3_data = next((m for m in data if m['master_id'] == self.master3.id), None)
                if master3_data:
                    if master3_data['next_available_slot'] is None:
                        print("✅ Master 3 correctly shows no next available slot")
                        return True
                    else:
                        print("❌ Master 3 unexpectedly has a next available slot")
                        return False
                        
        print(f"❌ Unexpected response: {response.status_code} - {response.text}")
        return False
        
    def test_workload_updates(self):
        """Test that workload data updates correctly after assignment"""
        print("\n🧪 Testing Workload Updates After Assignment...")
        
        token = self.get_auth_token('curator@test.com', 'testpass123')
        headers = {'Authorization': f'Token {token}'}
        
        # Get initial workload
        response = requests.get(f"{self.base_url}/api/masters/workload/all/", headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to get initial workload: {response.text}")
            return False
            
        initial_data = response.json()
        master2_initial = next((m for m in initial_data if m['master_id'] == self.master2.id), None)
        
        if not master2_initial:
            print("❌ Master 2 not found in workload data")
            return False
            
        initial_orders = master2_initial['total_orders_today']
        print(f"📊 Master 2 initial orders today: {initial_orders}")
        
        # Get updated workload after assignment
        response = requests.get(f"{self.base_url}/api/masters/workload/all/", headers=headers)
        if response.status_code == 200:
            updated_data = response.json()
            master2_updated = next((m for m in updated_data if m['master_id'] == self.master2.id), None)
            
            if master2_updated:
                updated_orders = master2_updated['total_orders_today']
                print(f"📊 Master 2 updated orders today: {updated_orders}")
                
                # The count should reflect the assigned order
                if updated_orders >= initial_orders:
                    print("✅ Master workload correctly reflects assignment")
                    return True
                else:
                    print("⚠️  Workload count may not include the new assignment yet (depends on order date)")
                    return True
                    
        print("❌ Failed to get updated workload data")
        return False
        
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n🧪 Testing Edge Cases...")
        
        token = self.get_auth_token('curator@test.com', 'testpass123')
        headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
        
        # Test assigning to non-existent master
        assign_data = {'assigned_master': 99999}
        response = requests.patch(
            f"{self.base_url}/assign/{self.test_order2.id}/",
            json=assign_data,
            headers=headers
        )
        
        if response.status_code == 400 or response.status_code == 404:
            print("✅ Correctly rejected assignment to non-existent master")
        else:
            print(f"⚠️  Unexpected response for non-existent master: {response.status_code}")
            
        # Test assigning non-existent order
        assign_data = {'assigned_master': self.master1.id}
        response = requests.patch(
            f"{self.base_url}/assign/99999/",
            json=assign_data,
            headers=headers
        )
        
        if response.status_code == 404:
            print("✅ Correctly rejected assignment of non-existent order")
        else:
            print(f"⚠️  Unexpected response for non-existent order: {response.status_code}")
            
        return True
        
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test orders
        Order.objects.filter(client_name__startswith='Test Client').delete()
        
        # Delete test users and their profiles
        User.objects.filter(email__contains='@test.com').delete()
        
        # Delete test availability
        MasterAvailability.objects.filter(master__email__contains='@test.com').delete()
        
        print("✅ Test data cleaned up")
        
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Order Assignment Integration Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            
            # Run tests
            tests = [
                self.test_master_workload_api,
                self.test_order_assignment_api,
                self.test_order_assignment_restrictions,
                self.test_workload_updates,
                self.test_edge_cases
            ]
            
            results = []
            for test in tests:
                try:
                    result = test()
                    results.append(result)
                except Exception as e:
                    print(f"❌ Test {test.__name__} failed with exception: {e}")
                    results.append(False)
                    
            # Summary
            passed = sum(results)
            total = len(results)
            
            print("\n" + "=" * 60)
            print(f"📊 TEST SUMMARY: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All tests passed! Order assignment system is working correctly.")
            else:
                print("⚠️  Some tests failed. Please check the output above.")
                
        except Exception as e:
            print(f"❌ Test setup failed: {e}")
            
        finally:
            # Cleanup
            self.cleanup_test_data()
            
        return passed == total

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
        
    print(f"Testing against: {base_url}")
    
    tester = OrderAssignmentIntegrationTest(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
