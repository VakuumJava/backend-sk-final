from django.core.management.base import BaseCommand
from api1.models import CustomUser


class Command(BaseCommand):
    help = 'Обновляет роли пользователей согласно новой схеме'

    def handle(self, *args, **options):
        """Обновляет роли пользователей согласно новой схеме"""
        
        # Маппинг старых ролей к новым
        role_mapping = {
            'admin': 'super-admin',
            'warranty_master': 'warrant-master',
            # Остальные роли остаются без изменений
            'master': 'master',
            'operator': 'operator',
            'curator': 'curator'
        }
        
        users_updated = 0
        
        self.stdout.write(
            self.style.SUCCESS('Начинаем обновление ролей пользователей...')
        )
        
        for user in CustomUser.objects.all():
            old_role = user.role
            new_role = role_mapping.get(old_role, old_role)
            
            if old_role != new_role:
                user.role = new_role
                user.save()
                users_updated += 1
                self.stdout.write(
                    f"Обновлен пользователь {user.email}: {old_role} -> {new_role}"
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nВсего обновлено пользователей: {users_updated}')
        )
        
        # Выводим статистику по ролям
        self.stdout.write('\nТекущее распределение ролей:')
        for role_key, role_name in CustomUser.ROLE_CHOICES:
            count = CustomUser.objects.filter(role=role_key).count()
            self.stdout.write(f"  {role_name}: {count}")
        
        self.stdout.write(
            self.style.SUCCESS('Обновление завершено!')
        )
