#!/usr/bin/env python3
"""
Тест для проверки исправления системы распределения прибыли
"""

import os
import sys
import django
import requests
import json

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from api1.models import CustomUser, ProfitDistributionSettings, SystemLog

def test_profit_distribution_api():
    """Тест API настроек распределения прибыли"""
    
    print("🔧 Тестирование исправленной системы распределения прибыли...")
    
    # 1. Создаём или получаем супер-админа
    print("1. Создание/получение супер-админа...")
    try:
        super_admin = CustomUser.objects.get(email='super_admin@test.com')
        print(f"   ✅ Супер-админ найден: {super_admin.email}")
    except CustomUser.DoesNotExist:
        super_admin = CustomUser.objects.create_user(
            email='super_admin@test.com',
            password='admin123',
            role='super-admin'
        )
        print(f"   ✅ Супер-админ создан: {super_admin.email}")
    
    # 2. Получаем токен
    token, created = Token.objects.get_or_create(user=super_admin)
    print(f"   ✅ Токен получен: {token.key[:20]}...")
    
    # 3. Проверяем текущие настройки
    print("\n2. Проверка текущих настроек...")
    url = 'http://127.0.0.1:8000/api/profit-distribution/'
    headers = {'Authorization': f'Token {token.key}'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            current_settings = response.json()
            print("   ✅ Текущие настройки получены:")
            for key, value in current_settings.items():
                if key.endswith('_percent'):
                    print(f"      {key}: {value}%")
        else:
            print(f"   ❌ Ошибка получения настроек: {response.status_code}")
            print(f"      {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ⚠️ Сервер не запущен. Запустите сервер: python3 manage.py runserver")
        return False
    
    # 4. Обновляем настройки
    print("\n3. Обновление настроек...")
    new_settings = {
        'master_paid_percent': 25,
        'master_balance_percent': 35,
        'curator_percent': 10,
        'company_percent': 30
    }
    
    response = requests.put(url, headers=headers, json=new_settings)
    if response.status_code == 200:
        result = response.json()
        print("   ✅ Настройки успешно обновлены!")
        print(f"   📝 Изменения: {result.get('changes', 'Нет изменений')}")
        
        # Проверяем, что системный лог создался
        print("\n4. Проверка системного лога...")
        system_logs = SystemLog.objects.filter(
            action='percentage_settings_updated',
            performed_by=super_admin
        ).order_by('-created_at')[:1]
        
        if system_logs.exists():
            log = system_logs.first()
            print(f"   ✅ Системный лог создан: {log.description}")
            print(f"   📅 Время: {log.created_at}")
        else:
            print("   ❌ Системный лог не найден!")
            return False
            
    else:
        print(f"   ❌ Ошибка обновления: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    # 5. Проверяем валидацию (сумма не равна 100%)
    print("\n5. Проверка валидации (некорректные данные)...")
    invalid_settings = {
        'master_paid_percent': 40,
        'master_balance_percent': 40,
        'curator_percent': 10,
        'company_percent': 20  # Сумма = 110%
    }
    
    response = requests.put(url, headers=headers, json=invalid_settings)
    if response.status_code == 400:
        error_data = response.json()
        print("   ✅ Валидация работает корректно!")
        print(f"   📝 Ошибка: {error_data.get('error', 'Неизвестная ошибка')}")
    else:
        print(f"   ❌ Валидация не сработала! Статус: {response.status_code}")
        print(f"      {response.text}")
        return False
    
    print("\n🎉 Все тесты пройдены успешно!")
    print("✅ Система распределения прибыли работает корректно!")
    print("✅ Системное логирование функционирует!")
    print("✅ Валидация данных работает!")
    
    return True

def test_database_direct():
    """Прямое тестирование через Django ORM"""
    print("\n🔧 Прямое тестирование через Django ORM...")
    
    # Получаем настройки
    settings = ProfitDistributionSettings.get_settings()
    print(f"Текущие настройки: {settings.master_paid_percent}%, {settings.master_balance_percent}%, {settings.curator_percent}%, {settings.company_percent}%")
    
    # Проверяем валидацию
    try:
        settings.master_paid_percent = 50
        settings.master_balance_percent = 50
        settings.curator_percent = 10
        settings.company_percent = 10  # Сумма = 120%
        settings.clean()
        print("❌ Валидация не сработала!")
        return False
    except Exception as e:
        print(f"✅ Валидация работает: {e}")
    
    # Сбрасываем на корректные значения
    settings.master_paid_percent = 30
    settings.master_balance_percent = 30
    settings.curator_percent = 5
    settings.company_percent = 35
    settings.save()
    
    print("✅ Прямое тестирование пройдено!")
    return True

if __name__ == '__main__':
    print("🚀 Запуск комплексного тестирования системы распределения прибыли...")
    
    # Тестирование через ORM
    if not test_database_direct():
        sys.exit(1)
    
    # Тестирование через API
    if not test_profit_distribution_api():
        sys.exit(1)
    
    print("\n🎯 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("Система распределения прибыли полностью исправлена и готова к использованию!")
