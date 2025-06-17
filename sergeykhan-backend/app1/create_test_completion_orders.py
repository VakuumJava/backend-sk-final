#!/usr/bin/env python3
"""
Скрипт для создания тестовых заказов для проверки завершения заказов.
Создает заказы в статусе 'назначен' или 'выполняется', которые можно использовать 
для ручного тестирования процесса завершения заказов.
"""
import os
import sys
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order, MasterAvailability

def create_test_completion_orders():
    print("🚀 Создание тестовых заказов для проверки завершения...")
    
    # Получаем мастеров
    masters = CustomUser.objects.filter(role='master')
    if not masters.exists():
        print("❌ Нет доступных мастеров в системе. Пожалуйста, сначала создайте мастеров.")
        return
    
    # Получаем операторов
    operators = CustomUser.objects.filter(role='operator')
    if not operators.exists():
        print("❌ Нет доступных операторов в системе. Пожалуйста, сначала создайте операторов.")
        return
    
    # Получаем кураторов
    curators = CustomUser.objects.filter(role='curator')
    
    # Тестовые заказы для завершения
    service_types = [
        "Ремонт бытовой техники", 
        "Установка техники", 
        "Обслуживание техники", 
        "Диагностика", 
        "Консультация"
    ]
    
    equipment_types = [
        "Холодильник", 
        "Стиральная машина", 
        "Посудомоечная машина", 
        "Телевизор", 
        "Микроволновая печь", 
        "Кондиционер", 
        "Пылесос", 
        "Водонагреватель"
    ]
    
    brands = [
        "Samsung", 
        "LG", 
        "Bosch", 
        "Electrolux", 
        "Sony", 
        "Haier", 
        "Siemens", 
        "Zanussi", 
        "Indesit", 
        "BEKO"
    ]
    
    problems = [
        "не включается", 
        "шумит при работе", 
        "протекает", 
        "не греет", 
        "выдает ошибку", 
        "не открывается", 
        "треснул экран",
        "требуется замена детали",
        "нужна настройка",
        "неисправность компрессора"
    ]
    
    streets = [
        "ул. Ленина", 
        "пр. Мира", 
        "ул. Гагарина", 
        "ул. Пушкина", 
        "ул. Советская", 
        "ул. Молодежная", 
        "ул. Центральная", 
        "пр. Победы", 
        "ул. Набережная", 
        "ул. Московская"
    ]
    
    # Генерируем имена
    first_names = [
        "Александр", "Иван", "Петр", "Михаил", "Дмитрий", 
        "Мария", "Екатерина", "Ольга", "Анна", "Елена"
    ]
    
    last_names = [
        "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", 
        "Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова"
    ]
    
    # Создаем 10 тестовых заказов
    for i in range(10):
        # Случайно выбираем детали заказа
        service_type = random.choice(service_types)
        equipment_type = random.choice(equipment_types)
        brand = random.choice(brands)
        problem = random.choice(problems)
        street = random.choice(streets)
        
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        client_name = f"{first_name} {last_name}"
        
        # Создаем номер телефона
        phone = f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
        
        # Формируем описание заказа
        description = f"{service_type}: {brand} {equipment_type} {problem}"
        
        # Выбираем случайного мастера
        master = random.choice(masters)
        
        # Выбираем случайного оператора
        operator = random.choice(operators)
        
        # Выбираем куратора, если есть
        curator = random.choice(curators) if curators.exists() else None
        
        # Выбираем статус (назначен или выполняется)
        status = random.choice(['назначен', 'выполняется'])
        
        # Создаем даты для заказа
        scheduled_date = (timezone.now() + timedelta(days=random.randint(1, 5))).date()
        
        # Создаем время для заказа (с 9:00 до 18:00)
        hour = random.randint(9, 17)
        minute = random.choice([0, 15, 30, 45])
        scheduled_time = datetime.strptime(f"{hour}:{minute}", "%H:%M").time()
        
        # Проверяем, есть ли доступность у мастера в это время
        availability = MasterAvailability.objects.filter(
            master=master,
            date=scheduled_date,
            start_time__lte=scheduled_time,
            end_time__gt=scheduled_time
        ).first()
        
        # Если нет доступности, создаем её
        if not availability:
            start_hour = max(9, hour - 1)
            end_hour = min(18, hour + 1)
            
            MasterAvailability.objects.create(
                master=master,
                date=scheduled_date,
                start_time=datetime.strptime(f"{start_hour}:00", "%H:%M").time(),
                end_time=datetime.strptime(f"{end_hour}:00", "%H:%M").time()
            )
        
        # Создаем заказ
        order_data = {
            'client_name': client_name,
            'client_phone': phone,
            'description': description,
            'street': street,
            'house_number': str(random.randint(1, 100)),
            'apartment': str(random.randint(1, 100)),
            'service_type': service_type,
            'equipment_type': equipment_type,
            'estimated_cost': random.randint(1500, 7000),
            'status': status,
            'operator': operator,
            'curator': curator,
            'assigned_master': master,
            'scheduled_date': scheduled_date,
            'scheduled_time': scheduled_time,
            'is_test': True  # Отмечаем как тестовый
        }
        
        # Создаем заказ
        order = Order.objects.create(**order_data)
        
        # Устанавливаем время создания
        created_at = timezone.now() - timedelta(days=random.randint(1, 3))
        order.created_at = created_at
        order.save()
        
        # Выводим информацию о созданном заказе
        master_info = f" → {order.assigned_master.first_name} {order.assigned_master.last_name}"
        operator_info = f" (Оператор: {order.operator.first_name})" if order.operator else ""
        schedule_info = f" | Назначено на: {order.scheduled_date.strftime('%d.%m.%Y')} {order.scheduled_time.strftime('%H:%M')}"
        
        print(f"✅ Заказ #{order.id}: {order.client_name} - {order.status}{master_info}{operator_info}{schedule_info}")

if __name__ == "__main__":
    create_test_completion_orders()
    print("\n✅ Готово! Тестовые заказы для проверки завершения созданы.")
