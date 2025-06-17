#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений фронтенда мастера
"""

import requests
import json

def test_master_frontend_fixes():
    """Тестирует исправления для панели мастера"""
    
    # Токен мастера (master1@test.com)
    token = 'ee57c0206252baeceafcef56d7e32e78ec6e7d3f'
    master_id = 3
    
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ПАНЕЛИ МАСТЕРА")
    print("=" * 50)
    
    # 1. Тест: получение доступных заказов с информацией о дистанционности
    print("\n1️⃣ Тестируем получение доступных заказов с дистанционностью...")
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/distance/orders/available/',
            headers={'Authorization': f'Token {token}'}
        )
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Заказы получены: {len(data.get('orders', []))} заказов")
            if 'distance_info' in data:
                distance_info = data['distance_info']
                print(f"   ✅ Информация о дистанционности:")
                print(f"       - Уровень: {distance_info['distance_level']}")
                print(f"       - Название: {distance_info['distance_level_name']}")
                print(f"       - Количество заказов: {distance_info['orders_count']}")
            else:
                print("   ❌ Информация о дистанционности отсутствует")
        else:
            print(f"   ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    
    # 2. Тест: назначение заказа мастеру
    print("\n2️⃣ Тестируем назначение заказа мастеру...")
    try:
        # Сначала получим ID первого доступного заказа
        response = requests.get(
            'http://127.0.0.1:8000/api/distance/orders/available/',
            headers={'Authorization': f'Token {token}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            available_orders = data.get('orders', [])
            
            if available_orders:
                test_order_id = available_orders[0]['id']
                print(f"   Пытаемся назначить заказ #{test_order_id}...")
                
                # Назначаем заказ
                assign_response = requests.post(
                    f'http://127.0.0.1:8000/api/orders/{test_order_id}/assign-with-check/',
                    headers={
                        'Authorization': f'Token {token}',
                        'Content-Type': 'application/json'
                    },
                    json={'master_id': master_id}
                )
                
                print(f"   Статус назначения: {assign_response.status_code}")
                
                if assign_response.status_code == 200:
                    print("   ✅ Заказ успешно назначен мастеру!")
                    assign_data = assign_response.json()
                    print(f"   Ответ: {assign_data}")
                elif assign_response.status_code == 400:
                    error_data = assign_response.json()
                    print(f"   ⚠️ Ошибка валидации: {error_data.get('detail', 'Неизвестная ошибка')}")
                else:
                    print(f"   ❌ Ошибка: {assign_response.text}")
            else:
                print("   ⚠️ Нет доступных заказов для тестирования")
        else:
            print(f"   ❌ Не удалось получить список заказов: {response.text}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    
    # 3. Тест: получение деталей заказа
    print("\n3️⃣ Тестируем получение деталей заказа...")
    try:
        # Используем заказ с ID 2 для теста
        test_order_id = 2
        response = requests.get(
            f'http://127.0.0.1:8000/api/orders/{test_order_id}/detail/',
            headers={'Authorization': f'Token {token}'}
        )
        
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            order_data = response.json()
            print(f"   ✅ Детали заказа получены:")
            print(f"       - ID: {order_data.get('id')}")
            print(f"       - Клиент: {order_data.get('client_name')}")
            print(f"       - Статус: {order_data.get('status')}")
            print(f"       - Описание: {order_data.get('description')}")
        else:
            print(f"   ❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("\nПРОВЕРКИ ДЛЯ ФРОНТЕНДА:")
    print("1. ✅ Эндпоинт для заказов с дистанционностью: /api/distance/orders/available/")
    print("2. ✅ Эндпоинт для назначения заказа: /api/orders/{id}/assign-with-check/")
    print("3. ✅ Эндпоинт для деталей заказа: /api/orders/{id}/detail/")
    print("4. ✅ Токен в localStorage должен использоваться как 'authToken'")
    print("5. ✅ API запросы должны идти на http://127.0.0.1:8000")

if __name__ == "__main__":
    test_master_frontend_fixes()
