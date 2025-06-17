#!/usr/bin/env python3
"""
Скрипт для создания тестовых мастеров, операторов и заказов
для полного тестирования системы
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order, Balance
from rest_framework.authtoken.models import Token

def create_test_data():
    print("🚀 Создание тестовых данных...")
    
    # Создание тестовых мастеров
    masters_data = [
        {
            'email': 'master1@test.com',
            'first_name': 'Алексей',
            'last_name': 'Петров',
            'password': 'test123456',
            'role': 'master'
        },
        {
            'email': 'master2@test.com',
            'first_name': 'Дмитрий',
            'last_name': 'Иванов',
            'password': 'test123456',
            'role': 'master'
        },
        {
            'email': 'master3@test.com',
            'first_name': 'Сергей',
            'last_name': 'Сидоров',
            'password': 'test123456',
            'role': 'master'
        },
        {
            'email': 'master4@test.com',
            'first_name': 'Андрей',
            'last_name': 'Козлов',
            'password': 'test123456',
            'role': 'master'
        }
    ]
    
    # Создание тестовых операторов
    operators_data = [
        {
            'email': 'operator1@test.com',
            'first_name': 'Мария',
            'last_name': 'Операторова',
            'password': 'test123456',
            'role': 'operator'
        },
        {
            'email': 'operator2@test.com',
            'first_name': 'Анна',
            'last_name': 'Диспетчерова',
            'password': 'test123456',
            'role': 'operator'
        }
    ]
    
    # Создание тестового куратора
    curator_data = {
        'email': 'curator1@test.com',
        'first_name': 'Елена',
        'last_name': 'Кураторова',
        'password': 'test123456',
        'role': 'curator'
    }
    
    created_users = []
    
    # Создание мастеров
    print("\n👷‍♂️ Создание мастеров...")
    for master_data in masters_data:
        user, created = CustomUser.objects.get_or_create(
            email=master_data['email'],
            defaults=master_data
        )
        if created:
            user.set_password(master_data['password'])
            user.save()
            
            # Создание токена для мастера
            token, _ = Token.objects.get_or_create(user=user)
            
            # Создание баланса для мастера
            Balance.objects.get_or_create(
                user=user,
                defaults={'amount': 0.0, 'paid_amount': 0.0}
            )
            
            print(f"✅ Мастер создан: {user.first_name} {user.last_name} ({user.email})")
            print(f"   Token: {token.key}")
            created_users.append(user)
        else:
            print(f"⚠️  Мастер уже существует: {user.email}")
            created_users.append(user)
    
    # Создание операторов
    print("\n📞 Создание операторов...")
    for operator_data in operators_data:
        user, created = CustomUser.objects.get_or_create(
            email=operator_data['email'],
            defaults=operator_data
        )
        if created:
            user.set_password(operator_data['password'])
            user.save()
            
            # Создание токена для оператора
            token, _ = Token.objects.get_or_create(user=user)
            
            print(f"✅ Оператор создан: {user.first_name} {user.last_name} ({user.email})")
            print(f"   Token: {token.key}")
            created_users.append(user)
        else:
            print(f"⚠️  Оператор уже существует: {user.email}")
            created_users.append(user)
    
    # Создание куратора
    print("\n👨‍💼 Создание куратора...")
    user, created = CustomUser.objects.get_or_create(
        email=curator_data['email'],
        defaults=curator_data
    )
    if created:
        user.set_password(curator_data['password'])
        user.save()
        
        # Создание токена для куратора
        token, _ = Token.objects.get_or_create(user=user)
        
        print(f"✅ Куратор создан: {user.first_name} {user.last_name} ({user.email})")
        print(f"   Token: {token.key}")
        created_users.append(user)
    else:
        print(f"⚠️  Куратор уже существует: {user.email}")
        created_users.append(user)
    
    # Создание тестовых заказов
    print("\n📋 Создание тестовых заказов...")
    
    masters = CustomUser.objects.filter(role='master')
    operators = CustomUser.objects.filter(role='operator')
    
    orders_data = [
        {
            'client_name': 'Иван Тестов',
            'client_phone': '+7 (900) 123-45-67',
            'description': 'Ремонт стиральной машины Samsung',
            'street': 'ул. Ленина',
            'house_number': '10',
            'apartment': '25',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Стиральная машина',
            'estimated_cost': 3500.0,
            'status': 'новый'
        },
        {
            'client_name': 'Мария Петрова',
            'client_phone': '+7 (900) 234-56-78',
            'description': 'Установка посудомоечной машины',
            'street': 'пр. Мира',
            'house_number': '15',
            'apartment': '102',
            'service_type': 'Установка техники',
            'equipment_type': 'Посудомоечная машина',
            'estimated_cost': 2500.0,
            'status': 'новый'
        },
        {
            'client_name': 'Александр Сидоров',
            'client_phone': '+7 (900) 345-67-89',
            'description': 'Ремонт холодильника LG',
            'street': 'ул. Гагарина',
            'house_number': '22',
            'apartment': '5',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Холодильник',
            'estimated_cost': 4200.0,
            'status': 'в обработке'
        },
        {
            'client_name': 'Елена Козлова',
            'client_phone': '+7 (900) 456-78-90',
            'description': 'Чистка кондиционера',
            'street': 'ул. Пушкина',
            'house_number': '8',
            'apartment': '33',
            'service_type': 'Обслуживание техники',
            'equipment_type': 'Кондиционер',
            'estimated_cost': 1800.0,
            'status': 'новый'
        },
        {
            'client_name': 'Дмитрий Волков',
            'client_phone': '+7 (900) 567-89-01',
            'description': 'Замена компрессора в холодильнике',
            'street': 'ул. Советская',
            'house_number': '45',
            'apartment': '12',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Холодильник',
            'estimated_cost': 6500.0,
            'status': 'назначен'
        },
        {
            'client_name': 'Анна Морозова',
            'client_phone': '+7 (900) 678-90-12',
            'description': 'Ремонт микроволновки',
            'street': 'ул. Молодежная',
            'house_number': '17',
            'apartment': '8',
            'service_type': 'Ремонт бытовой техники',
            'equipment_type': 'Микроволновая печь',
            'estimated_cost': 2200.0,
            'status': 'в работе'
        }
    ]
    
    created_orders = []
    for i, order_data in enumerate(orders_data):
        # Назначение оператора для некоторых заказов
        if i < 4 and operators.exists():
            order_data['operator'] = operators[i % operators.count()]
        
        # Назначение мастера для некоторых заказов
        if order_data['status'] in ['назначен', 'в работе'] and masters.exists():
            order_data['assigned_master'] = masters[i % masters.count()]
        
        # Устанавливаем дату создания в разное время
        created_at = timezone.now() - timedelta(hours=i*2, minutes=i*15)
        
        order = Order.objects.create(**order_data)
        order.created_at = created_at
        order.save()
        
        created_orders.append(order)
        
        master_info = f" → {order.assigned_master.first_name} {order.assigned_master.last_name}" if order.assigned_master else ""
        operator_info = f" (Оператор: {order.operator.first_name})" if order.operator else ""
        
        print(f"✅ Заказ #{order.id}: {order.client_name} - {order.status}{master_info}{operator_info}")
    
    print(f"\n🎉 Создано {len(created_orders)} тестовых заказов")
    
    # Вывод сводки по созданным данным
    print("\n" + "="*60)
    print("📊 СВОДКА ПО СОЗДАННЫМ ДАННЫМ")
    print("="*60)
    
    print(f"\n👷‍♂️ МАСТЕРА ({masters.count()}):")
    for master in masters:
        token = Token.objects.get(user=master).key
        assigned_orders = Order.objects.filter(assigned_master=master).count()
        print(f"  • {master.first_name} {master.last_name} ({master.email})")
        print(f"    Token: {token}")
        print(f"    Назначено заказов: {assigned_orders}")
    
    print(f"\n📞 ОПЕРАТОРЫ ({operators.count()}):")
    for operator in operators:
        token = Token.objects.get(user=operator).key
        handled_orders = Order.objects.filter(operator=operator).count()
        print(f"  • {operator.first_name} {operator.last_name} ({operator.email})")
        print(f"    Token: {token}")
        print(f"    Обработано заказов: {handled_orders}")
    
    curators = CustomUser.objects.filter(role='curator')
    print(f"\n👨‍💼 КУРАТОРЫ ({curators.count()}):")
    for curator in curators:
        token = Token.objects.get(user=curator).key
        print(f"  • {curator.first_name} {curator.last_name} ({curator.email})")
        print(f"    Token: {token}")
    
    print(f"\n📋 ЗАКАЗЫ ПО СТАТУСАМ:")
    statuses = Order.objects.values_list('status', flat=True).distinct()
    for status in statuses:
        count = Order.objects.filter(status=status).count()
        print(f"  • {status}: {count} заказов")
    
    print(f"\n🔑 СУПЕР-АДМИН:")
    superadmin = CustomUser.objects.filter(role='super-admin').first()
    if superadmin:
        token = Token.objects.get(user=superadmin).key
        print(f"  • {superadmin.email}")
        print(f"    Token: {token}")
    
    print("\n" + "="*60)
    print("✅ ВСЕ ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ УСПЕШНО!")
    print("="*60)
    
    return {
        'masters': list(masters),
        'operators': list(operators),
        'curators': list(curators),
        'orders': created_orders
    }

if __name__ == "__main__":
    create_test_data()
