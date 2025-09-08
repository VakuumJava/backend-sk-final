from django.core.management.base import BaseCommand
from api1.models import CustomUser
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Создать администратора'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email администратора', default='admin@sergeykhan.kz')
        parser.add_argument('--password', type=str, help='Пароль администратора', default='admin123')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']
        password = options['password']
        
        try:
            # Проверяем, существует ли уже пользователь с таким email
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                self.stdout.write(f'⚠️ Пользователь с email {email} уже существует')
                
                # Обновляем пароль и права
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.role = 'super-admin'
                user.save()
                
                self.stdout.write(self.style.SUCCESS(f'✅ Пароль и права обновлены для {email}'))
            else:
                # Создаем нового суперпользователя
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name='Admin',
                    last_name='User',
                    role='super-admin'
                )
                self.stdout.write(self.style.SUCCESS(f'✅ Суперпользователь создан: {email}'))
            
            self.stdout.write('=' * 50)
            self.stdout.write(f'📧 Email: {email}')
            self.stdout.write(f'🔑 Пароль: {password}')
            self.stdout.write(f'👤 Роль: {user.role}')
            self.stdout.write(f'🔐 Супер админ: {user.is_superuser}')
            self.stdout.write(f'👮 Персонал: {user.is_staff}')
            self.stdout.write(f'✅ Активен: {user.is_active}')
            self.stdout.write('=' * 50)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка при создании администратора: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
