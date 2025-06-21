#!/usr/bin/env python3
"""
Тестируем распределение средств с новым завершением
"""

import os
import sys
import django

# Добавляем путь к Django проекту
sys.path.insert(0, '/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')

# Инициализируем Django
django.setup()

from api1.models import OrderCompletion, FinancialTransaction, BalanceLog
from api1.views.completion_views import distribute_completion_funds
from django.contrib.auth import get_user_model

def test_current_logic():
    """Тестирует текущую логику распределения"""
    
    print("=== ТЕСТ ТЕКУЩЕЙ ЛОГИКИ РАСПРЕДЕЛЕНИЯ ===\n")
    
    # Найдем завершение для тестирования
    completion = OrderCompletion.objects.filter(status='одобрен', is_distributed=False).first()
    if not completion:
        print("Нет подходящих завершений для тестирования")
        return
    
    print(f"Тестируем завершение заказа #{completion.order.id}")
    print(f"Чистая прибыль: {completion.net_profit} тенге")
    print(f"Мастер: {completion.master.get_full_name() if completion.master else 'master@gmail.com'}")
    
    # Получаем куратора
    User = get_user_model()
    curator = User.objects.filter(role='super-admin').first()
    if not curator:
        curator = User.objects.filter(role='curator').first()
    
    if not curator:
        print("Куратор не найден")
        return
    
    print(f"Куратор: {curator.get_full_name() or curator.email}")
    
    # Получаем распределение до выполнения
    distribution = completion.calculate_distribution()
    if not distribution:
        print("Не удалось получить распределение")
        return
    
    print(f"\nНастройки распределения:")
    settings = distribution['settings_details']
    print(f"- Мастер к выплате: {settings['master_paid_percent']}%")
    print(f"- Мастер к балансу: {settings['master_balance_percent']}%")
    print(f"- Куратор: {settings['curator_percent']}%")
    print(f"- Компания: {settings['company_percent']}%")
    
    # Рассчитываем ожидаемые суммы
    master_paid = distribution['master_immediate']  # К выплате
    master_deferred = distribution['master_deferred']  # Только баланс
    total_to_balance = master_paid + master_deferred  # К балансу = выплата + баланс
    
    print(f"\nОЖИДАЕМОЕ РАСПРЕДЕЛЕНИЕ:")
    print(f"1. К выплате (в кошелек): {master_paid} тенге")
    print(f"2. К балансу (общая сумма): {total_to_balance} тенге")
    print(f"3. Куратор: {distribution['curator_share']} тенге")
    print(f"4. Компания: {distribution['company_share']} тенге")
    
    # Получаем количество транзакций до распределения
    transactions_before = FinancialTransaction.objects.filter(order_completion=completion).count()
    print(f"\nТранзакций до распределения: {transactions_before}")
    
    # Выполняем распределение
    print(f"\n=== ВЫПОЛНЯЕМ РАСПРЕДЕЛЕНИЕ ===")
    try:
        result = distribute_completion_funds(completion, curator)
        print(f"✅ Результат: {result}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # Проверяем транзакции после распределения
    transactions_after = FinancialTransaction.objects.filter(order_completion=completion)
    print(f"\nТранзакций после распределения: {transactions_after.count()}")
    
    print(f"\n=== СОЗДАННЫЕ ТРАНЗАКЦИИ ===")
    for transaction in transactions_after:
        print(f"Тип: {transaction.get_transaction_type_display()}")
        print(f"Пользователь: {transaction.user.get_full_name() or transaction.user.email}")
        print(f"Сумма: {transaction.amount} тенге")
        print(f"Описание: {transaction.description}")
        print("---")
    
    # Проверяем соответствие логике
    master_payment_transactions = transactions_after.filter(transaction_type='master_payment')
    master_balance_transactions = transactions_after.filter(transaction_type='master_balance_total')
    master_deferred_transactions = transactions_after.filter(transaction_type='master_deferred')
    
    print(f"\n=== АНАЛИЗ ТРАНЗАКЦИЙ МАСТЕРА ===")
    print(f"Транзакций 'master_payment': {master_payment_transactions.count()}")
    print(f"Транзакций 'master_balance_total': {master_balance_transactions.count()}")
    print(f"Транзакций 'master_deferred': {master_deferred_transactions.count()}")
    
    # Проверяем правильность логики
    if master_payment_transactions.exists():
        payment_amount = master_payment_transactions.first().amount
        print(f"Сумма к выплате: {payment_amount} тенге (ожидалось: {master_paid})")
        if payment_amount == master_paid:
            print("✅ К выплате корректно")
        else:
            print("❌ К выплате некорректно")
    
    if master_balance_transactions.exists():
        balance_amount = master_balance_transactions.first().amount
        print(f"Сумма к балансу: {balance_amount} тенге (ожидалось: {total_to_balance})")
        if balance_amount == total_to_balance:
            print("✅ К балансу корректно")
        else:
            print("❌ К балансу некорректно")
    
    if master_deferred_transactions.exists():
        print("❌ Найдена транзакция 'master_deferred' - это старая логика!")
        deferred_amount = master_deferred_transactions.first().amount
        print(f"Сумма отложенной выплаты: {deferred_amount} тенге")

if __name__ == "__main__":
    test_current_logic()
