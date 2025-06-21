# 🔧 ИСПРАВЛЕНИЕ РОЛИ СУПЕРПОЛЬЗОВАТЕЛЯ

## Проблема:
Пользователь создан с ролью `'admin'`, но в модели доступна только роль `'super-admin'`

## 🎯 Быстрое решение (1 минута):

### 1. Подключитесь к Railway shell:
```bash
railway shell
```

### 2. Выполните команды в Python shell:
```python
from django.contrib.auth import get_user_model
User = get_user_model()

# Найти пользователя
user = User.objects.get(email='admin@sergeykhan.com')
print(f'Текущая роль: {user.role}')

# Исправить роль
user.role = 'super-admin'
user.save()

print(f'Новая роль: {user.role}')
print('Роль успешно обновлена!')

# Выход
exit()
```

### 3. Проверьте админку:
Теперь пользователь должен иметь все права супер-админа.

## ✅ Альтернатива - пересоздать пользователя:

### Удалить старого:
```python
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(email='admin@sergeykhan.com').delete()
```

### Создать нового (с правильной ролью):
```python
User.objects.create_superuser(
    email='admin@sergeykhan.com',
    password='Admin123!SerKey',
    first_name='Admin',
    last_name='User',
    role='super-admin'
)
```

## 📋 Доступные роли:
- `'master'` - Мастер
- `'operator'` - Оператор  
- `'warrant-master'` - Гарантийный мастер
- `'super-admin'` - Супер админ ✅ (нужная роль)
- `'curator'` - Куратор
