#!/usr/bin/env python
"""
Тестирование доступа к заявкам обратной связи для разных ролей
"""

import os
import django
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, FeedbackRequest
from rest_framework.authtoken.models import Token
import requests

API_BASE_URL = "http://127.0.0.1:8000"

def test_feedback_access():
    print("🧪 Тестирование доступа к заявкам обратной связи")
    print("=" * 60)
    
    # Получаем пользователей разных ролей
    try:
        super_admin = CustomUser.objects.filter(role='super-admin').first()
        curator = CustomUser.objects.filter(role='curator').first()
        operator = CustomUser.objects.filter(role='operator').first()
        master = CustomUser.objects.filter(role='master').first()
        
        print(f"👑 Super Admin: {super_admin.email if super_admin else 'Не найден'}")
        print(f"👨‍💼 Curator: {curator.email if curator else 'Не найден'}")
        print(f"📞 Operator: {operator.email if operator else 'Не найден'}")
        print(f"🔧 Master: {master.email if master else 'Не найден'}")
        print()
        
        # Тестируем доступ для каждой роли
        for user, role_name in [(super_admin, "Super Admin"), (curator, "Curator"), (operator, "Operator"), (master, "Master")]:
            if not user:
                print(f"❌ {role_name}: пользователь не найден")
                continue
                
            # Получаем или создаем токен
            token, created = Token.objects.get_or_create(user=user)
            
            print(f"🔍 Тестирование доступа для {role_name} ({user.email}):")
            
            # Тестируем доступ к непрозвоненным заявкам
            try:
                response = requests.get(
                    f"{API_BASE_URL}/feedback-requests/not-called/",
                    headers={'Authorization': f'Token {token.key}'}
                )
                print(f"  📞 Непрозвоненные: {response.status_code} - {len(response.json()) if response.status_code == 200 else 'Ошибка'}")
            except Exception as e:
                print(f"  📞 Непрозвоненные: Ошибка - {e}")
            
            # Тестируем доступ к обзвоненным заявкам
            try:
                response = requests.get(
                    f"{API_BASE_URL}/feedback-requests/called/",
                    headers={'Authorization': f'Token {token.key}'}
                )
                print(f"  ☎️ Обзвоненные: {response.status_code} - {len(response.json()) if response.status_code == 200 else 'Ошибка'}")
            except Exception as e:
                print(f"  ☎️ Обзвоненные: Ошибка - {e}")
            
            print()
            
        # Общая статистика
        total_requests = FeedbackRequest.objects.count()
        not_called = FeedbackRequest.objects.filter(is_called=False).count()
        called = FeedbackRequest.objects.filter(is_called=True).count()
        
        print(f"📊 Статистика заявок:")
        print(f"  📞 Всего заявок: {total_requests}")
        print(f"  🔴 Не обзвоненные: {not_called}")
        print(f"  🟢 Обзвоненные: {called}")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    test_feedback_access()
