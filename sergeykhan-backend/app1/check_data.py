#!/usr/bin/env python3
import os
import django

# Устанавливаем переменную окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import CustomUser, Order
from rest_framework.authtoken.models import Token

# Проверяем пользователей
users = CustomUser.objects.all()
print(f'Users: {users.count()}')
for u in users[:5]:
    print(f'  {u.id}: {u.email} ({u.role})')

# Проверяем токены
tokens = Token.objects.all()
print(f'Tokens: {tokens.count()}')
for t in tokens[:3]:
    print(f'  {t.key[:10]}... -> {t.user.email}')

# Проверяем заказы
orders = Order.objects.all()
print(f'Orders: {orders.count()}')
for o in orders[:3]:
    print(f'  {o.id}: {o.client_name} - {o.status}')
