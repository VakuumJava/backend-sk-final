
import os
import sys
import django
from decimal import Decimal

sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import *
from api1.views import distribute_completion_funds

def test_profit_distribution():
    print("🔧 Тестируем систему распределения прибыли...")
    
    try:
        print("\n1️⃣ Проверяем настройки системы...")
        settings = ProfitDistributionSettings.get_settings()
        if not settings:
            print("❌ Настройки не найдены, создаем тестовые...")
            settings = ProfitDistributionSettings.objects.create(
                master_paid_percent=Decimal('60'),
                master_balance_percent=Decimal('20'), 
                company_percent=Decimal('20')
            )
        
        print(f"✅ Настройки найдены:")
        print(f"   - Мастеру на руки: {settings.master_paid_percent}%")
        print(f"   - Мастеру на баланс: {settings.master_balance_percent}%") 
        print(f"   - Компании: {settings.company_percent}%")
        
        # 2. Создаем тестовых пользователей
        print("\n2️⃣ Создаем тестовых пользователей...")
        
        # Мастер
        master_user, created = CustomUser.objects.get_or_create(
            email='master@test.com',
            defaults={
                'user_type': 'master',
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
            email='curator@test.com',
            defaults={
                'user_type': 'curator',
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
        
        company_balance, created = Balance.objects.get_or_create(
            user_id=1,  # Системный пользователь для компании
            defaults={'amount': Decimal('0'), 'paid_amount': Decimal('0')}
        )
        print(f"✅ Баланс компании: {company_balance.amount} руб.")
        
        # 4. Создаем тестовый заказ
        print("\n4️⃣ Создаем тестовый заказ...")
        
        order, created = Order.objects.get_or_create(
            id=9999,
            defaults={
                'customer_name': 'Тестовый клиент',
                'customer_phone': '+7999999999',
                'address': 'Тестовый адрес',
                'price': Decimal('1000'),
                'master': master_user,
                'curator': curator_user,
                'status': 'completed'
            }
        )
        if not created:
            order.price = Decimal('1000')
            order.master = master_user
            order.curator = curator_user
            order.status = 'completed'
            order.save()
            
        print(f"✅ Заказ #{order.id} на сумму {order.price} руб.")
        
        # 5. Создаем завершение заказа
        print("\n5️⃣ Создаем завершение заказа...")
        
        completion, created = OrderCompletion.objects.get_or_create(
            order=order,
            defaults={
                'master': master_user,
                'status': 'pending',
                'description': 'Тестовое завершение'
            }
        )
        print(f"✅ Завершение создано, статус: {completion.status}")
        
        # 6. Проверяем расчет распределения
        print("\n6️⃣ Тестируем расчет распределения...")
        
        distribution = completion.calculate_distribution()
        print(f"✅ Расчетное распределение:")
        print(f"   - Мастеру на руки: {distribution['master_immediate']} руб.")
        print(f"   - Мастеру на баланс: {distribution['master_balance']} руб.")
        print(f"   - Куратору: {distribution['curator_amount']} руб.")
        print(f"   - Компании: {distribution['company_amount']} руб.")
        print(f"   - Всего: {distribution['master_immediate'] + distribution['master_balance'] + distribution['curator_amount'] + distribution['company_amount']} руб.")
        
        # 7. Сохраняем начальные балансы
        print("\n7️⃣ Сохраняем начальные балансы...")
        initial_master_amount = master_balance.amount
        initial_master_paid = master_balance.paid_amount
        initial_curator_amount = curator_balance.amount
        initial_company_amount = company_balance.amount
        
        print(f"📊 Начальные балансы:")
        print(f"   - Мастер (баланс): {initial_master_amount} руб.")
        print(f"   - Мастер (на руки): {initial_master_paid} руб.")
        print(f"   - Куратор: {initial_curator_amount} руб.")
        print(f"   - Компания: {initial_company_amount} руб.")
        
        # 8. Выполняем распределение
        print("\n8️⃣ Выполняем распределение средств...")
        
        result = distribute_completion_funds(completion)
        print(f"✅ Результат функции distribute_completion_funds: {result}")
        
        # 9. Проверяем итоговые балансы
        print("\n9️⃣ Проверяем итоговые балансы...")
        
        # Обновляем данные из БД
        master_balance.refresh_from_db()
        curator_balance.refresh_from_db()
        company_balance.refresh_from_db()
        
        print(f"📊 Итоговые балансы:")
        print(f"   - Мастер (баланс): {master_balance.amount} руб. (изменение: +{master_balance.amount - initial_master_amount})")
        print(f"   - Мастер (на руки): {master_balance.paid_amount} руб. (изменение: +{master_balance.paid_amount - initial_master_paid})")
        print(f"   - Куратор: {curator_balance.amount} руб. (изменение: +{curator_balance.amount - initial_curator_amount})")
        print(f"   - Компания: {company_balance.amount} руб. (изменение: +{company_balance.amount - initial_company_amount})")
        
        # 10. Проверяем корректность распределения
        print("\n🔟 Проверяем корректность распределения...")
        
        master_total_change = (master_balance.amount - initial_master_amount) + (master_balance.paid_amount - initial_master_paid)
        curator_change = curator_balance.amount - initial_curator_amount
        company_change = company_balance.amount - initial_company_amount
        total_distributed = master_total_change + curator_change + company_change
        
        print(f"📈 Изменения:")
        print(f"   - Мастер (общее): {master_total_change} руб.")
        print(f"   - Куратор: {curator_change} руб.")
        print(f"   - Компания: {company_change} руб.")
        print(f"   - Всего распределено: {total_distributed} руб.")
        print(f"   - Цена заказа: {order.price} руб.")
        
        # Проверяем соответствие
        if abs(total_distributed - order.price) < Decimal('0.01'):
            print("✅ Распределение корректно: сумма соответствует цене заказа")
        else:
            print(f"❌ Ошибка распределения: распределено {total_distributed}, а должно {order.price}")
            
        # Проверяем пропорции
        expected_master_immediate = order.price * settings.master_paid_percent / 100
        expected_master_balance = order.price * settings.master_balance_percent / 100
        expected_company = order.price * settings.company_percent / 100
        
        master_immediate_change = master_balance.paid_amount - initial_master_paid
        master_balance_change = master_balance.amount - initial_master_amount
        
        print(f"\n📐 Проверка пропорций:")
        print(f"   - Мастеру на руки: ожидается {expected_master_immediate}, получено {master_immediate_change}")
        print(f"   - Мастеру на баланс: ожидается {expected_master_balance}, получено {master_balance_change}")
        print(f"   - Компании: ожидается {expected_company}, получено {company_change}")
        
        # 11. Проверяем статус завершения
        print("\n1️⃣1️⃣ Проверяем статус завершения...")
        completion.refresh_from_db()
        print(f"✅ Статус завершения: {completion.status}")
        
        print("\n🎉 Тест завершен успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_profit_distribution()
