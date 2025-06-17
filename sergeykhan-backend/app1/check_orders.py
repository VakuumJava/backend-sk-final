#!/usr/bin/env python3
import os
import django

# Устанавливаем переменную окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import Order

# Проверяем заказы
orders = Order.objects.all()
print('All orders:')
for o in orders:
    print(f'  {o.id}: {o.client_name} - {o.status} - assigned_master: {o.assigned_master}')
