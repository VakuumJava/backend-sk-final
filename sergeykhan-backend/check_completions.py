#!/usr/bin/env python3
"""
Скрипт для проверки статуса завершений
"""

import os
import sys
import django

# Добавляем путь к Django проекту
sys.path.insert(0, '/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')

# Инициализируем Django
django.setup()

from api1.models import OrderCompletion

def check_completions():
    """Проверяет завершения заказов"""
    
    print("=== ПРОВЕРКА ЗАВЕРШЕНИЙ ЗАКАЗОВ ===\n")
    
    completions = OrderCompletion.objects.all()
    print(f"Всего завершений: {completions.count()}")
    
    for completion in completions:
        print(f"\nЗавершение #{completion.id}:")
        print(f"  Заказ: #{completion.order.id}")
        print(f"  Статус: {completion.status}")
        print(f"  Мастер: {completion.master.get_full_name() if completion.master else 'Не указан'}")
        print(f"  Чистая прибыль: {completion.net_profit} тенге")
        print(f"  Распределено: {completion.is_distributed}")
        
        # Пробуем получить распределение
        try:
            distribution = completion.calculate_distribution()
            if distribution:
                print(f"  ✅ Распределение доступно")
                print(f"    - К выплате: {distribution['master_immediate']} тенге")
                print(f"    - К балансу: {distribution['master_immediate'] + distribution['master_deferred']} тенге")
            else:
                print(f"  ❌ Распределение недоступно")
                # Проверим причину
                if completion.status != 'одобрен':
                    print(f"    Причина: статус не 'одобрен' (текущий: {completion.status})")
                if completion.is_distributed:
                    print(f"    Причина: уже распределено")
                if not (completion.order.assigned_master or completion.order.transferred_to):
                    print(f"    Причина: мастер не назначен")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

if __name__ == "__main__":
    check_completions()
