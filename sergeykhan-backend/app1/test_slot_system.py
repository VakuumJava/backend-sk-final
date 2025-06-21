#!/usr/bin/env python
"""
Тестирование новой системы слотов заказов
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
sys.path.append('/Users/bekzhan/Documents/projects/sk/SergeyKhanWeb/sergeykhan-backend/app1')
django.setup()

from api1.models import CustomUser, Order, OrderSlot, MasterDailySchedule
from datetime import date, datetime, time, timedelta
import json


def test_slot_system():
    """Тестирование системы слотов"""
    print("🔧 Тестирование системы слотов заказов")
    print("=" * 50)
    
    # Получаем тестового мастера
    try:
        master = CustomUser.objects.get(email='master@test.com')
        print(f"✅ Мастер найден: {master.email} (ID: {master.id})")
    except CustomUser.DoesNotExist:
        print("❌ Тестовый мастер не найден")
        return
    
    # Получаем или создаем расписание на сегодня
    today = date.today()
    daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, today)
    print(f"✅ Расписание дня создано: {daily_schedule}")
    print(f"   📅 Дата: {today}")
    print(f"   ⏰ Рабочие часы: {daily_schedule.work_start_time} - {daily_schedule.work_end_time}")
    print(f"   📊 Максимум слотов: {daily_schedule.max_slots}")
    
    # Показываем все слоты дня
    print(f"\n📋 Все слоты дня:")
    slots = daily_schedule.get_all_slots()
    for slot in slots:
        status_icon = "🔴" if slot['is_occupied'] else "🟢"
        order_info = f" (Заказ #{slot['order'].id})" if slot['order'] else " (свободен)"
        print(f"   {status_icon} Слот {slot['slot_number']}: {slot['time']} - {slot['end_time']}{order_info}")
    
    # Показываем доступные слоты
    available_slots = OrderSlot.get_available_slots_for_master(master, today)
    print(f"\n🆓 Доступные слоты: {available_slots}")
    print(f"🔢 Свободных слотов: {len(available_slots)}")
    print(f"🔢 Занятых слотов: {daily_schedule.get_occupied_slots_count()}")
    
    # Создаем тестовый заказ
    print(f"\n🔧 Создание тестового заказа...")
    test_order = Order.objects.create(
        client_name='Тест Слот Клиент',
        client_phone='+996700123456',
        description='Тестовый заказ для проверки системы слотов',
        address='Тестовый адрес',
        is_test=True
    )
    print(f"✅ Тестовый заказ создан: ID = {test_order.id}")
    
    # Назначаем заказ на первый доступный слот
    if available_slots:
        slot_number = available_slots[0]
        print(f"\n🎯 Назначаем заказ #{test_order.id} на слот {slot_number}...")
        
        # Вычисляем время слота
        start_datetime = datetime.combine(today, daily_schedule.work_start_time)
        slot_datetime = start_datetime + (daily_schedule.slot_duration * (slot_number - 1))
        slot_time = slot_datetime.time()
        
        try:
            order_slot = OrderSlot.create_slot_for_order(
                order=test_order,
                master=master,
                slot_date=today,
                slot_number=slot_number,
                slot_time=slot_time
            )
            print(f"✅ Слот создан успешно!")
            print(f"   📍 Слот: {order_slot.get_slot_display_name()}")
            print(f"   ⏰ Время: {order_slot.slot_time} - {order_slot.get_end_time()}")
            print(f"   📋 Статус: {order_slot.status}")
            
            # Проверяем обновленное состояние
            print(f"\n📊 Обновленное состояние:")
            updated_slots = daily_schedule.get_all_slots()
            for slot in updated_slots:
                if slot['slot_number'] == slot_number:
                    print(f"   🔴 Слот {slot['slot_number']}: {slot['time']} - {slot['end_time']} (Заказ #{slot['order'].id})")
                    break
            
            # Показываем информацию о заказе
            print(f"\n📄 Информация о заказе:")
            print(f"   🆔 ID: {test_order.id}")
            print(f"   👤 Клиент: {test_order.client_name}")
            print(f"   📞 Телефон: {test_order.client_phone}")
            print(f"   📍 Адрес: {test_order.address}")
            print(f"   📋 Статус: {test_order.status}")
            print(f"   👨‍🔧 Мастер: {test_order.assigned_master.email if test_order.assigned_master else 'Не назначен'}")
            print(f"   📅 Запланированная дата: {test_order.scheduled_date}")
            print(f"   ⏰ Запланированное время: {test_order.scheduled_time}")
            
            if hasattr(test_order, 'slot'):
                print(f"   🎯 Слот: {test_order.slot.get_slot_display_name()}")
            
        except Exception as e:
            print(f"❌ Ошибка при создании слота: {e}")
            
    else:
        print("⚠️ Нет доступных слотов для назначения")
    
    # Финальная статистика
    print(f"\n📈 Финальная статистика:")
    final_available = OrderSlot.get_available_slots_for_master(master, today)
    print(f"   🆓 Доступных слотов: {len(final_available)}")
    print(f"   🔴 Занятых слотов: {daily_schedule.get_occupied_slots_count()}")
    print(f"   📊 Загрузка: {daily_schedule.get_occupied_slots_count()}/{daily_schedule.max_slots}")
    
    print(f"\n✅ Тестирование завершено!")


def test_api_endpoints():
    """Тестирование API endpoints через curl команды"""
    print("\n🌐 Команды для тестирования API:")
    print("=" * 50)
    
    # Получаем токен мастера
    print("1. Логин мастера:")
    print('curl -X POST http://127.0.0.1:8000/login/ \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"email": "master@test.com", "password": "test123456"}\'')
    
    print("\n2. Получить расписание мастера на сегодня:")
    print('curl -X GET http://127.0.0.1:8000/api/slots/master/1/schedule/ \\')
    print('  -H "Authorization: Token YOUR_TOKEN_HERE"')
    
    print("\n3. Получить доступные слоты мастера:")
    print('curl -X GET http://127.0.0.1:8000/api/slots/master/1/available/ \\')
    print('  -H "Authorization: Token YOUR_TOKEN_HERE"')
    
    print("\n4. Назначить заказ на слот:")
    print('curl -X POST http://127.0.0.1:8000/api/slots/assign/ \\')
    print('  -H "Authorization: Token YOUR_TOKEN_HERE" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"order_id": ORDER_ID, "master_id": 1, "slot_date": "2025-06-18", "slot_number": 1}\'')
    
    print("\n5. Получить информацию о слоте заказа:")
    print('curl -X GET http://127.0.0.1:8000/api/slots/order/ORDER_ID/ \\')
    print('  -H "Authorization: Token YOUR_TOKEN_HERE"')
    
    print("\n6. Сводка по всем мастерам:")
    print('curl -X GET http://127.0.0.1:8000/api/slots/masters/summary/ \\')
    print('  -H "Authorization: Token YOUR_TOKEN_HERE"')


if __name__ == '__main__':
    test_slot_system()
    test_api_endpoints()
