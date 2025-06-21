# Суперпользователь Django - Данные для входа

## ✅ АКТУАЛЬНЫЕ данные для Railway деплоя:

### 🌐 URL админки:
**https://backend-sk-final-production.up.railway.app/admin/**

### 🔑 Данные для входа:
- **Email**: `admin@sergeykhan.com`
- **Пароль**: `Admin123!SerKey`

## ⚠️ ПРОБЛЕМА CORS С VERCEL:

Если frontend на Vercel (`sergey-khan-web-gamma.vercel.app`) не может подключиться к backend, добавьте в Railway variables:

### Через Railway Dashboard:
1. Зайдите в Railway project → Settings → Environment Variables
2. Добавьте/обновите переменные:

```bash
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://backend-sk-final-production.up.railway.app,https://sergey-khan-web-gamma.vercel.app
CSRF_TRUSTED_ORIGINS=https://backend-sk-final-production.up.railway.app,https://sergey-khan-web-gamma.vercel.app,https://*.vercel.app
```

3. Перезапустите деплой в Railway

## 🛠️ Альтернативное решение:
Если проблемы с CORS сохраняются, временно можно разрешить все домены (ТОЛЬКО для тестирования):

```bash
CORS_ALLOW_ALL_ORIGINS=True
```

**⚠️ Уберите эту настройку перед продакшеном!**

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
