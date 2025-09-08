from django.core.management.base import BaseCommand
from api1.models import CustomUser
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Показать список всех пользователей'

    def handle(self, *args, **options):
        User = get_user_model()
        
        self.stdout.write('=' * 60)
        self.stdout.write('📋 СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ')
        self.stdout.write('=' * 60)
        
        users = User.objects.all().order_by('id')
        
        if not users:
            self.stdout.write('❌ Пользователи не найдены')
            return
        
        for user in users:
            self.stdout.write(f'ID: {user.id}')
            self.stdout.write(f'📧 Email: {user.email}')
            self.stdout.write(f'👤 Имя: {user.first_name} {user.last_name}')
            self.stdout.write(f'🏷️ Роль: {user.role}')
            self.stdout.write(f'🔐 Супер админ: {user.is_superuser}')
            self.stdout.write(f'👮 Персонал: {user.is_staff}')
            self.stdout.write(f'✅ Активен: {user.is_active}')
            self.stdout.write(f'📅 Создан: {user.date_joined}')
            self.stdout.write(f'🕐 Последний вход: {user.last_login}')
            self.stdout.write('-' * 40)
        
        self.stdout.write(f'📊 Всего пользователей: {users.count()}')
        
        # Статистика по ролям
        self.stdout.write('\n📈 СТАТИСТИКА ПО РОЛЯМ:')
        roles = User.objects.values_list('role', flat=True).distinct()
        for role in roles:
            count = User.objects.filter(role=role).count()
            self.stdout.write(f'  {role}: {count}')
