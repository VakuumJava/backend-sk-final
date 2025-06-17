#!/usr/bin/env python3
"""
Test profit distribution after fixing the settings bug
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order, OrderCompletion, MasterProfitSettings, ProfitDistributionSettings

def test_profit_settings():
    print("🧪 Тестируем исправление настроек распределения прибыли...")
    
    # Get a master
    master = CustomUser.objects.filter(role='master').first()
    if not master:
        print("❌ Мастер не найден")
        return
    
    print(f"✅ Тестируем с мастером: {master.email}")
    
    # Test global settings
    try:
        global_settings = ProfitDistributionSettings.get_settings()
        print(f"✅ Глобальные настройки получены: {type(global_settings)}")
        print(f"   master_paid_percent: {global_settings.master_paid_percent}")
        print(f"   master_balance_percent: {global_settings.master_balance_percent}")
        print(f"   curator_percent: {global_settings.curator_percent}")
        print(f"   company_percent: {global_settings.company_percent}")
    except Exception as e:
        print(f"❌ Ошибка получения глобальных настроек: {e}")
        return
    
    # Test master-specific settings function
    try:
        settings = MasterProfitSettings.get_settings_for_master(master)
        print(f"✅ Настройки для мастера получены: {type(settings)}")
        print(f"   settings: {settings}")
    except Exception as e:
        print(f"❌ Ошибка получения настроек мастера: {e}")
        return
    
    # Test calculation on completed order if any
    try:
        completion = OrderCompletion.objects.filter(
            order__assigned_master=master,
            status='одобрен'
        ).first()
        
        if completion:
            print(f"✅ Найдено завершение заказа для тестирования: {completion.id}")
            distribution = completion.calculate_distribution()
            if distribution:
                print(f"✅ Распределение рассчитано успешно:")
                print(f"   master_immediate: {distribution['master_immediate']}")
                print(f"   master_deferred: {distribution['master_deferred']}")
                print(f"   curator_share: {distribution['curator_share']}")
                print(f"   company_share: {distribution['company_share']}")
            else:
                print(f"❌ Не удалось рассчитать распределение")
        else:
            print("ℹ️ Нет одобренных завершений для тестирования")
            
    except Exception as e:
        print(f"❌ Ошибка тестирования распределения: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_profit_settings()
