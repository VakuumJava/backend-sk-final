from django.core.management.base import BaseCommand
from api1.models import CustomUser

class Command(BaseCommand):
    help = 'Установить пароль для супер-админа'

    def handle(self, *args, **options):
        try:
            superadmin = CustomUser.objects.filter(role='super_admin').first()
            if superadmin:
                # Устанавливаем простой пароль для тестирования
                superadmin.set_password('admin123')
                superadmin.save()
                self.stdout.write(f'Пароль установлен для {superadmin.email}')
                self.stdout.write('Новый пароль: admin123')
            else:
                self.stdout.write('Супер-админ не найден')
        except Exception as e:
            self.stdout.write(f'Ошибка: {e}')
