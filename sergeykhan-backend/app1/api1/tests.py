# Minimal test file to verify distance system functionality
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
    calculate_average_check, 
    calculate_daily_revenue, 
    calculate_net_turnover,
    check_distance_level,
    update_master_distance_status,
    get_visible_orders_for_master
)

User = get_user_model()


class DistanceSystemMinimalTestCase(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = Client()
        
        # Создаём тестового админа
        self.admin_user = CustomUser.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='super-admin'
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

    def create_test_orders(self, master, count=5, cost=50000):
        """Создаёт тестовые заказы для мастера"""
        orders = []
        for i in range(count):
            # Create order without created_at first (due to auto_now_add=True constraint)
            order = Order.objects.create(
                client_name=f'Client {i+1}',
                client_phone=f'+7700000000{i}',
                description=f'Test order {i+1}',
                status='завершен',
                assigned_master=master,
                final_cost=Decimal(str(cost)),
                expenses=Decimal('1000')
            )
            # Then manually update created_at to backdate the order
            order_time = timezone.now() - timedelta(days=i)
            Order.objects.filter(id=order.id).update(created_at=order_time)
            # Refresh the object to get updated created_at
            order.refresh_from_db()
            orders.append(order)
        return orders

    def test_distance_settings_endpoint(self):
        """Тестирует эндпоинт настроек дистанционки"""
        response = self.client.get(
            reverse('get_distance_settings'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('averageCheckThreshold', data)
        self.assertIn('visiblePeriodStandard', data)

    def test_calculate_average_check(self):
        """Тестирует расчёт среднего чека"""
        # Создаём заказы с разной стоимостью
        Order.objects.create(
            client_name='Client 1',
            client_phone='+77000000001',
            description='Order 1',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('100000'),
            expenses=Decimal('1000')
        )
        Order.objects.create(
            client_name='Client 2',
            client_phone='+77000000002',
            description='Order 2',
            status='завершен',
            assigned_master=self.master_user,
            final_cost=Decimal('50000'),
            expenses=Decimal('1000')
        )
        
        avg_check = calculate_average_check(self.master_user.id)
        expected_avg = (100000 + 50000) / 2
        self.assertEqual(float(avg_check), expected_avg)

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
            reverse('get_master_distance_info', kwargs={'master_id': self.master_user.id}),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
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
        response = self.client.get(
            reverse('get_all_masters_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIsInstance(data, list)
        # Должен быть как минимум наш тестовый мастер
        self.assertGreater(len(data), 0)
        
        for master_info in data:
            self.assertIn('master_id', master_info)
            self.assertIn('master_email', master_info)
            self.assertIn('distance_level', master_info)

    def test_force_update_masters_distance(self):
        """Тестирует принудительное обновление статусов дистанционки"""
        response = self.client.post(
            reverse('force_update_all_masters_distance'),
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('message', data)
        self.assertIn('updated_masters', data)

    def test_master_available_orders_with_distance(self):
        """Тестирует получение доступных заказов с учётом дистанционки"""
        # Создаём новые заказы
        order = Order.objects.create(
            client_name='Available Client',
            client_phone='+77000000123',
            description='Available order',
            status='новый'
        )
        
        response = self.client.get(
            reverse('get_master_available_orders_with_distance'),
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertIn('orders', data)
        self.assertIn('distance_info', data)
        self.assertIsInstance(data['orders'], list)

    def test_get_all_masters_distance_detailed(self):
        """Тест получения детальной информации по всем мастерам"""
        # Создаём заказы для мастера
        self.create_test_orders(self.master_user, count=3, cost=70000)
        
        # Обновляем статус дистанционки мастера
        update_master_distance_status(self.master_user.id)
        
        url = reverse('get_all_masters_distance')
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)  # Только один мастер
        
        master_data = data[0]
        
        # Проверяем обязательные поля
        self.assertIn('master_id', master_data)
        self.assertIn('master_email', master_data)
        self.assertIn('distance_level', master_data)
        self.assertIn('distance_level_name', master_data)
        self.assertIn('statistics', master_data)
        self.assertIn('thresholds', master_data)
        self.assertIn('meets_requirements', master_data)
        
        # Проверяем структуру statistics
        stats = master_data['statistics']
        self.assertIn('average_check', stats)
        self.assertIn('daily_revenue', stats)
        self.assertIn('net_turnover_10_days', stats)
        
        # Проверяем структуру meets_requirements
        requirements = master_data['meets_requirements']
        self.assertIn('standard_distance', requirements)
        self.assertIn('daily_distance_by_revenue', requirements)
        self.assertIn('daily_distance_by_turnover', requirements)
        
        # Проверяем, что все поля имеют правильные типы
        self.assertEqual(master_data['master_id'], self.master_user.id)
        self.assertEqual(master_data['master_email'], self.master_user.email)
        self.assertIsInstance(master_data['distance_level'], int)
        self.assertIsInstance(master_data['distance_level_name'], str)
        self.assertIsInstance(stats['average_check'], (int, float))
        self.assertIsInstance(stats['daily_revenue'], (int, float))
        self.assertIsInstance(stats['net_turnover_10_days'], (int, float))
        self.assertIsInstance(requirements['standard_distance'], bool)
        self.assertIsInstance(requirements['daily_distance_by_revenue'], bool)
        self.assertIsInstance(requirements['daily_distance_by_turnover'], bool)

    def test_manual_distance_setting(self):
        """Тест ручного назначения уровня дистанционки"""
        url = reverse('set_master_distance_manually', args=[self.master_user.id])
        data = {'distance_level': 2}
        
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.admin_token.key}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что уровень дистанционки изменился
        self.master_user.refresh_from_db()
        self.assertEqual(self.master_user.dist, 2)

    def test_master_distance_with_orders(self):
        """Тест получения информации о дистанционке мастера с заказами"""
        # Создаём тестовые заказы
        self.create_test_orders(self.master_user, count=2, cost=60000)
        
        # Создаём новые заказы, доступные для назначения
        Order.objects.create(
            client_name='Test Client 1',
            client_phone='+77777777771',
            description='Test Order 1',
            status='новый',
            created_at=timezone.now()
        )
        Order.objects.create(
            client_name='Test Client 2', 
            client_phone='+77777777772',
            description='Test Order 2',
            status='новый',
            created_at=timezone.now()
        )
        
        url = reverse('get_master_distance_with_orders')
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        # Проверяем структуру ответа
        self.assertIn('distance_info', data)
        self.assertIn('orders', data)
        self.assertIn('total_orders', data)
        
        # Проверяем distance_info
        distance_info = data['distance_info']
        self.assertIn('distance_level', distance_info)
        self.assertIn('distance_level_name', distance_info)
        self.assertIn('visibility_hours', distance_info)
        self.assertIn('statistics', distance_info)
        self.assertIn('thresholds', distance_info)
        self.assertIn('meets_requirements', distance_info)
        
        # Проверяем meets_requirements для мастера (должно быть level_1 и level_2)
        requirements = distance_info['meets_requirements']
        self.assertIn('level_1', requirements)
        self.assertIn('level_2', requirements)
        
        # Проверяем, что есть заказы
        self.assertIsInstance(data['orders'], list)
        self.assertIsInstance(data['total_orders'], int)
        self.assertEqual(data['total_orders'], len(data['orders']))

    def test_take_order_functionality(self):
        """Тест функции взятия заказа мастером"""
        # Создаём новый заказ
        order = Order.objects.create(
            client_name='Test Client',
            client_phone='+77777777777',
            description='Test Order for Taking',
            status='в обработке',  # Orders must be 'в обработке' to be assignable
            created_at=timezone.now()
        )
        
        url = reverse('assign', args=[order.id])
        data = {'assigned_master': self.master_user.id}
        
        response = self.client.patch(
            url,
            json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.master_token.key}'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что заказ был назначен мастеру
        order.refresh_from_db()
        self.assertEqual(order.assigned_master, self.master_user)
        self.assertEqual(order.status, 'назначен')
        self.assertEqual(order.curator, self.master_user)  # Master acts as curator when taking order themselves
