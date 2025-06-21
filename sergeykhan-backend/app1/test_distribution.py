#!/usr/bin/env python3
import os
import django
import sys

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import OrderCompletion, ProfitDistributionSettings
from decimal import Decimal

def test_distribution():
    print("Testing ProfitDistributionSettings and OrderCompletion...")
    
    # Test settings
    settings = ProfitDistributionSettings.get_settings()
    print(f"\nCurrent settings:")
    print(f"Master Paid: {settings.master_paid_percent}%")
    print(f"Master Balance: {settings.master_balance_percent}%")
    print(f"Curator: {settings.curator_percent}%")    
    print(f"Company: {settings.company_percent}%")
    total = settings.master_paid_percent + settings.master_balance_percent + settings.curator_percent + settings.company_percent
    print(f"Total: {total}%")
    
    # Test distribution calculation
    completion = OrderCompletion()
    completion.net_profit = Decimal('100000')  # 100,000 тенге profit
    completion.status = 'одобрен'  # Set status to approved
    completion.is_distributed = False  # Not yet distributed
    
    distribution = completion.calculate_distribution()
    if distribution:
        print(f"\nDistribution calculation for {completion.net_profit} тенге profit:")
        print(f"Master Paid (immediate): {distribution['master_paid']} тенге")
        print(f"Master Balance: {distribution['master_balance']} тенге")
        print(f"Master Total: {distribution['master_total']} тенге")
        print(f"Curator: {distribution['curator_share']} тенге")
        print(f"Company: {distribution['company_share']} тенге")
        total_distributed = distribution['master_total'] + distribution['curator_share'] + distribution['company_share']
        print(f"Total distributed: {total_distributed} тенге")
        print(f"Verification: {total_distributed} == {completion.net_profit}? {total_distributed == completion.net_profit}")
    else:
        print("Distribution not calculated (completion not approved or already distributed)")

if __name__ == "__main__":
    test_distribution()
