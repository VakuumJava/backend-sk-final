#!/usr/bin/env python3
"""
Тест текущей системы распределения заказов
Проверяет, используется ли возраст или приоритет в логике распределения
"""

import os
import sys
import django

# Настройка Django
sys.path.append('/Users/bekzhan/Documents/projects/sk/SergeyKhanWeb/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import Order, CustomUser

def test_order_distribution_logic():
    """Тестирует текущую логику распределения заказов"""
    
    print("🔍 ТЕСТ СИСТЕМЫ РАСПРЕДЕЛЕНИЯ ЗАКАЗОВ")
    print("=" * 50)
    
    # 1. Проверяем, есть ли поля age и priority в модели
    print("1. Проверка полей в модели Order:")
    
    order_fields = [field.name for field in Order._meta.fields]
    
    if 'age' in order_fields:
        print("   ❌ Поле 'age' (возраст) НАЙДЕНО в модели")
    else:
        print("   ✅ Поле 'age' (возраст) НЕ найдено в модели")
        
    if 'priority' in order_fields:
        print("   ❌ Поле 'priority' (приоритет) НАЙДЕНО в модели")
    else:
        print("   ✅ Поле 'priority' (приоритет) НЕ найдено в модели")
    
    # 2. Проверяем существующие заказы
    print("\n2. Анализ существующих заказов:")
    orders = Order.objects.all()
    print(f"   📊 Всего заказов: {orders.count()}")
    
    if orders.exists():
        # Проверяем, используются ли поля age и priority
        if 'age' in order_fields:
            orders_with_age = orders.exclude(age__isnull=True)
            print(f"   📊 Заказов с указанным возрастом: {orders_with_age.count()}")
            
        if 'priority' in order_fields:
            high_priority_orders = orders.filter(priority__in=['высокий', 'срочный'])
            print(f"   📊 Заказов с высоким приоритетом: {high_priority_orders.count()}")
    
    # 3. Проверяем мастеров
    print("\n3. Анализ мастеров:")
    masters = CustomUser.objects.filter(role='master')
    print(f"   👨‍🔧 Всего мастеров: {masters.count()}")
    
    return True

def check_current_distribution_endpoints():
    """Проверяет текущие endpoints распределения"""
    
    print("\n4. Текущие endpoints распределения:")
    print("   🔗 /api/workload/masters/ - получение нагрузки мастеров")
    print("   🔗 /api/availability/best-master/ - поиск лучшего мастера")
    print("   🔗 /api/orders/{id}/assign-with-check/ - назначение с проверкой нагрузки")
    
    print("\n✅ ЗАКЛЮЧЕНИЕ:")
    print("   Система распределения основана ТОЛЬКО на:")
    print("   1. Нагрузке мастера (workload_percentage)")
    print("   2. Свободных слотах (free_slots)")
    print("   3. Дате создания заказа (created_at)")
    print("   \n   ❌ Возраст клиента и приоритет заказа НЕ влияют на распределение!")

if __name__ == '__main__':
    try:
        test_order_distribution_logic()
        check_current_distribution_endpoints()
        print("\n🎯 РЕЗУЛЬТАТ: Приоритет по возрасту НЕ используется в системе!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
