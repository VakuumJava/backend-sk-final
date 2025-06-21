from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api1.models import CompanyBalance, CompanyBalanceLog
from api1.serializers import CompanyBalanceLogSerializer
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Тестирует исправленный CompanyBalanceLogSerializer'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Тестирование CompanyBalanceLogSerializer'))
        self.stdout.write('=' * 60)
        
        # 1. Создаем или получаем тестового пользователя
        try:
            admin_user = User.objects.get(email='test@admin.com')
            self.stdout.write(f'✅ Найден пользователь: {admin_user.email}')
        except User.DoesNotExist:
            admin_user = User.objects.create_user(
                email='test@admin.com',
                password='test123',
                role='super_admin'
            )
            self.stdout.write(f'✅ Создан пользователь: {admin_user.email}')
        
        # 2. Создаем или получаем запись баланса компании
        company_balance, created = CompanyBalance.objects.get_or_create(
            id=1,
            defaults={'amount': 50000.00}
        )
        if created:
            self.stdout.write(f'✅ Создан баланс компании: {company_balance.amount}')
        else:
            self.stdout.write(f'✅ Баланс компании: {company_balance.amount}')
        
        # 3. Создаем тестовый лог
        from decimal import Decimal
        test_amount = Decimal('10000.00')
        test_log = CompanyBalanceLog.objects.create(
            action_type='add',
            amount=test_amount,
            reason='Тестовая операция для проверки сериализатора',
            performed_by=admin_user,
            old_value=company_balance.amount,
            new_value=company_balance.amount + test_amount
        )
        self.stdout.write(f'✅ Создан тестовый лог: ID={test_log.id}')
        
        # 4. Тестируем сериализатор
        try:
            serializer = CompanyBalanceLogSerializer(test_log)
            serialized_data = serializer.data
            
            self.stdout.write(self.style.SUCCESS('✅ Сериализация прошла успешно!'))
            self.stdout.write('📊 Сериализованные данные:')
            self.stdout.write(json.dumps(serialized_data, indent=2, ensure_ascii=False, default=str))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка сериализации: {e}'))
            return
        
        # 5. Тестируем сериализацию всех логов
        try:
            all_logs = CompanyBalanceLog.objects.all()[:5]  # Берем первые 5
            serializer = CompanyBalanceLogSerializer(all_logs, many=True)
            serialized_data = serializer.data
            
            self.stdout.write(f'✅ Сериализация множественных объектов успешна!')
            self.stdout.write(f'📊 Количество логов: {len(serialized_data)}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка множественной сериализации: {e}'))
            return
        
        # 6. Проверим, что все поля присутствуют (берем первый элемент)
        expected_fields = [
            'id', 'action_type', 'action_type_display', 'amount', 'reason',
            'performed_by', 'performed_by_email', 'old_value', 'new_value', 'created_at'
        ]
        
        if serialized_data:
            first_item = serialized_data[0] if isinstance(serialized_data, list) else serialized_data
            actual_fields = set(first_item.keys())
            missing_fields = set(expected_fields) - actual_fields
            extra_fields = actual_fields - set(expected_fields)
            
            if missing_fields:
                self.stdout.write(self.style.WARNING(f'⚠️  Отсутствующие поля: {missing_fields}'))
            
            if extra_fields:
                self.stdout.write(self.style.WARNING(f'⚠️  Дополнительные поля: {extra_fields}'))
            
            if not missing_fields and not extra_fields:
                self.stdout.write(self.style.SUCCESS('✅ Все ожидаемые поля присутствуют!'))
        
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('🎉 Тестирование сериализатора завершено успешно!'))
