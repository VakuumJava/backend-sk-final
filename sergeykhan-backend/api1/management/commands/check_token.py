from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token
from api1.models import CustomUser

class Command(BaseCommand):
    help = 'Проверить токен супер-админа'

    def handle(self, *args, **options):
        superadmin = CustomUser.objects.filter(role='super_admin').first()
        if superadmin:
            try:
                token = Token.objects.get(user=superadmin)
                self.stdout.write(f'User: {superadmin.email}')
                self.stdout.write(f'Token: {token.key}')
                self.stdout.write(f'Is active: {superadmin.is_active}')
                self.stdout.write(f'Role: {superadmin.role}')
            except Token.DoesNotExist:
                self.stdout.write('Токен не найден для супер-админа')
        else:
            self.stdout.write('Супер-админ не найден')
