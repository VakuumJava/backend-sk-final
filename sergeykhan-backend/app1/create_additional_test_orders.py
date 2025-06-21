#!/usr/bin/env python3
"""
Скрипт для создания дополнительных тестовых заказов
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone
import random

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order

def create_additional_test_orders():
    print("🚀 Создание дополнительных тестовых заказов...")
    
    # Получаем существующих пользователей
    masters = CustomUser.objects.filter(role='master')
    operators = CustomUser.objects.filter(role='operator')
    
    # Дополнительные тестовые заказы
    additional_orders = [
        {
            'client_name': 'Владимир Тестировщиков',
            'client_phone': '+7 (701) 123-45-67',
            'description': 'Ремонт стиральной машины Samsung, не сливает воду',
            'street': 'ул. Абая',
            'house_number': '123',
            'apartment': '45',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Стиральная машина',
            'estimated_cost': 4500.0,
            'status': 'новый'
        },
        {
            'client_name': 'Айгуль Тестова',
            'client_phone': '+7 (702) 234-56-78',
            'description': 'Посудомоечная машина Bosch не включается',
            'street': 'пр. Назарбаева',
            'house_number': '56',
            'apartment': '78',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Посудомоечная машина',
            'estimated_cost': 5200.0,
            'status': 'в обработке'
        },
        {
            'client_name': 'Нурлан Токаев',
            'client_phone': '+7 (703) 345-67-89',
            'description': 'Кондиционер LG протекает, нужна чистка',
            'street': 'ул. Сатпаева',
            'house_number': '89',
            'apartment': '12',
            'service_type': 'Обслуживание техники',
            'equipment_type': 'Кондиционер',
            'estimated_cost': 3200.0,
            'status': 'назначен'
        },
        {
            'client_name': 'Алма Жанова',
            'client_phone': '+7 (704) 456-78-90',
            'description': 'Микроволновка перестала греть',
            'street': 'ул. Толе би',
            'house_number': '34',
            'apartment': '56',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Микроволновая печь',
            'estimated_cost': 2800.0,
            'status': 'выполняется'
        },
        {
            'client_name': 'Асхат Жумабеков',
            'client_phone': '+7 (705) 567-89-01',
            'description': 'Замена фильтра в пылесосе Dyson',
            'street': 'ул. Фурманова',
            'house_number': '91',
            'apartment': '23',
            'service_type': 'Обслуживание техники',
            'equipment_type': 'Пылесос',
            'estimated_cost': 1500.0,
            'status': 'ожидает_подтверждения'
        },
        {
            'client_name': 'Гульнара Абдуллина',
            'client_phone': '+7 (706) 678-90-12',
            'description': 'Телевизор Samsung не показывает изображение',
            'street': 'ул. Байтурсынова',
            'house_number': '67',
            'apartment': '89',
            'service_type': 'Ремонт техники',
            'equipment_type': 'Телевизор',
            'estimated_cost': 6800.0,
            'status': 'завершен'
        },
        {
            'client_name': 'Ерлан Касымов',
            'client_phone': '+7 (707) 789-01-23',
            'description': 'Холодильник сильно шумит',
            'street': 'ул. Розыбакиева',
            'house_number': '45',
            'apartment': '67',
            'service_type': 'Диагностика',
            'equipment_type': 'Холодильник',
            'estimated_cost': 1200.0,
            'status': 'отклонен'
        },
        {
            'client_name': 'Диана Смирнова',
            'client_phone': '+7 (708) 890-12-34',
            'description': 'Установка нового кондиционера Daikin',
            'street': 'ул. Жандосова',
            'house_number': '123',
            'apartment': '45',
            'service_type': 'Установка техники',
            'equipment_type': 'Кондиционер',
            'estimated_cost': 8500.0,
            'status': 'новый'
        }
    ]
    
    created_orders = []
    
    for i, order_data in enumerate(additional_orders):
        # Назначение оператора для некоторых заказов
        if operators.exists() and random.choice([True, False]):
            order_data['operator'] = random.choice(operators)
        
        # Назначение мастера для заказов со статусами назначен, выполняется, ожидает_подтверждения, завершен
        if order_data['status'] in ['назначен', 'выполняется', 'ожидает_подтверждения', 'завершен'] and masters.exists():
            order_data['assigned_master'] = random.choice(masters)
        
        # Устанавливаем разные даты создания
        hours_ago = random.randint(1, 72)  # от 1 до 72 часов назад
        created_at = timezone.now() - timedelta(hours=hours_ago, minutes=random.randint(0, 59))
        
        order = Order.objects.create(**order_data)
        order.created_at = created_at
        order.save()
        
        created_orders.append(order)
        
        print(f"✅ Заказ #{order.id}: {order.client_name} - {order.status}")
        if order.operator:
            print(f"   Оператор: {order.operator.first_name}")
        if order.assigned_master:
            print(f"   Мастер: {order.assigned_master.first_name}")
    
    print(f"\n🎉 Создано {len(created_orders)} дополнительных заказов")
    
    # Статистика по всем заказам
    print("\n============================================================")
    print("📊 ОБЩАЯ СТАТИСТИКА ПО ВСЕМ ЗАКАЗАМ")
    print("============================================================")
    
    all_orders = Order.objects.all()
    statuses = {}
    for order in all_orders:
        status = order.status
        if status in statuses:
            statuses[status] += 1
        else:
            statuses[status] = 1
    
    print(f"📋 Всего заказов в системе: {all_orders.count()}")
    print("\n📊 По статусам:")
    for status, count in statuses.items():
        print(f"  • {status}: {count} заказов")

if __name__ == '__main__':
    create_additional_test_orders()
