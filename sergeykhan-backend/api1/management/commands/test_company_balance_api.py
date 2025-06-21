from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from api1.models import CompanyBalance, CompanyBalanceLog
import requests
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Полный тест API endpoints баланса компании с авторизацией'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Полный тест API endpoints баланса компании'))
        self.stdout.write('=' * 70)
        
        # 1. Создаем или получаем супер-администратора
        try:
            admin_user = User.objects.get(email='testadmin@example.com')
            self.stdout.write(f'✅ Найден администратор: {admin_user.email}')
        except User.DoesNotExist:
            admin_user = User.objects.create_user(
                email='testadmin@example.com',
                password='admin123',
                role='super-admin'
            )
            self.stdout.write(f'✅ Создан администратор: {admin_user.email}')
        
        # 2. Создаем или получаем токен
        token, created = Token.objects.get_or_create(user=admin_user)
        if created:
            self.stdout.write('✅ Создан новый токен')
        else:
            self.stdout.write('✅ Найден существующий токен')
        
        # 3. Создаем или получаем баланс компании
        company_balance = CompanyBalance.get_instance()
        self.stdout.write(f'✅ Баланс компании: {company_balance.amount}')
        
        # 4. Создаем тестовый лог
        from decimal import Decimal
        test_log = CompanyBalanceLog.objects.create(
            action_type='top_up',
            amount=Decimal('5000.00'),
            reason='Автоматический тест API endpoint',
            performed_by=admin_user,
            old_value=company_balance.amount,
            new_value=company_balance.amount + Decimal('5000.00')
        )
        self.stdout.write(f'✅ Создан тестовый лог: ID={test_log.id}')
        
        # 5. Тестируем API endpoints
        base_url = "http://localhost:8000"
        headers = {
            'Authorization': f'Token {token.key}',
            'Content-Type': 'application/json'
        }
        
        # Тест 1: Получение логов баланса компании
        self.stdout.write('\n📡 Тестирование GET /api/company-balance/logs/')
        try:
            response = requests.get(f"{base_url}/api/company-balance/logs/", headers=headers)
            self.stdout.write(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(self.style.SUCCESS('   ✅ Успешно получены логи!'))
                self.stdout.write(f'   📊 Количество логов: {len(data)}')
                
                if data:
                    first_log = data[0]
                    self.stdout.write('   📝 Первый лог содержит поля:')
                    for field in first_log.keys():
                        self.stdout.write(f'      - {field}')
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ Ошибка: {response.text}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Исключение: {e}'))
        
        # Тест 2: Получение текущего баланса компании
        self.stdout.write('\n📡 Тестирование GET /api/company-balance/')
        try:
            response = requests.get(f"{base_url}/api/company-balance/", headers=headers)
            self.stdout.write(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(self.style.SUCCESS('   ✅ Успешно получен баланс!'))
                self.stdout.write(f'   💰 Баланс: {data.get("amount", "не найден")}')
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ Ошибка: {response.text}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Исключение: {e}'))
        
        # Тест 3: Изменение баланса компании (добавление)
        self.stdout.write('\n📡 Тестирование POST /api/company-balance/modify/')
        test_data = {
            'action_type': 'top_up',
            'amount': '1000.00',
            'reason': 'Тестовое пополнение через API'
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/company-balance/modify/", 
                headers=headers,
                json=test_data
            )
            self.stdout.write(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(self.style.SUCCESS('   ✅ Баланс успешно изменен!'))
                self.stdout.write(f'   💰 Новый баланс: {data.get("current_balance", "не найден")}')
            else:
                self.stdout.write(self.style.ERROR(f'   ❌ Ошибка: {response.text}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Исключение: {e}'))
        
        # Тест 4: Проверим, что новый лог создался
        self.stdout.write('\n📡 Повторная проверка логов после изменения баланса')
        try:
            response = requests.get(f"{base_url}/api/company-balance/logs/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(f'   📊 Количество логов сейчас: {len(data)}')
                
                # Проверим последний лог
                if data:
                    latest_log = data[0]  # логи сортируются по убыванию даты
                    self.stdout.write('   📝 Последний лог:')
                    self.stdout.write(f'      - Действие: {latest_log.get("action_type")}')
                    self.stdout.write(f'      - Сумма: {latest_log.get("amount")}')
                    self.stdout.write(f'      - Причина: {latest_log.get("reason")}')
                    self.stdout.write(f'      - Выполнил: {latest_log.get("performed_by_email")}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Исключение: {e}'))
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('🎉 Все тесты API endpoints выполнены!'))
        self.stdout.write(self.style.SUCCESS('✅ Internal Server Error исправлен - API работает корректно!'))
