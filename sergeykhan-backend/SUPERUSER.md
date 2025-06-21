# Суперпользователь Django - Данные для входа

## ✅ АКТУАЛЬНЫЕ данные для Railway деплоя:

### 🌐 URL админки:
**https://backend-sk-final-production.up.railway.app/admin/**

### 🔑 Данные для входа:
- **Email**: `admin@sergeykhan.com`
- **Пароль**: `Admin123!SerKey`

## 🔧 ИСПРАВЛЕНИЕ РОЛИ ПОЛЬЗОВАТЕЛЯ:

Если у пользователя нет правильной роли, выполните:

### Через Railway shell:
```bash
railway shell
```

Затем в shell выполните:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='admin@sergeykhan.com')
print(f'Текущая роль: {user.role}')
user.role = 'super-admin'
user.save()
print(f'Новая роль: {user.role}')
exit()
```

### Доступные роли в системе:
- `'master'` - Мастер
- `'operator'` - Оператор  
- `'warrant-master'` - Гарантийный мастер
- `'super-admin'` - Супер админ ✅
- `'curator'` - Куратор

## Как установить переменные в Railway:

### Через CLI:
```bash
# Подключиться к проекту
railway link

# Установить переменные (используйте одинарные кавычки для избежания проблем с zsh)
railway variables --set 'DJANGO_SUPERUSER_EMAIL=admin@sergeykhan.com'
railway variables --set 'DJANGO_SUPERUSER_PASSWORD=Admin123!SerKey'
railway variables --set 'DJANGO_SUPERUSER_USERNAME=admin'
railway variables --set 'SECRET_KEY=django-secure-key-2025-sergeykhan-production'
railway variables --set 'DEBUG=False'

# Добавить PostgreSQL
railway add --database postgres

# Деплой
railway up
```

### Через Railway Dashboard:
1. Зайти в проект на railway.app
2. Перейти в Settings → Environment Variables
3. Добавить переменные:
   - `DJANGO_SUPERUSER_EMAIL` = `admin@sergeykhan.com`
   - `DJANGO_SUPERUSER_PASSWORD` = `Admin123!SerKey`
   - `DJANGO_SUPERUSER_USERNAME` = `admin`
   - `SECRET_KEY` = `ваш-секретный-ключ`
   - `DEBUG` = `False`

## Автоматическое создание:
Суперпользователь создается автоматически при деплое через `startup.sh` если переменные заданы.

## Ручное создание (если нужно):
```bash
# Подключиться к Railway
railway shell

# Создать суперпользователя
python manage.py createsuperuser
```

## Безопасность:
⚠️ **Смените пароль после первого входа!**
⚠️ **Используйте надежный SECRET_KEY в production**
