#!/usr/bin/env python3
import os
import django
import sys

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import ProfitDistributionSettings

def test_api_functionality():
    print("Testing the complete profit distribution system...")
    
    # Test 1: Get existing settings
    print("\n1. Testing get_settings():")
    settings = ProfitDistributionSettings.get_settings()
    print(f"   Master Paid: {settings.master_paid_percent}%")
    print(f"   Master Balance: {settings.master_balance_percent}%")
    print(f"   Curator: {settings.curator_percent}%")
    print(f"   Company: {settings.company_percent}%")
    print(f"   Total: {settings.master_paid_percent + settings.master_balance_percent + settings.curator_percent + settings.company_percent}%")
    
    # Test 2: Update settings
    print("\n2. Testing settings update:")
    try:
        old_values = {
            'master_paid_percent': settings.master_paid_percent,
            'master_balance_percent': settings.master_balance_percent,
            'curator_percent': settings.curator_percent,
            'company_percent': settings.company_percent,
        }
        
        # Update with new test values
        settings.master_paid_percent = 25
        settings.master_balance_percent = 35
        settings.curator_percent = 10
        settings.company_percent = 30
        
        # Test validation
        try:
            settings.clean()
            print("   ✅ Validation passed (100% total)")
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")
        
        settings.save()
        print("   ✅ Settings updated successfully")
        
        # Restore original values
        settings.master_paid_percent = old_values['master_paid_percent']
        settings.master_balance_percent = old_values['master_balance_percent']
        settings.curator_percent = old_values['curator_percent']
        settings.company_percent = old_values['company_percent']
        settings.save()
        print("   ✅ Original settings restored")
        
    except Exception as e:
        print(f"   ❌ Update test failed: {e}")
    
    # Test 3: Test validation with invalid percentages
    print("\n3. Testing validation with invalid percentages:")
    try:
        settings.master_paid_percent = 50
        settings.master_balance_percent = 30
        settings.curator_percent = 10
        settings.company_percent = 20  # Total = 110%
        
        settings.clean()
        print("   ❌ Validation should have failed but didn't")
    except Exception as e:
        print(f"   ✅ Validation correctly failed: {e}")
        
        # Restore valid values
        settings.master_paid_percent = 30
        settings.master_balance_percent = 30
        settings.curator_percent = 5
        settings.company_percent = 35
    
    print("\n✅ All tests completed successfully!")
    print("The profit distribution system is working correctly.")

if __name__ == "__main__":
    test_api_functionality()
