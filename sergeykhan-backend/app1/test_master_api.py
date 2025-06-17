#!/usr/bin/env python3
"""
Тест API заказов мастера
"""
import requests

# Данные авторизованного мастера
BASE_URL = "http://localhost:8000"
TOKEN = "ee57c0206252baeceafcef56d7e32e78ec6e7d3f"
USER_ID = 3

def test_master_orders():
    """Тестирует получение доступных заказов для мастера"""
    headers = {
        'Authorization': f'Token {TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Тестируем разные эндпоинты заказов
    endpoints_to_test = [
        "/api/orders/master/available/",
        "/api/orders/new/",
        "/api/orders/all/",
        f"/api/distance/master/{USER_ID}/",
        "/api/distance/orders/available/",
    ]
    
    for endpoint in endpoints_to_test:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n🔍 Тестируем: {endpoint}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"✅ Получено {len(data)} записей")
                    if data:
                        print(f"Пример записи: {list(data[0].keys()) if data[0] else 'Пустая запись'}")
                elif isinstance(data, dict):
                    print(f"✅ Получен объект с ключами: {list(data.keys())}")
                else:
                    print(f"✅ Получен ответ: {type(data)}")
            else:
                print(f"❌ Ошибка: {response.text}")
                
        except Exception as e:
            print(f"❌ Исключение: {e}")

def test_assign_order():
    """Тестирует назначение заказа мастеру"""
    headers = {
        'Authorization': f'Token {TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Сначала получаем доступные заказы
    try:
        response = requests.get(f"{BASE_URL}/api/orders/new/", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            if orders:
                order_id = orders[0]['id']
                print(f"\n🎯 Тестируем назначение заказа #{order_id}")
                
                # Тестируем назначение заказа
                assign_url = f"{BASE_URL}/api/orders/{order_id}/assign-with-check/"
                assign_response = requests.post(assign_url, headers=headers, json={"master_id": USER_ID})
                
                print(f"Статус: {assign_response.status_code}")
                print(f"Ответ: {assign_response.text}")
            else:
                print("\n⚠️ Нет доступных заказов для назначения")
        else:
            print(f"\n❌ Не удалось получить заказы: {response.text}")
    except Exception as e:
        print(f"❌ Ошибка при тестировании назначения: {e}")

if __name__ == "__main__":
    print("=== Тестирование API мастера ===")
    print(f"Мастер: ID {USER_ID}, Token: {TOKEN[:20]}...")
    
    test_master_orders()
    test_assign_order()
