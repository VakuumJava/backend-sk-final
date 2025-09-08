from django.core.management.base import BaseCommand
from api1.models import CustomUser

class Command(BaseCommand):
    help = 'Установить пароль для супер-админа'

    def handle(self, *args, **options):
        try:
            # Исправляем роль с подчеркивания на дефис
            superadmin = CustomUser.objects.filter(role='super-admin').first()
            if superadmin:
                # Устанавливаем простой пароль для тестирования
                superadmin.set_password('admin123')
                superadmin.save()
                self.stdout.write(f'Пароль установлен для {superadmin.email}')
                self.stdout.write('Новый пароль: admin123')
            else:
                self.stdout.write('Супер-админ не найден')
                # Попробуем создать суперпользователя, если его нет
                self.stdout.write('Попытка создать суперпользователя...')
                superuser = CustomUser.objects.create_superuser(
                    email='admin@example.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User',
                    role='super-admin'
                )
                self.stdout.write(f'Суперпользователь создан: {superuser.email}')
                self.stdout.write('Email: admin@example.com')
                self.stdout.write('Пароль: admin123')
        except Exception as e:
            self.stdout.write(f'Ошибка: {e}')
