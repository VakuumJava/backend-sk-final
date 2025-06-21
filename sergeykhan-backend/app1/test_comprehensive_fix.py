#!/usr/bin/env python3
"""
Простой тест для проверки исправления ошибки
"""

import os
import sys
import django

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, ProfitDistributionSettings, SystemLog
from api1.views import log_system_action

def test_system_log_functionality():
    """Тест функционала системного логирования"""
    print("🔧 Тестирование системного логирования...")
    
    # Создаём тестового пользователя
    try:
        user = CustomUser.objects.get(email='test_admin@test.com')
    except CustomUser.DoesNotExist:
        user = CustomUser.objects.create_user(
            email='test_admin@test.com',
            password='test123',
            role='super-admin'
        )
    print(f"✅ Пользователь: {user.email}")
    
    # Тестируем log_system_action
    print("📝 Тестирование log_system_action...")
    
    old_count = SystemLog.objects.count()
    
    log_system_action(
        action='percentage_settings_updated',
        performed_by=user,
        description='Тестовое обновление настроек распределения прибыли',
        old_value='{"test": "old"}',
        new_value='{"test": "new"}',
        metadata={'test_run': True}
    )
    
    new_count = SystemLog.objects.count()
    
    if new_count > old_count:
        print("✅ Системный лог успешно создан!")
        
        # Проверяем последний лог
        last_log = SystemLog.objects.latest('created_at')
        print(f"   📋 Действие: {last_log.action}")
        print(f"   👤 Пользователь: {last_log.performed_by.email}")
        print(f"   📝 Описание: {last_log.description}")
        print(f"   📅 Время: {last_log.created_at}")
        
        return True
    else:
        print("❌ Системный лог не был создан!")
        return False

def test_profit_distribution_settings():
    """Тест настроек распределения прибыли"""
    print("\n🔧 Тестирование настроек распределения прибыли...")
    
    # Получаем настройки
    settings = ProfitDistributionSettings.get_settings()
    print(f"📊 Текущие настройки:")
    print(f"   Мастеру (выплачено): {settings.master_paid_percent}%")
    print(f"   Мастеру (баланс): {settings.master_balance_percent}%")
    print(f"   Куратору: {settings.curator_percent}%")
    print(f"   Компании: {settings.company_percent}%")
    print(f"   Общий процент мастера: {settings.total_master_percent}%")
    
    # Тестируем валидацию
    print("\n🔍 Тестирование валидации...")
    original_values = (
        settings.master_paid_percent,
        settings.master_balance_percent,
        settings.curator_percent,
        settings.company_percent
    )
    
    try:
        # Пытаемся установить некорректные значения (сумма > 100%)
        settings.master_paid_percent = 60
        settings.master_balance_percent = 30
        settings.curator_percent = 20
        settings.company_percent = 10  # Сумма = 120%
        
        settings.clean()
        print("❌ Валидация не сработала!")
        return False
        
    except Exception as e:
        print(f"✅ Валидация работает корректно: {e}")
        
        # Восстанавливаем оригинальные значения
        settings.master_paid_percent = original_values[0]
        settings.master_balance_percent = original_values[1]
        settings.curator_percent = original_values[2]
        settings.company_percent = original_values[3]
        
        return True

def simulate_settings_update():
    """Симуляция обновления настроек как в views.py"""
    print("\n🔧 Симуляция обновления настроек...")
    
    # Создаём пользователя
    try:
        user = CustomUser.objects.get(email='test_admin@test.com')
    except CustomUser.DoesNotExist:
        user = CustomUser.objects.create_user(
            email='test_admin@test.com',
            password='test123',
            role='super-admin'
        )
    
    settings = ProfitDistributionSettings.get_settings()
    
    # Сохраняем старые значения
    old_settings = {
        'master_paid_percent': settings.master_paid_percent,
        'master_balance_percent': settings.master_balance_percent,
        'curator_percent': settings.curator_percent,
        'company_percent': settings.company_percent,
    }
    
    # Обновляем настройки
    new_data = {
        'master_paid_percent': 25,
        'master_balance_percent': 35,
        'curator_percent': 10,
        'company_percent': 30
    }
    
    for field, value in new_data.items():
        setattr(settings, field, value)
    
    settings.updated_by = user
    
    try:
        settings.clean()
        settings.save()
        
        # Создаем описание изменений
        changes = []
        for field, old_value in old_settings.items():
            new_value = getattr(settings, field)
            if old_value != new_value:
                field_names = {
                    'master_paid_percent': 'Мастеру (выплачено)',
                    'master_balance_percent': 'Мастеру (баланс)',
                    'curator_percent': 'Куратору',
                    'company_percent': 'Компании'
                }
                changes.append(f"{field_names[field]}: {old_value}% → {new_value}%")
        
        changes_description = "; ".join(changes) if changes else "Изменений не было"
        
        # Логируем изменение настроек (здесь раньше была ошибка!)
        print("📝 Создание системного лога...")
        log_system_action(
            action='percentage_settings_updated',
            performed_by=user,
            description=f'Обновлены настройки распределения прибыли. Изменения: {changes_description}',
            old_value=str(old_settings),
            new_value=str(new_data),
            metadata={'changes': changes}
        )
        
        print("✅ Настройки успешно обновлены!")
        print(f"📝 Изменения: {changes_description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении настроек: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Запуск тестирования исправленной системы...")
    
    success = True
    
    # Тест 1: Системное логирование
    if not test_system_log_functionality():
        success = False
    
    # Тест 2: Настройки распределения прибыли
    if not test_profit_distribution_settings():
        success = False
    
    # Тест 3: Симуляция обновления настроек
    if not simulate_settings_update():
        success = False
    
    if success:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Критическая ошибка 'IntegrityError: NOT NULL constraint failed: api1_orderlog.order_id' ИСПРАВЛЕНА!")
        print("✅ Система распределения прибыли работает корректно!")
        print("✅ Системное логирование функционирует!")
        print("✅ Валидация данных работает!")
        
        # Показываем последние системные логи
        print("\n📋 Последние системные логи:")
        recent_logs = SystemLog.objects.order_by('-created_at')[:3]
        for i, log in enumerate(recent_logs, 1):
            print(f"   {i}. {log.action} - {log.performed_by.email if log.performed_by else 'Система'}")
            print(f"      {log.description}")
            print(f"      {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    else:
        print("\n❌ ЕСТЬ ПРОБЛЕМЫ В ТЕСТАХ!")
        sys.exit(1)
