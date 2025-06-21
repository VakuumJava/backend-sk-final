# 📡 API ENDPOINTS ДОКУМЕНТАЦИЯ

## 🌐 Base URL:
`https://backend-sk-final-production.up.railway.app`

## 🔓 Публичные endpoints (без авторизации):

### Services:
```
GET /public/services/
```
**Описание**: Получить список всех сервисов
**URL**: `https://backend-sk-final-production.up.railway.app/public/services/`

### Settings:
```
GET /public/settings/
```
**Описание**: Получить публичные настройки
**URL**: `https://backend-sk-final-production.up.railway.app/public/settings/`

### Feedback:
```
POST /public/feedback/
```
**Описание**: Создать запрос обратной связи
**URL**: `https://backend-sk-final-production.up.railway.app/public/feedback/`

## 🔐 Требующие авторизации:

### Админка:
```
/admin/
```
**URL**: `https://backend-sk-final-production.up.railway.app/admin/`

## ❌ ЧАСТЫЕ ОШИБКИ:

### 1. 404 Not Found на `/api/v1/services/`
**Проблема**: Неправильный URL
**Решение**: Используйте `/public/services/` вместо `/api/v1/services/`

### 2. CORS Error
**Проблема**: Домен не разрешен в Django
**Решение**: Добавьте в Railway Environment Variables:
```
CORS_ALLOWED_ORIGINS=https://sergey-khan-web-gamma.vercel.app,https://backend-sk-final-production.up.railway.app
```

### 3. 403 Forbidden
**Проблема**: Нет токена авторизации для защищенных endpoints
**Решение**: Добавьте токен в заголовки запроса

## 🔧 Тестирование API:

### Curl пример:
```bash
curl -X GET "https://backend-sk-final-production.up.railway.app/public/services/" \
     -H "Accept: application/json"
```

### JavaScript пример:
```javascript
fetch('https://backend-sk-final-production.up.railway.app/public/services/')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```
