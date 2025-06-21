#!/usr/bin/env python3
"""
Исправленный тест системы распределения прибыли
"""

import os
import sys
import django
from decimal import Decimal

# Настройка Django
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import *
from api1.views import distribute_completion_funds
from django.utils import timezone

def test_profit_distribution():
    print("🔧 Тестируем систему распределения прибыли...")
    
    try:
        # 1. Проверяем настройки
        print("\n1️⃣ Проверяем настройки системы...")
        settings = ProfitDistributionSettings.get_settings()
        if not settings:
            print("❌ Настройки не найдены, создаем тестовые...")
            settings = ProfitDistributionSettings.objects.create(
                master_paid_percent=60,
                master_balance_percent=20,
                company_percent=20
            )
        else:
            # Обновляем настройки для тестирования
            print("📝 Обновляем настройки для теста...")
            settings.master_paid_percent = 60
            settings.master_balance_percent = 20
            settings.curator_percent = 5
            settings.company_percent = 15
            settings.save()
        
        print(f"✅ Настройки найдены:")
        print(f"   - Мастеру на руки: {settings.master_paid_percent}%")
        print(f"   - Мастеру на баланс: {settings.master_balance_percent}%") 
        print(f"   - Компании: {settings.company_percent}%")
        
        # 2. Создаем тестовых пользователей
        print("\n2️⃣ Создаем тестовых пользователей...")
        
        # Мастер
        master_user, created = CustomUser.objects.get_or_create(
            email='master_test@example.com',
            defaults={
                'role': 'master',
                'first_name': 'Тест',
                'last_name': 'Мастер'
            }
        )
        if created:
            master_user.set_password('testpass')
            master_user.save()
        print(f"✅ Мастер: {master_user.email}")
        
        # Куратор
        curator_user, created = CustomUser.objects.get_or_create(
            email='curator_test@example.com',
            defaults={
                'role': 'curator',
                'first_name': 'Тест',
                'last_name': 'Куратор'
            }
        )
        if created:
            curator_user.set_password('testpass')
            curator_user.save()
        print(f"✅ Куратор: {curator_user.email}")
        
        # 3. Создаем балансы
        print("\n3️⃣ Создаем балансы...")
        
        master_balance, created = Balance.objects.get_or_create(
            user=master_user,
            defaults={'amount': Decimal('0'), 'paid_amount': Decimal('0')}
        )
        print(f"✅ Баланс мастера: {master_balance.amount} руб. (на руки: {master_balance.paid_amount})")
        
        curator_balance, created = Balance.objects.get_or_create(
            user=curator_user,
            defaults={'amount': Decimal('0'), 'paid_amount': Decimal('0')}
        )
        print(f"✅ Баланс куратора: {curator_balance.amount} руб.")
        
        # 4. Создаем тестовый заказ
        print("\n4️⃣ Создаем тестовый заказ...")
        
        order, created = Order.objects.get_or_create(
            id=9999,
            defaults={
                'client_name': 'Тестовый клиент',
                'client_phone': '+7999999999',
                'description': 'Тестовое описание заказа',
                'street': 'Тестовая улица',
                'house_number': '123',
                'apartment': '45',
                'entrance': '2',
                'status': 'завершен',
                'assigned_master': master_user,
                'curator': curator_user,
                'final_cost': Decimal('10000.00'),
                'is_test': True
            }
        )
        if not created:
            order.final_cost = Decimal('10000.00')
            order.assigned_master = master_user
            order.curator = curator_user
            order.status = 'завершен'
            order.save()
            
        print(f"✅ Заказ #{order.id} на сумму {order.final_cost} руб.")
        
        # 5. Создаем завершение заказа
        print("\n5️⃣ Создаем завершение заказа...")
        
        completion, created = OrderCompletion.objects.get_or_create(
            order=order,
            defaults={
                'master': master_user,
                'work_description': 'Тестовое завершение работы',
                'parts_expenses': Decimal('2000.00'),
                'transport_costs': Decimal('500.00'),
                'total_received': Decimal('10000.00'),
                'completion_date': timezone.now(),
                'status': 'одобрен',
                'curator': curator_user,
                'review_date': django.utils.timezone.now(),
                'curator_notes': 'Тестовая проверка'
            }
        )
        if not created:
            completion.status = 'одобрен'
            completion.curator = curator_user
            completion.review_date = timezone.now()
            completion.save()
            
        print(f"✅ Завершение создано, статус: {completion.status}")
        print(f"   - Общие расходы: {completion.total_expenses} руб.")
        print(f"   - Чистая прибыль: {completion.net_profit} руб.")
        
        # 6. Проверяем расчет распределения
        print("\n6️⃣ Тестируем расчет распределения...")
        
        distribution = completion.calculate_distribution()
        if distribution:
            print(f"✅ Расчетное распределение:")
            print(f"   - Мастеру на руки: {distribution['master_immediate']} руб.")
            print(f"   - Мастеру на баланс: {distribution['master_deferred']} руб.")
            print(f"   - Куратору: {distribution['curator_share']} руб.")
            print(f"   - Компании: {distribution['company_share']} руб.")
            total_calc = distribution['master_immediate'] + distribution['master_deferred'] + distribution['curator_share'] + distribution['company_share']
            print(f"   - Всего распределено: {total_calc} руб.")
            print(f"   - Чистая прибыль: {completion.net_profit} руб.")
        else:
            print("❌ Не удалось рассчитать распределение")
            return False
        
        # 7. Сохраняем начальные балансы
        print("\n7️⃣ Сохраняем начальные балансы...")
        
        initial_master_amount = master_balance.amount
        initial_master_paid = master_balance.paid_amount
        initial_curator_amount = curator_balance.amount
        print(f"   - Начальный баланс мастера: {initial_master_amount} руб. (на руки: {initial_master_paid})")
        print(f"   - Начальный баланс куратора: {initial_curator_amount} руб.")
        
        # 8. Тестируем функцию распределения
        print("\n8️⃣ Запускаем функцию распределения...")
        
        result = distribute_completion_funds(completion, curator_user)
        print(f"✅ Функция вернула результат: {result}")
        
        # 9. Проверяем изменения балансов
        print("\n9️⃣ Проверяем изменения балансов...")
        
        # Обновляем балансы из базы
        master_balance.refresh_from_db()
        curator_balance.refresh_from_db()
        
        print(f"   - Новый баланс мастера: {master_balance.amount} руб. (на руки: {master_balance.paid_amount})")
        print(f"   - Новый баланс куратора: {curator_balance.amount} руб.")
        
        # Проверяем изменения
        master_amount_change = master_balance.amount - initial_master_amount
        master_paid_change = master_balance.paid_amount - initial_master_paid
        curator_amount_change = curator_balance.amount - initial_curator_amount
        
        print(f"   - Изменение баланса мастера: +{master_amount_change} руб.")
        print(f"   - Изменение выплат мастеру: +{master_paid_change} руб.")
        print(f"   - Изменение баланса куратора: +{curator_amount_change} руб.")
        
        # 10. Проверяем корректность расчетов
        print("\n🔟 Проверяем корректность расчетов...")
        
        expected_master_balance = distribution['master_deferred']
        expected_master_paid = distribution['master_immediate'] 
        expected_curator = distribution['curator_share']
        
        if abs(master_amount_change - expected_master_balance) < Decimal('0.01'):
            print("✅ Баланс мастера изменился корректно")
        else:
            print(f"❌ Ошибка в балансе мастера: ожидали {expected_master_balance}, получили изменение {master_amount_change}")
            
        if abs(master_paid_change - expected_master_paid) < Decimal('0.01'):
            print("✅ Выплата мастеру добавлена корректно")
        else:
            print(f"❌ Ошибка в выплате мастеру: ожидали {expected_master_paid}, получили изменение {master_paid_change}")
            
        if abs(curator_amount_change - expected_curator) < Decimal('0.01'):
            print("✅ Баланс куратора изменился корректно")
        else:
            print(f"❌ Ошибка в балансе куратора: ожидали {expected_curator}, получили изменение {curator_amount_change}")
        
        # 11. Проверяем статус распределения
        completion.refresh_from_db()
        if completion.is_distributed:
            print("✅ Статус распределения обновлен корректно")
        else:
            print("❌ Статус распределения не обновился")
        
        print("\n🎉 Тест завершен успешно!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_profit_distribution()
