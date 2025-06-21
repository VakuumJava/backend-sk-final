#!/usr/bin/env python3
"""
Скрипт для тестирования логина мастера
"""
import requests
import json

# URL бэкенда
BASE_URL = "http://localhost:8000"

def test_login(email, password):
    """Тестирует логин мастера"""
    login_url = f"{BASE_URL}/login/"
    
    data = {
        "email": email,
        "password": password
    }
    
    print(f"Попытка логина для {email}...")
    
    try:
        response = requests.post(login_url, json=data)
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешный логин!")
            print(f"Token: {result.get('token')}")
            print(f"User ID: {result.get('user', {}).get('id')}")
            print(f"Email: {result.get('user', {}).get('email')}")
            print(f"Role: {result.get('user', {}).get('role')}")
            return result
        else:
            print("❌ Ошибка логина")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу. Убедитесь, что бэкенд запущен на http://localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def main():
    print("=== Тестирование логина мастера ===")
    
    # Попробуем разные варианты email/password для мастеров
    test_credentials = [
        ("master1@test.com", "test123456"),
        ("master2@test.com", "test123456"),
        ("master3@test.com", "test123456"),
        ("master4@test.com", "test123456"),
        ("master@test.com", "password"),
        ("master@test.com", "test123456"),
    ]
    
    for email, password in test_credentials:
        result = test_login(email, password)
        if result and result.get('user', {}).get('role') == 'master':
            print(f"\n🎉 Найден мастер! Используйте эти данные:")
            print(f"Email: {email}")
            print(f"Password: {password}")
            print(f"Token: {result.get('token')}")
            print(f"User ID: {result.get('user', {}).get('id')}")
            break
        print()
    else:
        print("\n❌ Не найден ни один рабочий мастер")
        print("Возможно, нужно создать тестового мастера в базе данных")

if __name__ == "__main__":
    main()
