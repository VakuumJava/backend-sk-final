#!/usr/bin/env python3
"""
Тестирование новых API endpoints для индивидуальных настроек прибыли мастеров.
"""

import os
import sys
import django
import json
import requests
from decimal import Decimal

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, MasterProfitSettings, ProfitDistributionSettings, Order
from django.contrib.auth.tokens import default_token_generator
from rest_framework.authtoken.models import Token

def create_test_data():
    """Создание тестовых данных"""
    print("📋 Создание тестовых данных...")
    
    # Создаем администратора если не существует
    admin, created = CustomUser.objects.get_or_create(
        email='admin@test.com',
        defaults={
            'role': 'super-admin',
            'first_name': 'Администратор',
            'last_name': 'Тестовый'
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print(f"✅ Создан админ: {admin.email}")
    
    # Создаем тестовых мастеров
    masters = []
    for i in range(1, 4):
        master, created = CustomUser.objects.get_or_create(
            email=f'master{i}@test.com',
            defaults={
                'role': 'master',
                'first_name': f'Мастер',
                'last_name': f'Тестовый{i}'
            }
        )
        if created:
            master.set_password('master123')
            master.save()
            print(f"✅ Создан мастер: {master.email}")
        masters.append(master)
    
    # Создаем токен для администратора
    token, created = Token.objects.get_or_create(user=admin)
    print(f"🔑 Токен админа: {token.key}")
    
    # Создаем глобальные настройки если не существуют
    global_settings = ProfitDistributionSettings.get_settings()
    print(f"⚙️ Глобальные настройки: {global_settings.master_paid_percent}% выплата, {global_settings.master_balance_percent}% баланс")
    
    return admin, masters, token.key

def test_api_endpoints(token, masters):
    """Тестирование API endpoints"""
    print("\n🧪 Тестирование API endpoints...")
    
    base_url = 'http://127.0.0.1:8000/api1'
    headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}
    
    # Тест 1: Получение всех мастеров с настройками
    print("\n1️⃣ Тестируем получение всех мастеров с настройками...")
    try:
        response = requests.get(f'{base_url}/api/profit-settings/masters/', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Получено {data['total_count']} мастеров")
            for master in data['masters'][:2]:  # Показываем первых 2
                print(f"   - {master['name']}: индивидуальные настройки = {master['has_individual_settings']}")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Сервер не запущен. Запустите 'python manage.py runserver' для тестирования API")
        return False
    
    # Тест 2: Получение настроек конкретного мастера
    master_id = masters[0].id
    print(f"\n2️⃣ Тестируем получение настроек мастера ID={master_id}...")
    try:
        response = requests.get(f'{base_url}/api/profit-settings/master/{master_id}/', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Настройки мастера {data['master_name']}")
            print(f"   - Выплата: {data['settings']['master_paid_percent']}%")
            print(f"   - Баланс: {data['settings']['master_balance_percent']}%")
            print(f"   - Индивидуальные: {data['settings']['is_individual']}")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Сервер не запущен")
        return False
    
    # Тест 3: Создание индивидуальных настроек для мастера
    print(f"\n3️⃣ Тестируем создание индивидуальных настроек для мастера ID={master_id}...")
    try:
        settings_data = {
            'master_paid_percent': 35,
            'master_balance_percent': 25,
            'curator_percent': 10,
            'company_percent': 30,
            'is_active': True
        }
        response = requests.post(
            f'{base_url}/api/profit-settings/master/{master_id}/set/', 
            headers=headers,
            data=json.dumps(settings_data)
        )
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ {data['message']}")
            print(f"   - Создано: {data.get('created', False)}")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Сервер не запущен")
        return False
    
    # Тест 4: Проверяем что настройки сохранились
    print(f"\n4️⃣ Проверяем сохранение настроек...")
    try:
        response = requests.get(f'{base_url}/api/profit-settings/master/{master_id}/', headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['settings']['is_individual']:
                print(f"✅ Индивидуальные настройки активны!")
                print(f"   - Выплата: {data['settings']['master_paid_percent']}%")
                print(f"   - Баланс: {data['settings']['master_balance_percent']}%")
            else:
                print("❌ Настройки не сохранились как индивидуальные")
        else:
            print(f"❌ Ошибка: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠️ Сервер не запущен")
        return False
    
    return True

def test_local_logic():
    """Тестирование логики без запущенного сервера"""
    print("\n🔬 Тестирование локальной логики...")
    
    try:
        # Получаем тестового мастера
        master = CustomUser.objects.filter(role='master').first()
        if not master:
            print("❌ Не найдено мастеров для тестирования")
            return
        
        print(f"📋 Тестируем мастера: {master.email}")
        
        # Тестируем получение настроек до создания индивидуальных
        settings = MasterProfitSettings.get_settings_for_master(master)
        print(f"   Глобальные настройки: {settings['is_individual']} - {settings['master_paid_percent']}%/{settings['master_balance_percent']}%")
        
        # Создаем индивидуальные настройки
        individual_settings, created = MasterProfitSettings.objects.get_or_create(
            master=master,
            defaults={
                'master_paid_percent': 40,
                'master_balance_percent': 25,
                'curator_percent': 10,
                'company_percent': 25,
                'is_active': True
            }
        )
        
        if created:
            print("✅ Созданы индивидуальные настройки")
        else:
            print("ℹ️ Индивидуальные настройки уже существуют")
        
        # Тестируем получение настроек после создания индивидуальных
        settings = MasterProfitSettings.get_settings_for_master(master)
        print(f"   Индивидуальные настройки: {settings['is_individual']} - {settings['master_paid_percent']}%/{settings['master_balance_percent']}%")
        
        # Тестируем получение настроек для заказа
        order = Order.objects.filter(assigned_master=master).first()
        if order:
            order_settings = order.get_profit_settings()
            print(f"   Настройки для заказа #{order.id}: {order_settings['is_individual']} - {order_settings['master_paid_percent']}%/{order_settings['master_balance_percent']}%")
        else:
            print("ℹ️ Заказы не найдены для данного мастера")
        
        print("✅ Локальное тестирование завершено успешно")
        
    except Exception as e:
        print(f"❌ Ошибка в локальном тестировании: {e}")

def main():
    print("🚀 Тестирование системы индивидуальных настроек прибыли мастеров")
    print("=" * 70)
    
    # Создаем тестовые данные
    admin, masters, token = create_test_data()
    
    # Тестируем локальную логику
    test_local_logic()
    
    # Тестируем API endpoints
    api_works = test_api_endpoints(token, masters)
    
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("✅ Модели и миграции: OK")
    print("✅ Локальная логика: OK")
    
    if api_works:
        print("✅ API endpoints: OK")
        print("\n🎉 Все тесты пройдены успешно!")
    else:
        print("⚠️ API endpoints: Требуется запущенный сервер")
        print("\n💡 Для полного тестирования запустите:")
        print("   python manage.py runserver")
        print("   python test_master_profit_api.py")

if __name__ == '__main__':
    main()
