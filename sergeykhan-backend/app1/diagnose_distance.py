#!/usr/bin/env python3
"""
Скрипт для диагностики системы дистанционки
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

def diagnose_distance_system():
    """Диагностика системы дистанционки"""
    print("🔍 Диагностика системы дистанционки...")
    print("=" * 50)
    
    # 1. Проверяем настройки дистанционки
    print("\n1️⃣ Настройки дистанционки:")
    settings = DistanceSettingsModel.get_settings()
    print(f"   - Средний чек для стандартной дистанционки: {settings.average_check_threshold} руб.")
    print(f"   - Период видимости стандартной дистанционки: {settings.visible_period_standard} часов")
    print(f"   - Сумма заказов в сутки для суточной дистанционки: {settings.daily_order_sum_threshold} руб.")
    print(f"   - Чистый вал за 10 дней для суточной дистанционки: {settings.net_turnover_threshold} руб.")
    print(f"   - Период видимости суточной дистанционки: {settings.visible_period_daily} часов")
    
    # 2. Проверяем всех мастеров
    print("\n2️⃣ Статус дистанционки мастеров:")
    masters = CustomUser.objects.filter(role='master')
    print(f"   Всего мастеров: {masters.count()}")
    
    for master in masters:
        print(f"\n   📋 Мастер: {master.email} (ID: {master.id})")
        print(f"      Текущий уровень дистанционки: {master.dist}")
        print(f"      Ручная установка: {master.distance_manual_override}")
        
        # Рассчитываем статистику
        avg_check = calculate_average_check(master.id)
        daily_revenue = calculate_daily_revenue(master.id)
        net_turnover = calculate_net_turnover(master.id)
        calculated_level = check_distance_level(master.id)
        
        print(f"      📊 Статистика:")
        print(f"         - Средний чек: {avg_check} руб.")
        print(f"         - Доход за 24 часа: {daily_revenue} руб.")
        print(f"         - Чистый вал за 10 дней: {net_turnover} руб.")
        print(f"         - Рассчитанный уровень дистанционки: {calculated_level}")
        
        # Проверяем соответствие критериям
        meets_standard = avg_check >= settings.average_check_threshold
        meets_daily_revenue = daily_revenue >= settings.daily_order_sum_threshold
        meets_daily_turnover = net_turnover >= settings.net_turnover_threshold
        
        print(f"      ✅ Критерии:")
        print(f"         - Стандартная дистанционка: {'✅' if meets_standard else '❌'}")
        print(f"         - Суточная (по доходу): {'✅' if meets_daily_revenue else '❌'}")
        print(f"         - Суточная (по валу): {'✅' if meets_daily_turnover else '❌'}")
        
        # Получаем видимые заказы
        visible_orders = get_visible_orders_for_master(master.id)
        print(f"      📝 Видимые заказы: {visible_orders.count()}")
        
        # Показываем заказы мастера
        master_orders = Order.objects.filter(assigned_master=master)
        print(f"      📦 Заказы мастера: {master_orders.count()}")
        print(f"         - Завершённые: {master_orders.filter(status='завершен').count()}")
        print(f"         - В работе: {master_orders.exclude(status__in=['завершен', 'отклонен']).count()}")
        
        if master_orders.exists():
            print(f"      📅 Последние 3 заказа:")
            for order in master_orders.order_by('-created_at')[:3]:
                print(f"         - ID:{order.id}, Статус:{order.status}, Стоимость:{order.final_cost or order.estimated_cost}, Дата:{order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else 'N/A'}")
    
    # 3. Проверяем доступные заказы
    print("\n3️⃣ Доступные заказы:")
    available_orders = Order.objects.filter(
        status__in=['новый', 'в обработке'],
        assigned_master__isnull=True
    ).order_by('-created_at')
    
    print(f"   Всего доступных заказов: {available_orders.count()}")
    
    for order in available_orders[:5]:  # показываем первые 5
        print(f"   📋 Заказ ID:{order.id}")
        print(f"      Клиент: {order.client_name}")
        print(f"      Статус: {order.status}")
        print(f"      Создан: {order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else 'N/A'}")
        print(f"      Стоимость: {order.estimated_cost} руб.")
        
        # Проверяем кто может видеть этот заказ
        can_see_masters = []
        for master in masters:
            visible_orders = get_visible_orders_for_master(master.id)
            if order in visible_orders:
                can_see_masters.append(f"{master.email} (dist:{master.dist})")
        
        print(f"      👀 Видят мастера: {', '.join(can_see_masters) if can_see_masters else 'Никто'}")
    
    # 4. Рекомендации
    print("\n4️⃣ Рекомендации:")
    masters_with_issues = []
    
    for master in masters:
        calculated_level = check_distance_level(master.id)
        if master.dist != calculated_level and not master.distance_manual_override:
            masters_with_issues.append(f"{master.email}: текущий {master.dist}, должен быть {calculated_level}")
    
    if masters_with_issues:
        print("   ⚠️  Найдены проблемы с уровнями дистанционки:")
        for issue in masters_with_issues:
            print(f"      - {issue}")
        print("   💡 Рекомендуется обновить статусы дистанционки через админ-панель")
    else:
        print("   ✅ Все уровни дистанционки корректны")
    
    # Проверяем, есть ли мастера с суточной дистанционкой
    daily_masters = masters.filter(dist=2)
    if daily_masters.exists():
        print(f"\n   📈 Мастера с суточной дистанционкой ({daily_masters.count()}):")
        for master in daily_masters:
            visible_orders = get_visible_orders_for_master(master.id)
            print(f"      - {master.email}: видит {visible_orders.count()} заказов")
    else:
        print("\n   📉 Нет мастеров с суточной дистанционкой")

def update_all_masters():
    """Обновить статусы дистанционки для всех мастеров"""
    print("\n🔄 Обновление статусов дистанционки...")
    masters = CustomUser.objects.filter(role='master')
    updated_count = 0
    
    for master in masters:
        old_level = master.dist
        if update_master_distance_status(master.id):
            master.refresh_from_db()
            print(f"   ✅ {master.email}: {old_level} → {master.dist}")
            updated_count += 1
        else:
            print(f"   ➡️  {master.email}: {master.dist} (без изменений)")
    
    print(f"\n🎯 Обновлено: {updated_count} из {masters.count()} мастеров")

if __name__ == "__main__":
    try:
        diagnose_distance_system()
        
        # Спрашиваем, нужно ли обновить статусы
        print("\n" + "="*50)
        response = input("Обновить статусы дистанционки для всех мастеров? (y/N): ")
        if response.lower() in ['y', 'yes', 'да']:
            update_all_masters()
            print("\n🔄 Повторная диагностика после обновления:")
            diagnose_distance_system()
        
        print("\n✅ Диагностика завершена!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
