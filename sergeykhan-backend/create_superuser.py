#!/usr/bin/env python
"""
Скрипт для создания суперпользователя Django
Запускать локально или через Railway shell
"""
import os
import sys
import django

# Добавляем текущую папку в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_settings.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_superuser():
    User = get_user_model()
    
    # Данные по умолчанию
    email = 'admin@sergeykhan.com'
    password = 'Admin123!SerKey'
    
    # Проверяем, существует ли уже суперпользователь
    if User.objects.filter(email=email).exists():
        print(f'Суперпользователь с email {email} уже существует!')
        return
    
    # Создаем суперпользователя
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Admin',
        last_name='User',
        role='admin'
    )
    
    print(f'Суперпользователь создан успешно!')
    print(f'Email: {email}')
    print(f'Пароль: {password}')
    print(f'URL админки: /admin/')

if __name__ == '__main__':
    create_superuser()
