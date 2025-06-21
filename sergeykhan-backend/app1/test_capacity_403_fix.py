#!/usr/bin/env python3
"""
Тест для проверки исправления ошибки HTTP 403 в capacity analysis
"""

import os
import sys
import django
import requests

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser
from rest_framework.authtoken.models import Token

def test_capacity_api_access():
    """Тестирование доступа к API capacity analysis для разных ролей"""
    
    print("🔧 Тестирование исправления HTTP 403 для capacity analysis...")
    
    base_url = 'http://127.0.0.1:8000'
    
    # Создаем тестовых пользователей разных ролей
    roles_to_test = ['master', 'curator', 'super-admin', 'operator']
    
    for role in roles_to_test:
        print(f"\n👤 Тестируем роль: {role}")
        
        # Создаем или получаем пользователя
        try:
            user = CustomUser.objects.get(email=f'{role}_test@example.com')
            print(f"   ✅ Пользователь найден: {user.email}")
        except CustomUser.DoesNotExist:
            user = CustomUser.objects.create_user(
                email=f'{role}_test@example.com',
                password='test123',
                role=role
            )
            print(f"   ✅ Пользователь создан: {user.email}")
        
        # Получаем токен
        token, created = Token.objects.get_or_create(user=user)
        headers = {
            'Authorization': f'Token {token.key}',
            'Content-Type': 'application/json'
        }
        
        # Тестируем capacity analysis endpoint
        print("   🔍 Тестируем /api/capacity/analysis/...")
        try:
            response = requests.get(f'{base_url}/api/capacity/analysis/', headers=headers)
            if response.status_code == 200:
                print(f"   ✅ Доступ разрешен (200)")
                data = response.json()
                print(f"   📊 Получены данные: сегодня {data['today']['date']}")
            elif response.status_code == 403:
                print(f"   ❌ Доступ запрещен (403) - ОШИБКА НЕ ИСПРАВЛЕНА!")
                return False
            else:
                print(f"   ⚠️ Неожиданный статус: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Сервер не запущен")
            return False
        
        # Тестируем weekly forecast endpoint
        print("   🔍 Тестируем /api/capacity/weekly-forecast/...")
        try:
            response = requests.get(f'{base_url}/api/capacity/weekly-forecast/', headers=headers)
            if response.status_code == 200:
                print(f"   ✅ Доступ разрешен (200)")
                data = response.json()
                print(f"   📈 Прогноз на {len(data['week_forecast'])} дней")
            elif response.status_code == 403:
                print(f"   ❌ Доступ запрещен (403) - ОШИБКА НЕ ИСПРАВЛЕНА!")
                return False
            else:
                print(f"   ⚠️ Неожиданный статус: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("   ⚠️ Сервер не запущен")
            return False
    
    print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Ошибка HTTP 403 исправлена!")
    return True

if __name__ == '__main__':
    test_capacity_api_access()
