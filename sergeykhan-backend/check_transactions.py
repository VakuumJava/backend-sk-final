#!/usr/bin/env python3
"""
Скрипт для проверки транзакций и логов
"""

import os
import sys
import django

# Добавляем путь к Django проекту
sys.path.insert(0, '/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')

# Инициализируем Django
django.setup()

from api1.models import OrderCompletion, FinancialTransaction, BalanceLog, Balance

def check_distribution_records():
    """Проверяет записи о распределении средств"""
    
    print("=== ПРОВЕРКА ЗАПИСЕЙ О РАСПРЕДЕЛЕНИИ ===\n")
    
    # Найдем завершение, которое было недавно распределено
    completion = OrderCompletion.objects.filter(is_distributed=True).last()
    if not completion:
        print("Нет распределенных завершений")
        return
    
    print(f"Проверяем завершение заказа #{completion.order.id}")
    print(f"Мастер: {completion.master.get_full_name() if completion.master else 'Не указан'}")
    print(f"Чистая прибыль: {completion.net_profit} тенге")
    
    # Проверяем транзакции
    print(f"\n=== ФИНАНСОВЫЕ ТРАНЗАКЦИИ ===")
    transactions = FinancialTransaction.objects.filter(order_completion=completion)
    
    for transaction in transactions:
        print(f"Тип: {transaction.get_transaction_type_display()}")
        print(f"Пользователь: {transaction.user.get_full_name() or transaction.user.email}")
        print(f"Сумма: {transaction.amount} тенге")
        print(f"Описание: {transaction.description}")
        print(f"Дата: {transaction.created_at}")
        print("---")
    
    # Проверяем логи баланса
    print(f"\n=== ЛОГИ БАЛАНСА ===")
    if completion.master:
        balance_logs = BalanceLog.objects.filter(
            user=completion.master,
            reason__icontains=f"заказ #{completion.order.id}"
        )
        
        for log in balance_logs:
            print(f"Действие: {log.get_action_type_display()}")
            print(f"Сумма: {log.amount} тенге")
            print(f"Причина: {log.reason}")
            print(f"Старый баланс: {log.old_value} тенге")
            print(f"Новый баланс: {log.new_value} тенге")
            print(f"Дата: {log.created_at}")
            print("---")
    
    # Проверяем текущий баланс мастера
    if completion.master:
        try:
            balance = Balance.objects.get(user=completion.master)
            print(f"\n=== ТЕКУЩИЙ БАЛАНС МАСТЕРА ===")
            print(f"Баланс: {balance.amount} тенге")
        except Balance.DoesNotExist:
            print(f"\n❌ Баланс мастера не найден")

if __name__ == "__main__":
    check_distribution_records()
