#!/usr/bin/env python
"""
Скрипт для исправления роли существующего суперпользователя
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

def fix_superuser_role():
    User = get_user_model()
    
    email = 'admin@sergeykhan.com'
    
    try:
        user = User.objects.get(email=email)
        old_role = user.role
        user.role = 'super-admin'
        user.save()
        
        print(f'Пользователь {email} найден!')
        print(f'Старая роль: {old_role}')
        print(f'Новая роль: {user.role}')
        print('Роль успешно обновлена!')
        
    except User.DoesNotExist:
        print(f'Пользователь с email {email} не найден!')
        print('Создайте суперпользователя сначала.')

if __name__ == '__main__':
    fix_superuser_role()
