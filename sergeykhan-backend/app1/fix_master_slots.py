#!/usr/bin/env python3
"""
Исправляем проблему со слотами мастера
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order
from rest_framework.authtoken.models import Token

def fix_master_slots():
    """Исправляем проблему со слотами мастера"""
    
    # Найдем нашего тестового мастера
    try:
        master = CustomUser.objects.get(id=3, email='master1@test.com')
        print(f"👤 Найден мастер: {master.first_name} {master.last_name} (ID: {master.id})")
        
        # Проверим текущие заказы
        current_orders = Order.objects.filter(
            assigned_master=master,
            status__in=['назначен', 'выполняется']
        )
        
        print(f"📋 Текущие заказы мастера: {current_orders.count()}")
        for order in current_orders:
            print(f"  - Заказ #{order.id}: {order.client_name} ({order.status})")
        
        # Увеличим лимит заказов для мастера
        if not hasattr(master, 'max_orders_per_day'):
            master.max_orders_per_day = 20  # Увеличиваем лимит
            master.save()
            print(f"✅ Установлен лимит заказов: {master.max_orders_per_day}")
        
        # Или освободим несколько заказов
        if current_orders.count() >= 8:
            # Завершим несколько заказов
            orders_to_complete = current_orders[:3]
            for order in orders_to_complete:
                order.status = 'завершен'
                order.save()
                print(f"✅ Завершен заказ #{order.id}")
            
            print(f"🔄 Освобождено {len(orders_to_complete)} слотов")
        
        # Проверим оставшиеся заказы
        remaining_orders = Order.objects.filter(
            assigned_master=master,
            status__in=['назначен', 'выполняется']
        ).count()
        
        print(f"📊 Итого:")
        print(f"  - Назначенных заказов: {remaining_orders}")
        print(f"  - Свободных слотов: {getattr(master, 'max_orders_per_day', 8) - remaining_orders}")
        
        # Покажем доступные заказы для взятия
        available_orders = Order.objects.filter(status='новый')[:5]
        print(f"\n📋 Доступные заказы для взятия ({available_orders.count()}):")
        for order in available_orders:
            print(f"  - Заказ #{order.id}: {order.client_name} - {order.full_address}")
            
    except CustomUser.DoesNotExist:
        print("❌ Мастер с ID 3 не найден!")
        return False
    
    return True

if __name__ == "__main__":
    print("=== Исправление проблемы со слотами мастера ===")
    fix_master_slots()
