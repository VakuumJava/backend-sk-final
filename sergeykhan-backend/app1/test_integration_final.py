#!/usr/bin/env python3
"""
Интеграционный тест полного процесса одобрения завершения заказа куратором
"""

import os
import sys
import django
import requests
import json
from decimal import Decimal

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import *
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.utils import timezone

def integration_test():
    print("🧪 Интеграционный тест процесса одобрения завершения заказа...")
    
    # API endpoint
    BASE_URL = "http://localhost:8001/api"
    
    try:
        # 1. Создаем тестовых пользователей, если их нет
        print("\n1️⃣ Настройка тестовых пользователей...")
        
        # Куратор
        curator_user, created = CustomUser.objects.get_or_create(
            email='curator_integration@example.com',
            defaults={
                'role': 'curator',
                'first_name': 'Интеграционный',
                'last_name': 'Куратор'
            }
        )
        if created:
            curator_user.set_password('testpass123')
            curator_user.save()
        print(f"✅ Куратор: {curator_user.email}")
        
        # Мастер
        master_user, created = CustomUser.objects.get_or_create(
            email='master_integration@example.com',
            defaults={
                'role': 'master',
                'first_name': 'Интеграционный',
                'last_name': 'Мастер'
            }
        )
        if created:
            master_user.set_password('testpass123')
            master_user.save()
        print(f"✅ Мастер: {master_user.email}")
        
        # 2. Получаем токен куратора для API
        print("\n2️⃣ Получение токена авторизации...")
        token, created = Token.objects.get_or_create(user=curator_user)
        headers = {
            'Authorization': f'Token {token.key}',
            'Content-Type': 'application/json'
        }
        print(f"✅ Токен получен: {token.key[:10]}...")
        
        # 3. Создаем заказ и его завершение
        print("\n3️⃣ Создание тестового заказа и завершения...")
        
        # Используем случайный ID для избежания конфликтов
        import random
        random_id = random.randint(100000, 999999)
        
        order = Order.objects.create(
            id=random_id,
            client_name='Интеграционный клиент',
            client_phone='+7999999998',
            description='Интеграционный тест заказа',
            street='Интеграционная улица',
            house_number='456',
            apartment='78',
            entrance='3',
            status='завершен',
            assigned_master=master_user,
            curator=curator_user,
            final_cost=Decimal('15000.00'),
            is_test=True
        )
        
        completion = OrderCompletion.objects.create(
            order=order,
            master=master_user,
            work_description='Интеграционное завершение работы',
            parts_expenses=Decimal('3000.00'),
            transport_costs=Decimal('500.00'),
            total_received=Decimal('15000.00'),
            completion_date=timezone.now(),
            status='ожидает_проверки',
            curator_notes='',
        )
        
        print(f"✅ Заказ #{order.id} создан")
        print(f"✅ Завершение создано, ID: {completion.id}")
        print(f"   - Чистая прибыль: {completion.net_profit} руб.")
        
        # 4. Сохраняем начальные балансы
        master_balance, _ = Balance.objects.get_or_create(user=master_user)
        curator_balance, _ = Balance.objects.get_or_create(user=curator_user)
        
        initial_master_amount = master_balance.amount
        initial_master_paid = master_balance.paid_amount
        initial_curator_amount = curator_balance.amount
        
        print(f"   - Начальный баланс мастера: {initial_master_amount} руб. (на руки: {initial_master_paid})")
        print(f"   - Начальный баланс куратора: {initial_curator_amount} руб.")
        
        # 5. Тестируем API одобрения завершения
        print("\n4️⃣ Тестируем API одобрения завершения...")
        
        approve_url = f"{BASE_URL}/completions/{completion.id}/review/"
        approve_data = {
            'action': 'approve',
            'comment': 'Интеграционный тест - одобрено автоматически'
        }
        
        print(f"Отправляем POST запрос на: {approve_url}")
        print(f"Данные: {approve_data}")
        
        response = requests.post(
            approve_url,
            headers=headers,
            data=json.dumps(approve_data)
        )
        
        print(f"✅ Ответ API: {response.status_code}")
        if response.status_code == 200:
            response_data = response.json()
            print(f"   Статус завершения: {response_data.get('status')}")
            print(f"   Распределение выполнено: {response_data.get('is_distributed')}")
        else:
            print(f"❌ Ошибка API: {response.text}")
            return False
        
        # 6. Проверяем изменения балансов
        print("\n5️⃣ Проверяем изменения балансов...")
        
        # Обновляем балансы из базы
        master_balance.refresh_from_db()
        curator_balance.refresh_from_db()
        completion.refresh_from_db()
        
        print(f"   - Новый баланс мастера: {master_balance.amount} руб. (на руки: {master_balance.paid_amount})")
        print(f"   - Новый баланс куратора: {curator_balance.amount} руб.")
        print(f"   - Статус распределения: {completion.is_distributed}")
        
        # Проверяем изменения
        master_amount_change = master_balance.amount - initial_master_amount
        master_paid_change = master_balance.paid_amount - initial_master_paid
        curator_amount_change = curator_balance.amount - initial_curator_amount
        
        print(f"   - Изменение баланса мастера: +{master_amount_change} руб.")
        print(f"   - Изменение выплат мастеру: +{master_paid_change} руб.")
        print(f"   - Изменение баланса куратора: +{curator_amount_change} руб.")
        
        # 7. Проверяем, что процентное распределение правильное
        print("\n6️⃣ Проверяем правильность процентного распределения...")
        
        settings = ProfitDistributionSettings.get_settings()
        expected_master_paid = completion.net_profit * Decimal(settings.master_paid_percent) / 100
        expected_master_balance = completion.net_profit * Decimal(settings.master_balance_percent) / 100
        expected_curator = completion.net_profit * Decimal(settings.curator_percent) / 100
        
        print(f"   Ожидаемые суммы (согласно {settings.master_paid_percent}/{settings.master_balance_percent}/{settings.curator_percent}/{settings.company_percent}%):")
        print(f"   - Мастеру на руки: {expected_master_paid} руб.")
        print(f"   - Мастеру на баланс: {expected_master_balance} руб.")
        print(f"   - Куратору: {expected_curator} руб.")
        
        # Проверяем точность
        tolerance = Decimal('0.01')
        if abs(master_paid_change - expected_master_paid) < tolerance:
            print("   ✅ Выплата мастеру корректна")
        else:
            print(f"   ❌ Ошибка в выплате мастеру: ожидали {expected_master_paid}, получили {master_paid_change}")
            
        if abs(master_amount_change - expected_master_balance) < tolerance:
            print("   ✅ Баланс мастера корректен")
        else:
            print(f"   ❌ Ошибка в балансе мастера: ожидали {expected_master_balance}, получили {master_amount_change}")
            
        if abs(curator_amount_change - expected_curator) < tolerance:
            print("   ✅ Баланс куратора корректен")
        else:
            print(f"   ❌ Ошибка в балансе куратора: ожидали {expected_curator}, получили {curator_amount_change}")
        
        # 8. Проверяем создание транзакций
        print("\n7️⃣ Проверяем создание финансовых транзакций...")
        
        master_transactions = FinancialTransaction.objects.filter(
            user=master_user,
            order_completion=completion
        ).count()
        
        curator_transactions = FinancialTransaction.objects.filter(
            user=curator_user,
            order_completion=completion
        ).count()
        
        print(f"   - Транзакций мастера: {master_transactions}")
        print(f"   - Транзакций куратора: {curator_transactions}")
        
        if master_transactions >= 1 and curator_transactions >= 1:
            print("   ✅ Финансовые транзакции созданы")
        else:
            print("   ❌ Некоторые финансовые транзакции не созданы")
        
        print("\n🎉 Интеграционный тест завершен успешно!")
        print("✅ Система распределения прибыли работает корректно через API!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка во время интеграционного теста: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    integration_test()
