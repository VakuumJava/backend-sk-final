#!/usr/bin/env python3
"""
Скрипт для генерации ссылок для входа в систему с разными аккаунтами
"""

# Информация об аккаунтах для тестирования
ACCOUNTS = {
    'super_admin': {
        'email': 'superadmin@example.com',
        'password': 'super_admin_pass',
        'token': '327c2446fa3e569456c220b7b7cbdb9bcc4ff620',
        'role': 'Супер-администратор'
    },
    'master1': {
        'email': 'master1@test.com',
        'password': 'test123456',
        'token': 'ba187bce15be8dd8db2ebed3aa98f950bdd23003',
        'role': 'Мастер - Алексей Петров (имеет назначенный заказ)'
    },
    'master2': {
        'email': 'master2@test.com', 
        'password': 'test123456',
        'token': '91fb1989349a1ff8995cc6f4232c45bd06bcea8d',
        'role': 'Мастер - Дмитрий Иванов (имеет заказ в работе)'
    },
    'master3': {
        'email': 'master3@test.com',
        'password': 'test123456', 
        'token': 'ccaaf92df6f43b9379c52c1cefc1fb2acaa0dc7d',
        'role': 'Мастер - Сергей Сидоров (свободен)'
    },
    'master4': {
        'email': 'master4@test.com',
        'password': 'test123456',
        'token': '3eb3ec727439f6cb3700d9c89192e9f6c4fbd008', 
        'role': 'Мастер - Андрей Козлов (свободен)'
    },
    'operator1': {
        'email': 'operator1@test.com',
        'password': 'test123456',
        'token': '8b5ae72b7fa6c69db664dd383f1ef7dad8540b08',
        'role': 'Оператор - Мария Операторова'
    },
    'operator2': {
        'email': 'operator2@test.com',
        'password': 'test123456',
        'token': '7036ecdb28db85503159ff0c09be02483d0b998a',
        'role': 'Оператор - Анна Диспетчерова'
    },
    'curator1': {
        'email': 'curator1@test.com',
        'password': 'test123456',
        'token': '8b709c0c68b90ff206c2e4ce2321a9d7f4749df8',
        'role': 'Куратор - Елена Кураторова'
    }
}

def print_accounts_info():
    print("🔐" + "="*80)
    print("🎯 ИНФОРМАЦИЯ ДЛЯ ВХОДА В СИСТЕМУ")
    print("🔐" + "="*80)
    print()
    print("🌐 Фронтенд: http://localhost:3000/")
    print("🔧 Бэкенд API: http://127.0.0.1:8000/")
    print()
    
    for account_id, account in ACCOUNTS.items():
        print(f"👤 {account['role']}")
        print(f"   📧 Email: {account['email']}")
        print(f"   🔒 Пароль: {account['password']}")
        print(f"   🎫 Token: {account['token']}")
        print()
    
    print("=" * 80)
    print("📋 ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ:")
    print("=" * 80)
    print()
    print("1️⃣ ВХОД В СИСТЕМУ:")
    print("   • Откройте http://localhost:3000/login")
    print("   • Введите email и пароль любого из аккаунтов выше")
    print("   • Нажмите 'Войти'")
    print()
    print("2️⃣ СОЗДАНИЕ ЗАКАЗОВ (Супер-админ/Оператор):")
    print("   • Перейдите на http://localhost:3000/orders/create")
    print("   • Заполните форму заказа")
    print("   • Справа видна информация о нагрузке мастеров")
    print("   • Поля ВОЗРАСТ, ПРИОРИТЕТ, СПОСОБ ОПЛАТЫ удалены!")
    print()
    print("3️⃣ ПРОВЕРКА СИСТЕМЫ:")
    print("   • Убедитесь, что информация о мастерах отображается")
    print("   • Попробуйте создать заказ")
    print("   • Проверьте, что все отображается на одной странице")
    print("   • Убедитесь, что нет внутренних вкладок")
    print()
    print("4️⃣ API ТЕСТИРОВАНИЕ:")
    print("   • Используйте токены для прямых запросов к API")
    print("   • Пример: curl -H 'Authorization: Token TOKEN' http://127.0.0.1:8000/api/orders/all/")
    print()
    print("✅ ВСЕ ТЕСТОВЫЕ ДАННЫЕ ГОТОВЫ ДЛЯ ПРОВЕРКИ!")
    print("=" * 80)

def print_curl_examples():
    print("\n🔧" + "="*79)
    print("🎯 ПРИМЕРЫ CURL ЗАПРОСОВ ДЛЯ ТЕСТИРОВАНИЯ API")
    print("🔧" + "="*79)
    print()
    
    token = ACCOUNTS['super_admin']['token']
    
    examples = [
        ("Получить всех пользователей", f"curl -H 'Authorization: Token {token}' http://127.0.0.1:8000/api/user/"),
        ("Получить всех мастеров", f"curl -H 'Authorization: Token {token}' http://127.0.0.1:8000/users/masters/"),
        ("Получить все заказы", f"curl -H 'Authorization: Token {token}' http://127.0.0.1:8000/api/orders/all/"),
        ("Получить нагрузку мастеров", f"curl -H 'Authorization: Token {token}' http://127.0.0.1:8000/api/masters/workload/all/"),
        ("Создать заказ", f"""curl -X POST -H 'Authorization: Token {token}' -H 'Content-Type: application/json' \\
     -d '{{"client_name":"Тест API","client_phone":"+7999999999","description":"API тест","street":"API улица","house_number":"1"}}' \\
     http://127.0.0.1:8000/orders/create/""")
    ]
    
    for i, (description, command) in enumerate(examples, 1):
        print(f"{i}️⃣ {description}:")
        print(f"   {command}")
        print()

if __name__ == "__main__":
    print_accounts_info()
    print_curl_examples()
