#!/usr/bin/env python3
"""
Скрипт для создания тестовых расписаний мастеров
Это необходимо для демонстрации системы планирования нагрузки
"""
import os
import sys
import django
from datetime import datetime, timedelta, time
from django.utils import timezone

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, MasterAvailability, Order


def create_master_schedules():
    """Создает тестовые расписания для мастеров на несколько дней"""
    print("🗓️ Создание тестовых расписаний мастеров...")
    
    masters = CustomUser.objects.filter(role='master')
    if not masters.exists():
        print("❌ Мастера не найдены!")
        return
    
    today = timezone.now().date()
    
    # Создаем расписания на 7 дней вперед
    for days_ahead in range(7):
        target_date = today + timedelta(days=days_ahead)
        day_name = target_date.strftime('%A')
        
        print(f"\n📅 {target_date} ({day_name})")
        
        for i, master in enumerate(masters):
            # Разные паттерны работы для разных мастеров
            if i % 4 == 0:  # Мастер 1: полный день
                create_full_day_schedule(master, target_date)
            elif i % 4 == 1:  # Мастер 2: утренняя смена
                create_morning_schedule(master, target_date)
            elif i % 4 == 2:  # Мастер 3: вечерняя смена
                create_evening_schedule(master, target_date)
            else:  # Мастер 4: выходной или частичная занятость
                if days_ahead % 3 != 0:  # работает не каждый день
                    create_partial_schedule(master, target_date)
    
    print(f"\n✅ Расписания созданы для {masters.count()} мастеров на 7 дней")


def create_full_day_schedule(master, date):
    """Создает расписание на полный рабочий день (9:00-18:00)"""
    schedules = [
        (time(9, 0), time(12, 0)),   # 9:00-12:00
        (time(13, 0), time(16, 0)),  # 13:00-16:00  
        (time(16, 30), time(18, 0))  # 16:30-18:00
    ]
    
    for start_time, end_time in schedules:
        MasterAvailability.objects.get_or_create(
            master=master,
            date=date,
            start_time=start_time,
            defaults={'end_time': end_time}
        )
    
    print(f"  ✅ {master.email}: Полный день (9:00-18:00)")


def create_morning_schedule(master, date):
    """Создает утреннее расписание (8:00-14:00)"""
    schedules = [
        (time(8, 0), time(11, 0)),   # 8:00-11:00
        (time(11, 30), time(14, 0))  # 11:30-14:00
    ]
    
    for start_time, end_time in schedules:
        MasterAvailability.objects.get_or_create(
            master=master,
            date=date,
            start_time=start_time,
            defaults={'end_time': end_time}
        )
    
    print(f"  ✅ {master.email}: Утренняя смена (8:00-14:00)")


def create_evening_schedule(master, date):
    """Создает вечернее расписание (14:00-20:00)"""
    schedules = [
        (time(14, 0), time(17, 0)),  # 14:00-17:00
        (time(17, 30), time(20, 0))  # 17:30-20:00
    ]
    
    for start_time, end_time in schedules:
        MasterAvailability.objects.get_or_create(
            master=master,
            date=date,
            start_time=start_time,
            defaults={'end_time': end_time}
        )
    
    print(f"  ✅ {master.email}: Вечерняя смена (14:00-20:00)")


def create_partial_schedule(master, date):
    """Создает частичное расписание (только утром)"""
    MasterAvailability.objects.get_or_create(
        master=master,
        date=date,
        start_time=time(10, 0),
        defaults={'end_time': time(13, 0)}
    )
    
    print(f"  ✅ {master.email}: Частичная занятость (10:00-13:00)")


def assign_some_orders_to_schedule():
    """Назначает несколько заказов на расписание для демонстрации занятости"""
    print("\n📋 Назначение заказов на расписание...")
    
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Получаем заказы без назначенной даты
    unscheduled_orders = Order.objects.filter(
        scheduled_date__isnull=True,
        status__in=['новый', 'назначен', 'в обработке']
    )[:4]
    
    # Назначаем заказы на сегодня и завтра
    for i, order in enumerate(unscheduled_orders):
        if i % 2 == 0:
            order.scheduled_date = today
        else:
            order.scheduled_date = tomorrow
        
        # Назначаем время
        if i % 4 == 0:
            order.scheduled_time = time(9, 0)
        elif i % 4 == 1:
            order.scheduled_time = time(11, 0)
        elif i % 4 == 2:
            order.scheduled_time = time(14, 0)
        else:
            order.scheduled_time = time(16, 0)
        
        order.save()
        
        date_str = order.scheduled_date.strftime('%Y-%m-%d')
        time_str = order.scheduled_time.strftime('%H:%M')
        print(f"  ✅ Заказ #{order.id} ({order.client_name}): {date_str} в {time_str}")


def show_capacity_summary():
    """Показывает сводку по пропускной способности"""
    print("\n📊 СВОДКА ПО ПРОПУСКНОЙ СПОСОБНОСТИ")
    print("=" * 50)
    
    today = timezone.now().date()
    
    for days_ahead in range(3):  # Показываем первые 3 дня
        target_date = today + timedelta(days=days_ahead)
        day_name = target_date.strftime('%A')
        
        # Подсчитываем слоты
        total_slots = MasterAvailability.objects.filter(date=target_date).count()
        occupied_slots = Order.objects.filter(
            scheduled_date=target_date,
            status__in=['назначен', 'выполняется', 'в работе']
        ).count()
        free_slots = total_slots - occupied_slots
        
        utilization = round((occupied_slots / max(1, total_slots)) * 100, 1)
        
        print(f"📅 {target_date} ({day_name}):")
        print(f"   Всего слотов: {total_slots}")
        print(f"   Занято: {occupied_slots}")
        print(f"   Свободно: {free_slots}")
        print(f"   Загрузка: {utilization}%")
        print()


if __name__ == "__main__":
    print("🚀 Настройка тестовых расписаний мастеров")
    print("=" * 50)
    
    # Удаляем старые расписания
    print("🗑️ Очистка старых расписаний...")
    MasterAvailability.objects.all().delete()
    
    # Создаем новые расписания
    create_master_schedules()
    
    # Назначаем заказы
    assign_some_orders_to_schedule()
    
    # Показываем сводку
    show_capacity_summary()
    
    print("✅ ГОТОВО! Теперь можно тестировать систему планирования.")
    print("\n🔧 Для проверки используйте:")
    print("curl -H 'Authorization: Token 327c2446fa3e569456c220b7b7cbdb9bcc4ff620' \\")
    print("     http://127.0.0.1:8000/api/capacity/analysis/")
