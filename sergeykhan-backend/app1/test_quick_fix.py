#!/usr/bin/env python3
"""
Быстрый тест для проверки исправления ошибки
"""

import os
import sys
import django

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, ProfitDistributionSettings, SystemLog

def quick_test():
    """Быстрый тест основного функционала"""
    print("🔧 Быстрый тест исправленной системы...")
    
    # 1. Проверяем, что модель SystemLog существует
    print("1. Проверка модели SystemLog...")
    try:
        count = SystemLog.objects.count()
        print(f"   ✅ Модель SystemLog работает. Записей: {count}")
    except Exception as e:
        print(f"   ❌ Ошибка модели SystemLog: {e}")
        return False
    
    # 2. Создаём тестовый лог
    print("2. Создание тестового системного лога...")
    try:
        # Создаём пользователя если нужно
        user, created = CustomUser.objects.get_or_create(
            email='quick_test@test.com',
            defaults={'role': 'super-admin'}
        )
        if created:
            user.set_password('test123')
            user.save()
        
        # Создаём системный лог
        log = SystemLog.objects.create(
            action='percentage_settings_updated',
            description='Тестовое логирование исправленной системы',
            performed_by=user,
            old_value='test_old',
            new_value='test_new',
            metadata={'test': True}
        )
        print(f"   ✅ Системный лог создан: ID {log.id}")
        
    except Exception as e:
        print(f"   ❌ Ошибка создания лога: {e}")
        return False
    
    # 3. Проверяем настройки распределения прибыли
    print("3. Проверка настроек распределения прибыли...")
    try:
        settings = ProfitDistributionSettings.get_settings()
        print(f"   ✅ Настройки получены:")
        print(f"      Мастеру (выплачено): {settings.master_paid_percent}%")
        print(f"      Мастеру (баланс): {settings.master_balance_percent}%")
        print(f"      Куратору: {settings.curator_percent}%")
        print(f"      Компании: {settings.company_percent}%")
        
        # Проверяем валидацию
        total = (settings.master_paid_percent + settings.master_balance_percent + 
                settings.curator_percent + settings.company_percent)
        print(f"      Общая сумма: {total}%")
        
        if total == 100:
            print("   ✅ Валидация корректна: сумма = 100%")
        else:
            print(f"   ⚠️ Сумма не равна 100%: {total}%")
            
    except Exception as e:
        print(f"   ❌ Ошибка настроек: {e}")
        return False
    
    # 4. Тестируем функцию log_system_action
    print("4. Тестирование функции log_system_action...")
    try:
        from api1.views import log_system_action
        
        old_count = SystemLog.objects.count()
        
        log_system_action(
            action='percentage_settings_updated',
            performed_by=user,
            description='Проверка исправленной функции логирования',
            old_value='{"test": "old_value"}',
            new_value='{"test": "new_value"}',
            metadata={'fix_test': True}
        )
        
        new_count = SystemLog.objects.count()
        
        if new_count > old_count:
            print("   ✅ Функция log_system_action работает корректно!")
        else:
            print("   ❌ Функция log_system_action не создала лог!")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка функции log_system_action: {e}")
        return False
    
    return True

if __name__ == '__main__':
    print("🚀 Запуск быстрого теста исправления...")
    
    if quick_test():
        print("\n🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("✅ Критическая ошибка 'IntegrityError: NOT NULL constraint failed: api1_orderlog.order_id' ИСПРАВЛЕНА!")
        print("✅ Система может логировать изменения настроек распределения прибыли!")
        print("✅ Модель SystemLog функционирует корректно!")
        print("✅ Функция log_system_action работает без ошибок!")
        
        # Показываем количество системных логов
        total_logs = SystemLog.objects.count()
        print(f"\n📊 Всего системных логов в базе: {total_logs}")
        
        recent_logs = SystemLog.objects.order_by('-created_at')[:2]
        if recent_logs:
            print("📋 Последние логи:")
            for log in recent_logs:
                print(f"   • {log.action} - {log.description[:50]}...")
        
    else:
        print("\n❌ ТЕСТ НЕ ПРОЙДЕН!")
        print("Есть проблемы в исправленной системе.")
        sys.exit(1)
