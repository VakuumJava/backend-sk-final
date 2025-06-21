#!/usr/bin/env python3
"""
Скрипт для тестирования API завершения заказов.
Этот скрипт проверяет процесс завершения заказов через API.
"""
import os
import sys
import django
import random
import json
import requests
from datetime import datetime, timedelta

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order, OrderCompletion
from rest_framework.authtoken.models import Token

# URL базового API
BASE_URL = "http://localhost:8000/api"

def get_token(email):
    """Получить токен для пользователя"""
    try:
        user = CustomUser.objects.get(email=email)
        token, _ = Token.objects.get_or_create(user=user)
        return token.key
    except CustomUser.DoesNotExist:
        print(f"❌ Пользователь с email {email} не найден.")
        return None

def test_order_completion():
    """Тестирование процесса завершения заказов"""
    print("\n🚀 Тестирование API завершения заказов...\n")
    
    # 1. Получаем токены
    master_token = get_token("master1@test.com")
    curator_token = get_token("curator1@test.com")
    
    if not master_token or not curator_token:
        print("❌ Не удалось получить токены для тестирования.")
        return
    
    # 2. Получаем заказы мастера в статусе "выполняется"
    try:
        master_user = CustomUser.objects.get(email="master1@test.com")
        order = Order.objects.filter(
            assigned_master=master_user, 
            status="выполняется",
            is_test=True
        ).first()
        
        if not order:
            # Если нет заказа в статусе "выполняется", попробуем взять в статусе "назначен"
            order = Order.objects.filter(
                assigned_master=master_user, 
                status="назначен",
                is_test=True
            ).first()
            
            # Если нашли, обновим статус на "выполняется"
            if order:
                order.status = "выполняется"
                order.save()
                print(f"✅ Заказ #{order.id} переведен в статус 'выполняется'")
            else:
                print("❌ Не найдено подходящих заказов для мастера master1@test.com")
                return
    except CustomUser.DoesNotExist:
        print("❌ Мастер master1@test.com не найден.")
        return
    
    print(f"🔍 Выбран заказ #{order.id} для тестирования завершения.")
    
    # 3. Завершение заказа мастером
    completion_data = {
        "order_id": order.id,
        "work_description": "Отремонтировал устройство, заменил неисправные детали",
        "parts_expenses": 1500,
        "transport_costs": 500,
        "total_received": 5000,
        "completion_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    print("\n🔄 Отправка данных о завершении заказа мастером...")
    print(f"📋 Данные: {json.dumps(completion_data, indent=2, ensure_ascii=False)}")
    
    # Имитация запроса без фактической отправки
    print("\n✅ [Имитация] Заказ успешно отмечен как выполненный.")
    print(f"✅ [Имитация] Статус заказа изменен на 'ожидает_подтверждения'")
    
    # 4. Подтверждение завершения куратором
    confirmation_data = {
        "order_id": order.id,
        "status": "approved",
        "curator_notes": "Работа выполнена качественно"
    }
    
    print("\n🔄 Подтверждение завершения заказа куратором...")
    print(f"📋 Данные: {json.dumps(confirmation_data, indent=2, ensure_ascii=False)}")
    
    # Имитация запроса без фактической отправки
    print("\n✅ [Имитация] Завершение заказа подтверждено куратором.")
    print(f"✅ [Имитация] Статус заказа изменен на 'завершен'")
    
    # 5. Проверка фактического API (по желанию)
    should_test_real_api = input("\n❓ Хотите выполнить реальный тест API? (y/n): ").lower() == "y"
    
    if should_test_real_api:
        # Реальное завершение заказа мастером
        try:
            headers = {"Authorization": f"Token {master_token}"}
            complete_url = f"{BASE_URL}/complete-order/"
            
            response = requests.post(complete_url, json=completion_data, headers=headers)
            
            if response.status_code == 200:
                print("\n✅ Заказ успешно отмечен как выполненный.")
                print(f"📋 Ответ API: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
                
                # Реальное подтверждение завершения куратором
                headers = {"Authorization": f"Token {curator_token}"}
                confirm_url = f"{BASE_URL}/confirm-completion/"
                
                response = requests.post(confirm_url, json=confirmation_data, headers=headers)
                
                if response.status_code == 200:
                    print("\n✅ Завершение заказа подтверждено куратором.")
                    print(f"📋 Ответ API: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
                else:
                    print(f"\n❌ Ошибка при подтверждении заказа: {response.status_code}")
                    print(f"📋 Ответ API: {response.text}")
            else:
                print(f"\n❌ Ошибка при завершении заказа: {response.status_code}")
                print(f"📋 Ответ API: {response.text}")
        except Exception as e:
            print(f"\n❌ Ошибка при выполнении API запроса: {str(e)}")
    
    print("\n✅ Тестирование процесса завершения заказов завершено.")

if __name__ == "__main__":
    test_order_completion()
