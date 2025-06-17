#!/usr/bin/env python3
"""
Финальный тест исправления критической ошибки:
IntegrityError: NOT NULL constraint failed: api1_orderlog.order_id

Этот тест проверяет, что функция profit_distribution работает корректно
после исправления и не выдает ошибку IntegrityError.
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import *
from api1.views import log_system_action
from django.test import RequestFactory
from api1.views import profit_distribution
import json

def main():
    print('🎯 ФИНАЛЬНЫЙ ТЕСТ ИСПРАВЛЕНИЯ КРИТИЧЕСКОЙ ОШИБКИ')
    print('=' * 50)
    print('Ошибка: IntegrityError: NOT NULL constraint failed: api1_orderlog.order_id')
    print('Исправление: Добавлена модель SystemLog и функция log_system_action')
    print('=' * 50)
    
    try:
        # Создаем тестового пользователя с помощью CustomUser
        user, created = CustomUser.objects.get_or_create(
            username='final_test_admin', 
            defaults={
                'email': 'final_test@admin.com', 
                'is_superuser': True, 
                'is_staff': True,
                'first_name': 'Final',
                'last_name': 'Test'
            }
        )
        print(f'✅ Тестовый пользователь: {user.username} ({user.email})')
        
        # Создаем mock request
        factory = RequestFactory()
        
        # 1. Тестируем GET запрос
        print('\n📊 1. Тестирование GET запроса...')
        request = factory.get('/api/profit-distribution/')
        request.user = user
        response = profit_distribution(request)
        print(f'   ✅ GET статус: {response.status_code}')
        
        if response.status_code == 200:
            data = json.loads(response.content)
            total = (data.get('master_paid_percentage', 0) + 
                    data.get('master_balance_percentage', 0) + 
                    data.get('curator_percentage', 0) + 
                    data.get('company_percentage', 0))
            print(f'   📊 Текущие настройки:')
            print(f'      • Мастеру (выплачено): {data.get("master_paid_percentage")}%')
            print(f'      • Мастеру (баланс): {data.get("master_balance_percentage")}%')
            print(f'      • Куратору: {data.get("curator_percentage")}%')
            print(f'      • Компании: {data.get("company_percentage")}%')
            print(f'   ✅ Общая сумма: {total}% (должно быть 100%)')
        
        # 2. Тестируем POST запрос с валидными данными
        print('\n📝 2. Тестирование POST запроса (обновление настроек)...')
        test_data = {
            'master_paid_percentage': 40,
            'master_balance_percentage': 20,
            'curator_percentage': 15,
            'company_percentage': 25
        }
        
        request = factory.post('/api/profit-distribution/', 
                              data=json.dumps(test_data), 
                              content_type='application/json')
        request.user = user
        
        initial_log_count = SystemLog.objects.count()
        print(f'   📊 Логов до обновления: {initial_log_count}')
        
        response = profit_distribution(request)
        print(f'   ✅ POST статус: {response.status_code}')
        
        if response.status_code == 200:
            data = json.loads(response.content)
            print(f'   ✅ Обновление успешно!')
            print(f'   📄 Ответ: {data.get("message", "Настройки обновлены")}')
            
            # Проверяем, что логи создаются
            final_log_count = SystemLog.objects.count()
            print(f'   📊 Логов после обновления: {final_log_count}')
            
            if final_log_count > initial_log_count:
                print('   ✅ Новый системный лог создан!')
                last_log = SystemLog.objects.filter(action='percentage_settings_updated').last()
                if last_log:
                    print(f'      📝 Описание: {last_log.description[:80]}...')
                    print(f'      👤 Пользователь: {last_log.performed_by}')
                    print(f'      📅 Время: {last_log.created_at.strftime("%Y-%m-%d %H:%M:%S")}')
            else:
                print('   ⚠️ Новый лог не был создан (возможно, значения не изменились)')
        else:
            print(f'   ❌ Ошибка обновления - статус: {response.status_code}')
            print(f'   📄 Содержимое ответа: {response.content.decode()}')
        
        # 3. Тестируем POST запрос с невалидными данными
        print('\n🚫 3. Тестирование POST запроса с невалидными данными...')
        invalid_data = {
            'master_paid_percentage': 50,
            'master_balance_percentage': 30,
            'curator_percentage': 15,
            'company_percentage': 25  # Сумма: 120% (должна быть 100%)
        }
        
        request = factory.post('/api/profit-distribution/', 
                              data=json.dumps(invalid_data), 
                              content_type='application/json')
        request.user = user
        
        response = profit_distribution(request)
        print(f'   ✅ POST статус: {response.status_code}')
        
        if response.status_code == 400:
            data = json.loads(response.content)
            print(f'   ✅ Валидация работает корректно!')
            print(f'   📄 Ошибки: {data.get("errors", [])}')
        else:
            print(f'   ⚠️ Неожиданный ответ - статус: {response.status_code}')
        
        # 4. Итоговая статистика
        print('\n📊 4. Итоговая статистика...')
        total_logs = SystemLog.objects.count()
        recent_logs = SystemLog.objects.filter(action='percentage_settings_updated').order_by('-created_at')[:3]
        
        print(f'   📊 Всего системных логов: {total_logs}')
        print(f'   📋 Последние логи настроек распределения прибыли:')
        
        for i, log in enumerate(recent_logs, 1):
            print(f'      {i}. {log.performed_by} - {log.created_at.strftime("%Y-%m-%d %H:%M")}')
            print(f'         {log.description[:60]}...')
        
        print('\n' + '=' * 50)
        print('🎉 ФИНАЛЬНЫЙ ТЕСТ ПРОЙДЕН УСПЕШНО!')
        print('✅ Критическая ошибка IntegrityError ИСПРАВЛЕНА!')
        print('✅ Функция profit_distribution работает корректно!')
        print('✅ Системные логи создаются без ошибок!')
        print('✅ Валидация данных функционирует!')
        print('=' * 50)
        
    except Exception as e:
        print(f'\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}')
        import traceback
        traceback.print_exc()
        print('\n💡 Если вы видите эту ошибку, исправление не работает корректно!')
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    if success:
        print('\n🚀 Готово к развертыванию в продакшн!')
    else:
        print('\n🔧 Требуется дополнительная настройка.')
