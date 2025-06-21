#!/usr/bin/env python3
import os
import django

# Устанавливаем переменную окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser
from rest_framework.authtoken.models import Token

# Проверяем, есть ли уже пользователь super-admin
try:
    user = CustomUser.objects.get(role='super-admin')
    print(f'Super-admin пользователь уже существует: {user.email}')
except CustomUser.DoesNotExist:
    # Создаем нового super-admin пользователя
    user = CustomUser.objects.create_user(
        email='superadmin@example.com',
        password='admin123',
        role='super-admin',
        first_name='Super',
        last_name='Admin'
    )
    print(f'Создан новый super-admin пользователь: {user.email}')

# Создаем или получаем токен
token, created = Token.objects.get_or_create(user=user)
if created:
    print(f'Создан новый токен: {token.key}')
else:
    print(f'Токен уже существует: {token.key}')

print(f'Используйте этот токен для входа: {token.key}')
