from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import json

from .models import Order, CustomUser, Balance, BalanceLog
from .distancionka import (
    DistanceSettings, 
    calculate_average_check, 
    calculate_daily_revenue, 
    calculate_net_turnover,
    check_distance_level,
    update_master_distance_status,
    get_visible_orders_for_master
)

User = get_user_model()


class DistanceSystemTestCase(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаём тестового админа
        self.admin_user = CustomUser.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.admin_token = Token.objects.create(user=self.admin_user)
        
        # Создаём тестового мастера
        self.master_user = CustomUser.objects.create_user(
            email='master@test.com',
            password='testpass123',
            role='master'
        )
        self.master_token = Token.objects.create(user=self.master_user)
        
        # Создаём баланс для мастера
        Balance.objects.create(user=self.master_user, amount=Decimal('0.00'))
        
        # Настройки дистанционки по умолчанию
        self.default_settings = DistanceSettings()

    def create_test_orders(self, master, count=5, cost=50000):
        """Создаёт тестовые заказы для мастера"""
        orders = []
        for i in range(count):
            order = Order.objects.create(
                client_name=f'Client {i+1}',
                client_phone=f'+7700000000{i}',
                description=f'Test order {i+1}',
                status='завершен',
                assigned_master=master,
                final_cost=Decimal(str(cost)),
                expenses=Decimal('1000'),
                created_at=timezone.now() - timedelta(days=i)
            )
            orders.append(order)
        return orders

    def test_distance_settings_crud(self):
        """Тестирует CRUD операции с настройками дистанционки"""        # GET - получение настроек
        response = self.client.get(
            reverse('get_distance_settings'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('averageCheckThreshold', data)
        self.assertIn('visiblePeriodStandard', data)
        
        # PUT - обновление настроек        new_settings = {
            'averageCheckThreshold': 75000,
            'visiblePeriodStandard': 6,
            'dailyOrderSumThreshold': 400000,
            'netTurnoverThreshold': 2000000,
            'visiblePeriodDaily': 48
        }
        
        response = self.client.put(
            reverse('update_distance_settings'),
            data=json.dumps(new_settings),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что настройки обновились
        response = self.client.get(
            reverse('get_distance_settings'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        data = response.json()
        self.assertEqual(data['averageCheckThreshold'], 75000)
        self.assertEqual(data['visiblePeriodStandard'], 6)

    def test_calculate_average_check(self):
        """Тестирует расчёт среднего чека"""
        # Создаём заказы с разной стоимостью
        orders = [
            Order.objects.create(
                client_name='Client 1',
                client_phone='+77000000001',
                description='Order 1',
                status='завершен',
                assigned_master=self.master_user,
                final_cost=Decimal('100000'),
                expenses=Decimal('1000')
            ),
            Order.objects.create(
                client_name='Client 2',
                client_phone='+77000000002',
                description='Order 2',
                status='завершен',
                assigned_master=self.master_user,
                final_cost=Decimal('50000'),
                expenses=Decimal('1000')
            )
        ]
        
        avg_check = calculate_average_check(self.master_user.id)
        expected_avg = (100000 + 50000) / 2
        self.assertEqual(float(avg_check), expected_avg)

    def test_calculate_daily_revenue(self):
        """Тестирует расчёт дневной выручки"""
        # Создаём заказ за сегодня
        today_order = Order.objects.create(
            client_name='Today Client',
            client_phone='+77000000001',
            description='Today order',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('200000'),
            expenses=Decimal('1000'),
            created_at=timezone.now()
        )
        
        # Создаём заказ за вчера
        yesterday_order = Order.objects.create(
            client_name='Yesterday Client',
            client_phone='+77000000002',
            description='Yesterday order',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('100000'),
            expenses=Decimal('1000'),
            created_at=timezone.now() - timedelta(days=1)
        )
        
        daily_revenue = calculate_daily_revenue(self.master_user.id)
        self.assertEqual(float(daily_revenue), 200000.0)

    def test_calculate_net_turnover_10_days(self):
        """Тестирует расчёт чистого вала за 10 дней"""
        # Создаём заказы за последние 5 дней
        total_expected = 0
        for i in range(5):
            cost = Decimal('100000')
            expenses = Decimal('10000')
            Order.objects.create(
                client_name=f'Client {i+1}',
                client_phone=f'+7700000000{i}',
                description=f'Order {i+1}',
                status='завершен',
                assigned_master=self.master_user,
                final_cost=cost,
                expenses=expenses,
                created_at=timezone.now() - timedelta(days=i)            )
            total_expected += float(cost - expenses)
        
        net_turnover = calculate_net_turnover(self.master_user.id)
        self.assertEqual(float(net_turnover), total_expected)

    def test_check_distance_level(self):
        """Тестирует определение уровня дистанционки"""
        
        # Тест уровня 0 (нет дистанционки)
        level = check_distance_level(self.master_user.id)
        self.assertEqual(level, 0)
        
        # Создаём заказы для получения стандартной дистанционки
        self.create_test_orders(self.master_user, count=10, cost=70000)
        level = check_distance_level(self.master_user.id)
        self.assertEqual(level, 1)
        
        # Создаём заказы для получения суточной дистанционки
        Order.objects.create(
            client_name='Big Client',
            client_phone='+77000000099',
            description='Big order',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('400000'),
            expenses=Decimal('1000'),
            created_at=timezone.now()
        )
        level = check_distance_level(self.master_user.id)
        self.assertEqual(level, 2)

    def test_master_distance_info_endpoint(self):
        """Тестирует эндпоинт получения информации о дистанционке мастера"""
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('distance_level', data)
        self.assertIn('distance_level_name', data)
        self.assertIn('statistics', data)
        self.assertIn('thresholds', data)
        self.assertIn('meets_requirements', data)

    def test_all_masters_distance_endpoint(self):
        """Тестирует эндпоинт получения дистанционки всех мастеров"""
        # Создаём ещё одного мастера
        master2 = CustomUser.objects.create_user(
            email='master2@test.com',
            password='testpass123',
            role='master'
        )
        Balance.objects.create(user=master2, amount=Decimal('0.00'))
        
        response = self.client.get(
            reverse('all_masters_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)  # Два мастера
        
        for master_info in data:
            self.assertIn('master_id', master_info)
            self.assertIn('master_email', master_info)
            self.assertIn('distance_level', master_info)

    def test_force_update_masters_distance(self):
        """Тестирует принудительное обновление статусов дистанционки"""
        response = self.client.post(
            reverse('force_update_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('updated_masters', data)

    def test_master_available_orders_with_distance(self):
        """Тестирует получение доступных заказов с учётом дистанционки"""
        # Создаём новые заказы
        Order.objects.create(
            client_name='Available Client',
            client_phone='+77000000123',
            description='Available order',
            status='новый',
            created_at=timezone.now() + timedelta(hours=2)
        )
        
        response = self.client.get(
            reverse('master_available_orders_distance'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('orders', data)
        self.assertIn('distance_info', data)
        self.assertIsInstance(data['orders'], list)

    def test_get_visible_orders_for_master(self):
        """Тестирует функцию получения видимых заказов для мастера"""
        # Создаём заказы с разным временем создания
        now = timezone.now()
        
        # Заказ в прошлом (должен быть виден)
        past_order = Order.objects.create(
            client_name='Past Client',
            client_phone='+77000000001',
            description='Past order',
            status='новый',
            created_at=now - timedelta(hours=1)
        )
        
        # Заказ через 2 часа (не должен быть виден без дистанционки)
        future_order = Order.objects.create(
            client_name='Future Client',
            client_phone='+77000000002',
            description='Future order',
            status='новый',
            created_at=now + timedelta(hours=2)
        )
        
        # Заказ через 6 часов (не должен быть виден даже с обычной дистанционкой)
        far_future_order = Order.objects.create(
            client_name='Far Future Client',
            client_phone='+77000000003',
            description='Far future order',
            status='новый',
            created_at=now + timedelta(hours=6)
        )
        
        # Без дистанционки
        visible_orders = get_visible_orders_for_master(self.master_user.id)
        visible_ids = [order.id for order in visible_orders]
        self.assertIn(past_order.id, visible_ids)
        self.assertNotIn(future_order.id, visible_ids)
        self.assertNotIn(far_future_order.id, visible_ids)

    def test_permissions_distance_endpoints(self):
        """Тестирует права доступа к эндпоинтам дистанционки"""
        # Создаём пользователя-оператора
        operator_user = CustomUser.objects.create_user(
            email='operator@test.com',
            password='testpass123',
            role='operator'
        )
        operator_token = Token.objects.create(user=operator_user)
        
        # Тестируем доступ к админским эндпоинтам
        admin_endpoints = [
            'distance_settings',
            'all_masters_distance',
            'force_update_distance'
        ]
        
        for endpoint in admin_endpoints:
            # Доступ с токеном оператора (должен быть запрещён)
            response = self.client.get(
                reverse(endpoint),
                HTTP_AUTHORIZATION=f'Token {operator_token.key}'
            )
            self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])
            
            # Доступ с токеном админа (должен быть разрешён)
            response = self.client.get(
                reverse(endpoint),
                HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
            )
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED])    def test_update_master_distance_status(self):
        """Тестирует обновление статуса дистанционки мастера"""
        # Создаём заказы для получения дистанционки
        self.create_test_orders(self.master_user, count=10, cost=70000)
        
        # Обновляем статус
        result = update_master_distance_status(self.master_user.id)
        self.assertTrue(result)  # Функция должна вернуть True, если статус обновился
        
        # Проверяем, что статус действительно обновился
        self.master_user.refresh_from_db()
        self.assertEqual(self.master_user.dist, 1)

    def test_invalid_requests(self):
        """Тестирует некорректные запросы"""
        # Запрос без авторизации
        response = self.client.get(reverse('distance_settings'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Некорректные данные в настройках
        invalid_settings = {
            'averageCheckThreshold': 'invalid',
            'visiblePeriodStandard': -1
        }
        
        response = self.client.put(
            reverse('distance_settings'),
            data=json.dumps(invalid_settings),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edge_cases(self):
        """Тестирует граничные случаи"""
        # Мастер без заказов
        level = check_distance_level(self.master_user.id)
        self.assertEqual(level, 0)
        
        # Мастер с заказами ровно на пороге
        self.create_test_orders(self.master_user, count=10, cost=65000)
        level = check_distance_level(self.master_user.id)
        self.assertEqual(level, 1)
        
        # Несуществующий мастер
        non_existent_id = 99999
        level = check_distance_level(non_existent_id)
        self.assertEqual(level, 0)


class DistanceIntegrationTestCase(TestCase):
    """Интеграционные тесты для всей системы дистанционки"""
    
    def setUp(self):
        self.client = Client()
        
        # Создаём админа
        self.admin_user = CustomUser.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin'
        )
        self.admin_token = Token.objects.create(user=self.admin_user)
        
        # Создаём мастера
        self.master_user = CustomUser.objects.create_user(
            email='master@test.com',
            password='testpass123',
            role='master'
        )
        self.master_token = Token.objects.create(user=self.master_user)
        Balance.objects.create(user=self.master_user, amount=Decimal('0.00'))

    def test_full_distance_workflow(self):
        """Тестирует полный workflow системы дистанционки"""
        # 1. Проверяем изначальный статус мастера (без дистанционки)
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        self.assertEqual(data['distance_level'], 0)
        
        # 2. Создаём заказы для получения обычной дистанционки
        for i in range(10):
            Order.objects.create(
                client_name=f'Client {i+1}',
                client_phone=f'+7700000000{i}',
                description=f'Order {i+1}',
                status='завершен',
                assigned_master=self.master_user,
                final_cost=Decimal('70000'),
                expenses=Decimal('5000'),
                created_at=timezone.now() - timedelta(days=i)
            )
        
        # 3. Принудительно обновляем статусы
        response = self.client.post(
            reverse('force_update_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Проверяем новый статус мастера (обычная дистанционка)
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        self.assertEqual(data['distance_level'], 1)
        
        # 5. Создаём заказ на большую сумму для получения суточной дистанционки
        Order.objects.create(
            client_name='Big Client',
            client_phone='+77000000099',
            description='Big order',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('400000'),
            expenses=Decimal('10000'),
            created_at=timezone.now()
        )
        
        # 6. Снова обновляем статусы
        response = self.client.post(
            reverse('force_update_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        
        # 7. Проверяем итоговый статус (суточная дистанционка)
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        self.assertEqual(data['distance_level'], 2)
        
        # 8. Проверяем, что мастер видит заказы с учётом дистанционки
        # Создаём заказ через 12 часов
        future_order = Order.objects.create(
            client_name='Future Client',
            client_phone='+77000000100',
            description='Future order',
            status='новый',
            created_at=timezone.now() + timedelta(hours=12)
        )
        
        response = self.client.get(
            reverse('master_available_orders_distance'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        
        # С суточной дистанционкой должен видеть заказ через 12 часов
        order_ids = [order['id'] for order in data['orders']]
        self.assertIn(future_order.id, order_ids)

    def test_settings_update_affects_calculations(self):
        """Тестирует, что изменение настроек влияет на расчёты"""
        # Создаём заказы со средним чеком 60000
        for i in range(10):
            Order.objects.create(
                client_name=f'Client {i+1}',
                client_phone=f'+7700000000{i}',
                description=f'Order {i+1}',
                status='завершен',
                assigned_master=self.master_user,
                final_cost=Decimal('60000'),
                expenses=Decimal('5000'),
                created_at=timezone.now() - timedelta(days=i)
            )
        
        # С настройками по умолчанию (порог 65000) дистанционки нет
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        self.assertEqual(data['distance_level'], 0)
        
        # Изменяем настройки - снижаем порог до 55000
        new_settings = {
            'averageCheckThreshold': 55000,
            'visiblePeriodStandard': 4,
            'dailyOrderSumThreshold': 350000,
            'netTurnoverThreshold': 1500000,
            'visiblePeriodDaily': 24
        }
        
        response = self.client.put(
            reverse('distance_settings'),
            data=json.dumps(new_settings),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Принудительно обновляем статусы
        self.client.post(
            reverse('force_update_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        
        # Теперь должна быть дистанционка
        response = self.client.get(
            reverse('master_distance_info'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        data = response.json()
        self.assertEqual(data['distance_level'], 1)
