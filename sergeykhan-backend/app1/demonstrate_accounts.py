#!/usr/bin/env python3
"""
Скрипт для демонстрации работы с системой с разных аккаунтов
Показывает как выглядит система глазами мастера, оператора, куратора и супер-админа
"""
import requests
import json
from datetime import datetime

# Базовый URL API
BASE_URL = "http://127.0.0.1:8000"

# Токены пользователей (из предыдущего скрипта)
TOKENS = {
    'super_admin': '327c2446fa3e569456c220b7b7cbdb9bcc4ff620',
    'master1': 'ba187bce15be8dd8db2ebed3aa98f950bdd23003',
    'master2': '91fb1989349a1ff8995cc6f4232c45bd06bcea8d',
    'master3': 'ccaaf92df6f43b9379c52c1cefc1fb2acaa0dc7d',
    'master4': '3eb3ec727439f6cb3700d9c89192e9f6c4fbd008',
    'operator1': '8b5ae72b7fa6c69db664dd383f1ef7dad8540b08',
    'operator2': '7036ecdb28db85503159ff0c09be02483d0b998a',
    'curator1': '8b709c0c68b90ff206c2e4ce2321a9d7f4749df8'
}

def make_request(endpoint, token, method='GET', data=None):
    """Выполняет запрос к API с указанным токеном"""
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': f'Status {response.status_code}',
                'message': response.text[:200] if response.text else 'No message'
            }
    except Exception as e:
        return {'error': str(e)}

def print_section(title):
    """Печатает заголовок секции"""
    print("\n" + "="*80)
    print(f"🎯 {title}")
    print("="*80)

def print_user_info(token, role):
    """Получает и выводит информацию о пользователе"""
    user_info = make_request('/api/user/', token)
    if 'error' not in user_info:
        print(f"👤 Вход как: {user_info.get('email')} ({role})")
        print(f"   ID: {user_info.get('id')}, Роль: {user_info.get('role')}")
    else:
        print(f"❌ Ошибка получения данных пользователя: {user_info}")

def demonstrate_super_admin():
    """Демонстрация работы супер-админа"""
    print_section("СУПЕР-АДМИН - Полный обзор системы")
    token = TOKENS['super_admin']
    print_user_info(token, "Супер-администратор")
    
    # Получение всех заказов
    print("\n📋 ВСЕ ЗАКАЗЫ В СИСТЕМЕ:")
    orders = make_request('/api/orders/all/', token)
    if 'error' not in orders:
        for order in orders:
            status = order.get('status', 'неизвестно')
            master = order.get('assigned_master')
            master_info = f" → Мастер: {master}" if master else " (не назначен)"
            print(f"  • Заказ #{order.get('id')}: {order.get('client_name')} - {status}{master_info}")
    else:
        print(f"  ❌ Ошибка: {orders}")
    
    # Получение информации о мастерах
    print("\n👷‍♂️ ИНФОРМАЦИЯ О МАСТЕРАХ:")
    masters = make_request('/users/masters/', token)
    if 'error' not in masters:
        for master in masters:
            print(f"  • {master.get('first_name', '')} {master.get('last_name', '')} ({master.get('email')})")
    else:
        print(f"  ❌ Ошибка: {masters}")
    
    # Нагрузка мастеров
    print("\n📊 НАГРУЗКА МАСТЕРОВ:")
    workload = make_request('/api/masters/workload/all/', token)
    if 'error' not in workload:
        for master_data in workload:
            email = master_data.get('master_email', 'Unknown')
            orders_today = master_data.get('total_orders_today', 0)
            next_slot = master_data.get('next_available_slot')
            slot_info = f" (следующий слот: {next_slot})" if next_slot else " (нет слотов)"
            print(f"  • {email}: {orders_today} заказов сегодня{slot_info}")
    else:
        print(f"  ❌ Ошибка: {workload}")

def demonstrate_master(master_key):
    """Демонстрация работы мастера"""
    print_section(f"МАСТЕР - Работа с заказами ({master_key})")
    token = TOKENS[master_key]
    print_user_info(token, "Мастер")
    
    # Получение доступных заказов для мастера
    print("\n📋 ДОСТУПНЫЕ ЗАКАЗЫ ДЛЯ ВЗЯТИЯ:")
    available_orders = make_request('/api/orders/master/available/', token)
    if 'error' not in available_orders:
        if available_orders:
            for order in available_orders[:3]:  # Показываем первые 3
                print(f"  • Заказ #{order.get('id')}: {order.get('description')}")
                print(f"    Адрес: {order.get('public_address', 'не указан')}")
                print(f"    Статус: {order.get('status')}")
        else:
            print("  📭 Нет доступных заказов")
    else:
        print(f"  ❌ Ошибка: {available_orders}")
    
    # Мои заказы
    print("\n🔧 МОИ ТЕКУЩИЕ ЗАКАЗЫ:")
    user_info = make_request('/api/user/', token)
    if 'error' not in user_info:
        master_id = user_info.get('id')
        my_orders = make_request(f'/orders/master/{master_id}/', token)
        if 'error' not in my_orders:
            if my_orders:
                for order in my_orders:
                    print(f"  • Заказ #{order.get('id')}: {order.get('client_name')}")
                    print(f"    Описание: {order.get('description')}")
                    print(f"    Статус: {order.get('status')}")
                    print(f"    Телефон: {order.get('client_phone', 'скрыт')}")
            else:
                print("  📭 У вас нет назначенных заказов")
        else:
            print(f"  ❌ Ошибка: {my_orders}")

def demonstrate_operator(operator_key):
    """Демонстрация работы оператора"""
    print_section(f"ОПЕРАТОР - Обработка заказов ({operator_key})")
    token = TOKENS[operator_key]
    print_user_info(token, "Оператор")
    
    # Новые заказы для обработки
    print("\n📞 НОВЫЕ ЗАКАЗЫ ДЛЯ ОБРАБОТКИ:")
    new_orders = make_request('/api/orders/new/', token)
    if 'error' not in new_orders:
        if new_orders:
            for order in new_orders:
                print(f"  • Заказ #{order.get('id')}: {order.get('client_name')}")
                print(f"    Телефон: {order.get('client_phone')}")
                print(f"    Описание: {order.get('description')}")
                print(f"    Создан: {order.get('created_at', '')[:19]}")
        else:
            print("  ✅ Все заказы обработаны")
    else:
        print(f"  ❌ Ошибка: {new_orders}")
    
    # Заказы в обработке
    print("\n⏳ ЗАКАЗЫ В ОБРАБОТКЕ:")
    processing_orders = make_request('/get_processing_orders', token)
    if 'error' not in processing_orders:
        if processing_orders:
            for order in processing_orders:
                print(f"  • Заказ #{order.get('id')}: {order.get('client_name')} - {order.get('status')}")
        else:
            print("  📭 Нет заказов в обработке")
    else:
        print(f"  ❌ Ошибка: {processing_orders}")

def demonstrate_curator():
    """Демонстрация работы куратора"""
    print_section("КУРАТОР - Управление мастерами и контроль качества")
    token = TOKENS['curator1']
    print_user_info(token, "Куратор")
    
    # Все активные заказы
    print("\n📋 АКТИВНЫЕ ЗАКАЗЫ:")
    active_orders = make_request('/api/orders/active/', token)
    if 'error' not in active_orders:
        if active_orders:
            for order in active_orders:
                master = order.get('assigned_master')
                master_info = f" (Мастер: {master})" if master else " (не назначен)"
                print(f"  • Заказ #{order.get('id')}: {order.get('client_name')} - {order.get('status')}{master_info}")
        else:
            print("  📭 Нет активных заказов")
    else:
        print(f"  ❌ Ошибка: {active_orders}")
    
    # Статистика мастеров
    print("\n👷‍♂️ МАСТЕРА ПОД УПРАВЛЕНИЕМ:")
    masters = make_request('/users/masters/', token)
    if 'error' not in masters:
        for master in masters:
            print(f"  • {master.get('first_name', '')} {master.get('last_name', '')} ({master.get('email')})")
            print(f"    Роль: {master.get('role')}, Дистанционка: {master.get('dist', 0)}")
    else:
        print(f"  ❌ Ошибка: {masters}")

def create_test_order():
    """Создание тестового заказа от имени оператора"""
    print_section("СОЗДАНИЕ НОВОГО ЗАКАЗА")
    token = TOKENS['operator1']
    
    order_data = {
        "client_name": "Тест Клиентов",
        "client_phone": "+7 (900) 111-22-33", 
        "description": "Ремонт телевизора Samsung - не включается",
        "street": "ул. Тестовая",
        "house_number": "42",
        "apartment": "15",
        "service_type": "Ремонт электроники",
        "equipment_type": "Телевизор"
    }
    
    print(f"📝 Создание заказа от оператора:")
    print(f"   Клиент: {order_data['client_name']}")
    print(f"   Телефон: {order_data['client_phone']}")
    print(f"   Описание: {order_data['description']}")
    
    result = make_request('/orders/create/', token, 'POST', order_data)
    if 'error' not in result:
        print(f"✅ Заказ успешно создан! ID: {result.get('id')}")
        print(f"   Статус: {result.get('status')}")
        print(f"   Адрес: {result.get('full_address')}")
    else:
        print(f"❌ Ошибка создания заказа: {result}")

def demonstrate_order_assignment():
    """Демонстрация назначения заказа мастеру"""
    print_section("НАЗНАЧЕНИЕ ЗАКАЗА МАСТЕРУ")
    token = TOKENS['super_admin']
    
    # Получаем список новых заказов
    new_orders = make_request('/api/orders/new/', token)
    if 'error' not in new_orders and new_orders:
        order_id = new_orders[0]['id']
        print(f"📋 Назначаем заказ #{order_id} мастеру Сергею Сидорову")
        
        # Получаем ID мастера
        masters = make_request('/users/masters/', token)
        sergey_master = None
        for master in masters:
            if master.get('email') == 'master3@test.com':
                sergey_master = master
                break
        
        if sergey_master:
            # Назначаем заказ
            assign_data = {"master_id": sergey_master['id']}
            result = make_request(f'/assign/{order_id}/', token, 'POST', assign_data)
            if 'error' not in result:
                print(f"✅ Заказ #{order_id} назначен мастеру {sergey_master['first_name']} {sergey_master['last_name']}")
            else:
                print(f"❌ Ошибка назначения: {result}")
        else:
            print("❌ Мастер не найден")
    else:
        print("📭 Нет новых заказов для назначения")

def main():
    """Основная функция демонстрации"""
    print("🚀" + "="*79)
    print("🎯 ДЕМОНСТРАЦИЯ РАБОТЫ СИСТЕМЫ С РАЗНЫХ АККАУНТОВ")
    print("🚀" + "="*79)
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Создание нового заказа
    create_test_order()
    
    # 2. Работа супер-админа
    demonstrate_super_admin()
    
    # 3. Работа операторов
    demonstrate_operator('operator1')
    demonstrate_operator('operator2')
    
    # 4. Работа мастеров
    demonstrate_master('master1')  # У него есть назначенный заказ
    demonstrate_master('master3')  # У него нет заказов
    
    # 5. Работа куратора
    demonstrate_curator()
    
    # 6. Назначение заказа
    demonstrate_order_assignment()
    
    # 7. Повторный обзор мастера после назначения
    print_section("МАСТЕР ПОСЛЕ НАЗНАЧЕНИЯ ЗАКАЗА")
    demonstrate_master('master3')
    
    print("\n" + "🎉"*80)
    print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
    print("🎉"*80)

if __name__ == "__main__":
    main()
