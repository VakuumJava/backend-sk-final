#!/usr/bin/env python3
"""
Скрипт для решения проблемы дистанционки конкретного мастера
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order, DistanceSettingsModel
from api1.distancionka import (
    calculate_average_check,
    calculate_daily_revenue,
    calculate_net_turnover,
    check_distance_level,
    update_master_distance_status,
    get_visible_orders_for_master
)
from django.utils import timezone

def fix_master_distance(master_email):
    """Исправить проблему дистанционки для конкретного мастера"""
    print(f"🔧 Исправление дистанционки для мастера: {master_email}")
    print("=" * 60)
    
    try:
        master = CustomUser.objects.get(email=master_email, role='master')
    except CustomUser.DoesNotExist:
        print(f"❌ Мастер {master_email} не найден!")
        return False
    
    print(f"📋 Мастер найден: {master.email} (ID: {master.id})")
    print(f"   Текущий уровень дистанционки: {master.dist}")
    print(f"   Ручная установка: {master.distance_manual_override}")
    
    # Показываем текущую статистику
    avg_check = calculate_average_check(master.id)
    daily_revenue = calculate_daily_revenue(master.id)
    net_turnover = calculate_net_turnover(master.id)
    calculated_level = check_distance_level(master.id)
    
    print(f"\n📊 Текущая статистика:")
    print(f"   - Средний чек: {avg_check} руб.")
    print(f"   - Доход за 24 часа: {daily_revenue} руб.")
    print(f"   - Чистый вал за 10 дней: {net_turnover} руб.")
    print(f"   - Рассчитанный уровень: {calculated_level}")
    
    # Показываем видимые заказы ДО исправления
    visible_orders_before = get_visible_orders_for_master(master.id)
    print(f"\n👀 Видимые заказы ДО исправления: {visible_orders_before.count()}")
    for order in visible_orders_before:
        print(f"   - Заказ #{order.id}: {order.client_name}, статус: {order.status}")
    
    # Вариант 1: Сброс ручной установки и пересчет
    print(f"\n🔄 Вариант 1: Сброс к автоматическому расчету")
    print("   Это сбросит ручную установку и пересчитает дистанционку автоматически")
    
    # Вариант 2: Принудительная установка суточной дистанционки
    print(f"\n🔄 Вариант 2: Установка суточной дистанционки вручную")
    print("   Это установит суточную дистанционку (уровень 2) независимо от показателей")
    
    # Спрашиваем пользователя
    print("\n" + "="*60)
    choice = input("Выберите вариант (1 - авто, 2 - ручная суточная, 0 - отмена): ")
    
    if choice == "1":
        # Сбрасываем ручную установку
        print("\n🔄 Сбрасываем ручную установку...")
        master.distance_manual_override = False
        master.save()
        
        # Пересчитываем автоматически
        old_level = master.dist
        update_master_distance_status(master.id)
        master.refresh_from_db()
        
        print(f"✅ Готово! Уровень дистанционки: {old_level} → {master.dist}")
        print(f"   Ручная установка: False")
        
    elif choice == "2":
        # Устанавливаем суточную дистанционку вручную
        print("\n🔄 Устанавливаем суточную дистанционку вручную...")
        old_level = master.dist
        master.dist = 2
        master.distance_manual_override = True
        master.save()
        
        print(f"✅ Готово! Уровень дистанционки: {old_level} → {master.dist}")
        print(f"   Ручная установка: True")
        
    elif choice == "0":
        print("❌ Операция отменена")
        return False
    else:
        print("❌ Неверный выбор")
        return False
    
    # Показываем результат
    master.refresh_from_db()
    visible_orders_after = get_visible_orders_for_master(master.id)
    
    print(f"\n📊 Результат:")
    print(f"   - Уровень дистанционки: {master.dist}")
    print(f"   - Ручная установка: {master.distance_manual_override}")
    print(f"   - Видимые заказы: {visible_orders_after.count()}")
    
    if visible_orders_after.count() > 0:
        print(f"\n👀 Заказы ПОСЛЕ исправления:")
        for order in visible_orders_after:
            print(f"   - Заказ #{order.id}: {order.client_name}, статус: {order.status}")
    
    # Проверяем API эндпоинт
    print(f"\n🌐 Проверка API эндпоинтов:")
    print(f"   Для тестирования выполните:")
    print(f"   curl -H \"Authorization: Token [ваш-токен]\" http://localhost:8000/api/distance/master/orders/")
    print(f"   curl -H \"Authorization: Token [ваш-токен]\" http://localhost:8000/api/distance/orders/available/")
    
    return True

def create_test_order():
    """Создать тестовый заказ для проверки"""
    print("\n🆕 Создание тестового заказа...")
    
    test_order = Order.objects.create(
        client_name='Тестовый клиент',
        client_phone='+77000000999',
        description='Тестовый заказ для проверки дистанционки',
        status='новый',
        street='Тестовая улица',
        house_number='1',
        estimated_cost=Decimal('5000.00'),
        created_at=timezone.now()
    )
    
    print(f"✅ Создан тестовый заказ #{test_order.id}")
    return test_order

if __name__ == "__main__":
    print("🔧 Инструмент для исправления проблем дистанционки")
    print("=" * 60)
    
    # Показываем доступных мастеров
    masters = CustomUser.objects.filter(role='master')
    print(f"📋 Доступные мастера ({masters.count()}):")
    for i, master in enumerate(masters, 1):
        print(f"   {i}. {master.email} (dist: {master.dist}, ручная: {master.distance_manual_override})")
    
    # Спрашиваем email мастера
    print("\n" + "="*60)
    master_email = input("Введите email мастера для исправления (или 'exit' для выхода): ").strip()
    
    if master_email.lower() == 'exit':
        print("👋 До свидания!")
        sys.exit(0)
    
    # Исправляем проблему
    success = fix_master_distance(master_email)
    
    if success:
        # Предлагаем создать тестовый заказ
        print("\n" + "="*60)
        create_test = input("Создать тестовый заказ для проверки? (y/N): ").lower()
        if create_test in ['y', 'yes', 'да']:
            create_test_order()
    
    print("\n✅ Готово!")
