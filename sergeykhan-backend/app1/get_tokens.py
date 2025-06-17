#!/usr/bin/env python3
import os
import django

# Устанавливаем переменную окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from rest_framework.authtoken.models import Token

# Получаем полные токены
tokens = Token.objects.all()
print('Full tokens:')
for t in tokens:
    print(f'  {t.key} -> {t.user.email} ({t.user.role})')
