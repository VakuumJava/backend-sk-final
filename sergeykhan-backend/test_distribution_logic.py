#!/usr/bin/env python3
"""
Скрипт для тестирования логики распределения средств
"""

import os
import sys
import django

# Добавляем путь к Django проекту
sys.path.insert(0, '/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')

# Инициализируем Django
django.setup()

from api1.models import OrderCompletion, ProfitDistributionSettings, MasterProfitSettings
from decimal import Decimal

def test_distribution_logic():
    """Тестирует логику распределения средств"""
    
    print("=== ТЕСТ ЛОГИКИ РАСПРЕДЕЛЕНИЯ СРЕДСТВ ===\n")
    
    # Получаем последнее завершение для тестирования
    completion = OrderCompletion.objects.filter(status='одобрен').first()
    if not completion:
        print("Нет одобренных завершений для тестирования")
        return
    
    print(f"Тестируем завершение заказа #{completion.order.id}")
    print(f"Чистая прибыль: {completion.net_profit} тенге")
    print(f"Мастер: {completion.master.get_full_name() if completion.master else 'Не указан'}")
    
    # Получаем распределение
    distribution = completion.calculate_distribution()
    if not distribution:
        print("Не удалось получить распределение")
        return
    
    print(f"\nНастройки ({distribution['settings_used']}):")
    settings = distribution['settings_details']
    print(f"- Мастер к выплате: {settings['master_paid_percent']}%")
    print(f"- Мастер к балансу: {settings['master_balance_percent']}%")  
    print(f"- Куратор: {settings['curator_percent']}%")
    print(f"- Компания: {settings['company_percent']}%")
    
    # Рассчитываем суммы
    master_paid = distribution['master_immediate']  # К выплате
    master_deferred = distribution['master_deferred']  # Только баланс
    total_to_balance = master_paid + master_deferred  # К балансу = выплата + баланс
    
    print(f"\nРАСПРЕДЕЛЕНИЕ СРЕДСТВ:")
    print(f"1. Мастер К ВЫПЛАТЕ (в кошелек): {master_paid} тенге ({settings['master_paid_percent']}%)")
    print(f"2. Мастер К БАЛАНСУ (общая сумма): {total_to_balance} тенге ({settings['master_paid_percent']}% + {settings['master_balance_percent']}%)")
    print(f"   - Из них выплата: {master_paid} тенге")
    print(f"   - Из них баланс: {master_deferred} тенге")
    print(f"3. Куратор: {distribution['curator_share']} тенге ({settings['curator_percent']}%)")
    print(f"4. Компания: {distribution['company_share']} тенге ({settings['company_percent']}%)")
    
    # Проверяем сумму
    total_distributed = master_paid + master_deferred + distribution['curator_share'] + distribution['company_share']
    print(f"\nПРОВЕРКА:")
    print(f"Общая сумма к распределению: {total_distributed} тенге")
    print(f"Чистая прибыль: {completion.net_profit} тенге")
    print(f"Разница: {completion.net_profit - total_distributed} тенге")
    
    if abs(completion.net_profit - total_distributed) < Decimal('0.01'):
        print("✅ РАСПРЕДЕЛЕНИЕ КОРРЕКТНО")
    else:
        print("❌ ОШИБКА В РАСПРЕДЕЛЕНИИ")
    
    print(f"\n=== КЛЮЧЕВЫЕ МОМЕНТЫ ===")
    print(f"• 'К выплате' = {master_paid} тенге (только {settings['master_paid_percent']}%)")
    print(f"• 'К балансу' = {total_to_balance} тенге ({settings['master_paid_percent']}% + {settings['master_balance_percent']}%)")
    print(f"• В кошелек мастера идет только 'К выплате': {master_paid} тенге")
    print(f"• В логах и API должны быть оба значения: {master_paid} и {total_to_balance}")

if __name__ == "__main__":
    test_distribution_logic()
