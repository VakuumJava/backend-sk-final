#!/usr/bin/env python
"""
Скрипт для проверки входа мастера и получения токена
"""

import os
import sys
import django

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

import requests
import json
from api1.models import CustomUser

def test_master_login():
    """Тестируем вход мастера и получение токена"""
    
    # Найдем мастера
    try:
        master = CustomUser.objects.filter(role='master').first()
        if not master:
            print("❌ Мастер не найден в базе данных")
            return
            
        print(f"🎯 Найден мастер: {master.email} (ID: {master.id})")
        
        # Попробуем войти
        login_data = {
            'email': master.email,
            'password': 'password123'  # Стандартный пароль из создания тестовых данных
        }
        
        print(f"📤 Пытаемся войти как: {master.email}")
        
        response = requests.post('http://localhost:8000/api/login/', json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешный вход!")
            print(f"🔑 Токен: {result.get('token', 'Не найден')}")
            print(f"👤 ID пользователя: {result.get('user_id', 'Не найден')}")
            print(f"📋 Роль: {result.get('role', 'Не найдена')}")
            
            token = result.get('token')
            if token:
                print(f"\n📋 Для входа в браузере выполните в консоли:")
                print(f"localStorage.setItem('authToken', '{token}')")
                print(f"localStorage.setItem('userId', '{result.get('user_id')}')")
                print(f"localStorage.setItem('userRole', '{result.get('role')}')")
                print("Затем обновите страницу")
                
        else:
            print(f"❌ Ошибка входа: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_master_login()
