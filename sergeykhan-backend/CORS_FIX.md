# 🚨 БЫСТРОЕ РЕШЕНИЕ ПРОБЛЕМЫ CORS

## Проблема:
Frontend на Vercel (`sergey-khan-web-gamma.vercel.app`) не может подключиться к Backend на Railway из-за CORS ограничений.

## 🎯 Решение (2 минуты):

### Вариант 1: Точные домены
1. Зайдите в Railway Dashboard
2. Выберите ваш проект → Settings → Environment Variables
3. Добавьте эти переменные:

```
CORS_ALLOWED_ORIGINS = http://localhost:3000,https://backend-sk-final-production.up.railway.app,https://sergey-khan-web-gamma.vercel.app

CSRF_TRUSTED_ORIGINS = https://backend-sk-final-production.up.railway.app,https://sergey-khan-web-gamma.vercel.app
```

### Вариант 2: Разрешить все (для тестирования)
```
CORS_ALLOW_ALL_ORIGINS = True
```

4. Нажмите "Redeploy" в Railway

## ✅ После этого:
- CORS ошибки должны исчезнуть
- Frontend сможет подключиться к Backend API
- Админка будет работать без ошибок CSRF

## 🔧 Если нужно изменить домен:
Просто обновите переменную `CORS_ALLOWED_ORIGINS` в Railway, добавив новый домен через запятую.

## ⚠️ Безопасность:
- Уберите `CORS_ALLOW_ALL_ORIGINS=True` перед продакшеном
- Используйте точные домены в `CORS_ALLOWED_ORIGINS`
