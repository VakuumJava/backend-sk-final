from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta, datetime
from django.db import models
from django.core.exceptions import ValidationError

from decimal import Decimal, InvalidOperation

from .models import Order, CustomUser, Balance, BalanceLog, ProfitDistribution, CalendarEvent, Contact, CompanyBalance, OrderLog, TransactionLog, MasterAvailability, OrderCompletion, FinancialTransaction, CompanyBalanceLog, ProfitDistributionSettings
from .serializers import (
    OrderSerializer,
    CustomUserSerializer,
    BalanceSerializer,
    BalanceLogSerializer, CalendarEventSerializer, ContactSerializer,
    OrderLogSerializer, TransactionLogSerializer, OrderDetailSerializer,
    OrderPublicSerializer, OrderCompletionSerializer, OrderCompletionCreateSerializer,
    OrderCompletionReviewSerializer, FinancialTransactionSerializer, OrderCompletionDistributionSerializer
)
from .middleware import role_required, RolePermission

# Константы ролей
ROLES = {
    'MASTER': 'master',
    'OPERATOR': 'operator', 
    'WARRANT_MASTER': 'warrant-master',
    'SUPER_ADMIN': 'super-admin',
    'CURATOR': 'curator'
}


# ----------------------------------------
#  Вспомогательные функции логирования
# ----------------------------------------

def log_order_action(order, action, performed_by, description, old_value=None, new_value=None):
    """
    Логирует действие с заказом
    """
    OrderLog.objects.create(
        order=order,
        action=action,
        performed_by=performed_by,
        description=description,
        old_value=old_value,
        new_value=new_value
    )

def log_system_action(action, performed_by, description, old_value=None, new_value=None, metadata=None):
    """
    Логирует системное действие (не связанное с конкретным заказом)
    """
    from .models import SystemLog
    SystemLog.objects.create(
        action=action,
        performed_by=performed_by,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata or {}
    )

def log_transaction(user, transaction_type, amount, description, order=None, performed_by=None):
    """
    Логирует финансовую транзакцию
    """
    TransactionLog.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        order=order,
        performed_by=performed_by
    )


# ----------------------------------------
#  Публичные (регистрация/логин/тестовые)
# ----------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
def create_test_order(request):
    serializer = OrderSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.save(is_test=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_new_orders(request):
    orders = Order.objects.filter(status='новый')
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    print(f"DEBUG create_order: Received data: {request.data}")
    
    serializer = OrderSerializer(data=request.data)
    if serializer.is_valid():
        print("DEBUG create_order: Serializer is valid")
        # Check if scheduling information is provided
        scheduled_date = request.data.get('scheduled_date')
        scheduled_time = request.data.get('scheduled_time')
        assigned_master_id = request.data.get('assigned_master')
        
        # If scheduling info is provided, validate it
        if scheduled_date and scheduled_time and assigned_master_id:
            try:
                # Parse date and time
                schedule_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                schedule_time = datetime.strptime(scheduled_time, '%H:%M:%S').time()
                
                # Check if master exists
                master = CustomUser.objects.get(id=assigned_master_id, role='master')
                
                # Check if master has availability at this time
                availability_slots = MasterAvailability.objects.filter(
                    master=master,
                    date=schedule_date,
                    start_time__lte=schedule_time,
                    end_time__gt=schedule_time
                )
                
                if not availability_slots.exists():
                    return Response(
                        {'error': 'Master is not available at the requested time'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if there are conflicting orders
                conflicting_orders = Order.objects.filter(
                    assigned_master=master,
                    scheduled_date=schedule_date,
                    scheduled_time=schedule_time
                )
                
                if conflicting_orders.exists():
                    return Response(
                        {'error': 'Master already has an order scheduled at this time'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            except (ValueError, CustomUser.DoesNotExist):
                return Response(
                    {'error': 'Invalid master, date, or time format'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        order = serializer.save(status='новый', is_test=False)
        
        # Логируем создание заказа
        log_order_action(
            order=order,
            action='created',
            performed_by=None,  # Публичное создание заказа
            description=f'Заказ #{order.id} создан' + (f' с планируемым временем {scheduled_date} {scheduled_time}' if scheduled_date and scheduled_time else ''),
            old_value=None,
            new_value=f'Статус: новый, Описание: {order.description}' + (f', Планируемое время: {scheduled_date} {scheduled_time}' if scheduled_date and scheduled_time else '')
        )
        
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    
    print(f"DEBUG create_order: Serializer errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            }
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    serializer = CustomUserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------
#  Защищённые (для всех аутентифицированных — в том числе admin)
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_token(request):
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_processing_orders(request):
    orders = Order.objects.filter(status='в обработке')
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def assign_master(request, order_id):
    try:
        order = Order.objects.get(id=order_id, status__in=['новый', 'в обработке'])
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or not available for assignment'},
                        status=status.HTTP_404_NOT_FOUND)

    master_id = request.data.get('assigned_master')
    if not master_id:
        return Response({'error': 'Master ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Invalid master ID'}, status=status.HTTP_400_BAD_REQUEST)

    # Сохраняем старые значения для логирования
    old_master = order.assigned_master.email if order.assigned_master else None
    old_status = order.status

    order.assigned_master = master
    order.curator = request.user
    order.status = 'назначен'
    order.save()

    # Логируем назначение мастера
    log_order_action(
        order=order,
        action='master_assigned',
        performed_by=request.user,
        description=f'Мастер {master.email} назначен на заказ #{order.id}',
        old_value=f'Мастер: {old_master}, Статус: {old_status}',
        new_value=f'Мастер: {master.email}, Статус: назначен'
    )

    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_assigned_orders(request):
    orders = Order.objects.filter(assigned_master=request.user)
    # Use OrderDetailSerializer to show full address and details for taken orders
    serializer = OrderDetailSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CustomUserSerializer(user)
    return Response(serializer.data)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # Логируем удаление заказа перед удалением
    log_order_action(
        order=order,
        action='deleted',
        performed_by=request.user,
        description=f'Заказ #{order.id} удален пользователем {request.user.email}',
        old_value=f'Статус: {order.status}, Описание: {order.description}',
        new_value='Заказ удален'
    )

    order.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # Сохраняем старые значения для логирования
    old_values = {
        'status': order.status,
        'description': order.description,
        'estimated_cost': order.estimated_cost,
        'final_cost': order.final_cost,
    }

    serializer = OrderSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        updated_order = serializer.save()
        
        # Создаем описание изменений
        changes = []
        for field, old_value in old_values.items():
            new_value = getattr(updated_order, field)
            if old_value != new_value:
                changes.append(f'{field}: {old_value} → {new_value}')
        
        if changes:
            # Логируем изменения заказа
            log_order_action(
                order=updated_order,
                action='updated',
                performed_by=request.user,
                description=f'Заказ #{order.id} обновлен: {", ".join(changes)}',
                old_value=str(old_values),
                new_value=f'Новые значения: {", ".join(changes)}'
            )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_masters(request):
    masters = CustomUser.objects.filter(role='master')
    serializer = CustomUserSerializer(masters, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_operators(request):
    operators = CustomUser.objects.filter(role='operator')
    serializer = CustomUserSerializer(operators, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_curators(request):
    curators = CustomUser.objects.filter(role='curator')
    serializer = CustomUserSerializer(curators, many=True)
    return Response(serializer.data)


# ----------------------------------------
#  Балансы
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_balance(request, user_id):
    balance_obj, _ = Balance.objects.get_or_create(user_id=user_id, defaults={'amount': 0})
    return Response({'balance': balance_obj.amount})


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def top_up_balance(request, user_id):
    # 1) забираем amount
    amount_raw = request.data.get('amount')
    if amount_raw is None:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

    # 2) приводим к Decimal через str(), ловим ошибки
    try:
        amt = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

    # 3) находим пользователя
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # 4) обновляем баланс
    balance, _ = Balance.objects.get_or_create(user=user, defaults={'amount': 0})
    old_balance = balance.amount
    balance.amount += amt
    balance.save()

    # 5) логируем в BalanceLog
    BalanceLog.objects.create(
        user=user,
        action='top_up',
        amount=amt,
    )

    # 6) логируем в TransactionLog
    log_transaction(
        user=user,
        transaction_type='balance_top_up',
        amount=amt,
        description=f'Пополнение баланса пользователя {user.email} на сумму {amt}. Баланс: {old_balance} → {balance.amount}',
        performed_by=request.user
    )

    return Response({'message': 'Balance topped up'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def deduct_balance(request, user_id):
    amount_raw = request.data.get('amount')
    if amount_raw is None:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amt = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    balance, _ = Balance.objects.get_or_create(user=user, defaults={'amount': 0})
    if balance.amount < amt:
        return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

    balance.amount -= amt
    balance.save()

    BalanceLog.objects.create(
        user=user,
        action='deduct',
        amount=amt,
    )

    return Response({'message': 'Balance deducted'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_balance_logs(request, user_id):
    logs = BalanceLog.objects.filter(user_id=user_id).order_by('-created_at')
    serializer = BalanceLogSerializer(logs, many=True)
    return Response(serializer.data)


#########
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_orders(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders_last_4hours(request):
    time_threshold = timezone.now() - timedelta(hours=4)
    orders = Order.objects.filter(created_at__gte=time_threshold)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders_last_day(request):
    time_threshold = timezone.now() - timedelta(days=1)
    orders = Order.objects.filter(created_at__gte=time_threshold)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_active_orders(request):
    active_statuses = ['в обработке', 'назначен', 'выполняется']
    orders = Order.objects.filter(status__in=active_statuses)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_non_active_orders(request):
    inactive_statuses = ['завершен', 'новый']
    orders = Order.objects.filter(status__in=inactive_statuses)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_available_orders(request):
    """Доступные заказы для мастера с учётом дистанционки"""
    if request.user.role != ROLES['MASTER']:
        return Response({'error': 'Доступ запрещён'}, status=403)
    
    # Импортируем функцию из distancionka.py
    from .distancionka import get_visible_orders_for_master
    
    orders = get_visible_orders_for_master(request.user.id)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)



@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_transferred_orders(request):
    orders = Order.objects.filter(transferred_to=request.user).order_by('-id')
    data = [{
        'id': o.id,
        'description': o.description,
        'final_cost': str(o.final_cost),
        'status': o.status,
        'expenses': str(o.expenses),
        'original_master': o.master.username
    } for o in orders]

    return Response({'orders': data}, status=200)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def complete_transferred_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, transferred_to=request.user, status__in=['передан на гарантию', 'выполняется'])
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or access denied'}, status=404)

    try:
        final_cost = Decimal(str(request.data['final_cost']))
        expenses = Decimal(str(request.data['expenses']))
    except (KeyError, InvalidOperation):
        return Response({'error': 'Invalid cost/expenses'}, status=400)

    # Сохраняем старые значения для логирования
    old_status = order.status
    old_final_cost = order.final_cost
    old_expenses = order.expenses

    order.final_cost = final_cost
    order.expenses = expenses
    order.status = 'завершен гарантийным'
    order.save()

    # Логируем завершение заказа
    log_order_action(
        order=order,
        action='completed',
        performed_by=request.user,
        description=f'Заказ #{order.id} завершен гарантийным мастером {request.user.email}',
        old_value=f'Статус: {old_status}, Стоимость: {old_final_cost}, Расходы: {old_expenses}',
        new_value=f'Статус: завершен гарантийным, Стоимость: {final_cost}, Расходы: {expenses}'
    )

    # Логируем финансовую операцию если есть расходы
    if expenses > 0:
        log_transaction(
            user=request.user,
            transaction_type='master_payment',
            amount=expenses,
            description=f'Расходы гарантийного мастера по заказу #{order.id}',
            order=order,
            performed_by=request.user
        )

    return Response({'message': 'Order marked as completed by warranty master'}, status=200)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def approve_completed_order(request, order_id):
    if request.user.role not in ['admin', 'super-admin', 'curator']:
        return Response({'error': 'Only admin can approve orders'}, status=403)

    try:
        order = Order.objects.get(id=order_id, status__in=['завершен', 'завершен гарантийным'])
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or not completed'}, status=404)

    if not order.final_cost or not order.expenses:
        return Response({'error': 'Order must have final cost and expenses to distribute profit'}, status=400)

    # Сохраняем старый статус для логирования
    old_status = order.status
    order.status = 'одобрен'
    order.save()

    # Логируем одобрение заказа
    log_order_action(
        order=order,
        action='approved',
        performed_by=request.user,
        description=f'Заказ #{order.id} одобрен администратором {request.user.email}',
        old_value=f'Статус: {old_status}',
        new_value='Статус: одобрен'
    )

    # Используем новые настройки ProfitDistributionSettings
    settings = ProfitDistributionSettings.get_settings()
    profit = order.final_cost - order.expenses
    profit = max(profit, 0)

    master = order.transferred_to or order.assigned_master

    # Расчёт долей с использованием актуальных настроек
    master_paid_percent = settings.master_paid_percent
    master_balance_percent = settings.master_balance_percent
    total_master_percent = master_paid_percent + master_balance_percent
    curator_percent = settings.curator_percent
    
    # Мастеру платим по сумме двух процентов (наличные + баланс)
    master_share = profit * Decimal(total_master_percent) / 100
    curator_share = profit * Decimal(curator_percent) / 100 if order.curator else 0
    operator_share = 0  # Оператору процент не выделяется в новых настройках

    # Распределяем выплаты и логируем
    for user, amount, action, role, percent in [
        (master, master_share, 'earn_master', 'мастеру', total_master_percent),
        (order.curator, curator_share, 'earn_curator', 'куратору', curator_percent),
        (order.operator, operator_share, 'earn_operator', 'оператору', 0),
    ]:
        if user and amount > 0:
            balance, _ = Balance.objects.get_or_create(user=user, defaults={'amount': Decimal('0.00')})
            old_balance = balance.amount
            balance.amount += amount
            balance.save()
            
            # Логируем в BalanceLog с динамическим процентом
            BalanceLog.objects.create(
                user=user,
                action_type='top_up',  # Используем обновленное поле action_type вместо устаревшего action
                action=action,  # Для обратной совместимости
                amount=amount,
                reason=f'Выплата {role} за заказ #{order.id} ({percent}%)'
            )
            
            # Логируем в TransactionLog
            log_transaction(
                user=user,
                transaction_type='profit_distribution',
                amount=amount,
                description=f'Выплата {role} за заказ #{order.id} ({percent}%). Баланс: {old_balance} → {balance.amount}',
                order=order,
                performed_by=request.user
            )

    return Response({'message': 'Order approved and earnings distributed'}, status=200)


@api_view(['GET'])
def get_orders_by_master(request, master_id):
    """Get orders by master id"""
    master = CustomUser.objects.get(id=master_id)
    orders = Order.objects.filter(assigned_master=master)
    # Use OrderDetailSerializer to show full address and details for taken orders
    serializer = OrderDetailSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def fine_master(request):
    master_id = request.data.get('master_id')
    amount = Decimal(request.data.get('amount', 0))
    reason = request.data.get('reason', 'Штраф от куратора')

    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Invalid master ID'}, status=400)

    balance, _ = Balance.objects.get_or_create(user=master, defaults={'amount': Decimal('0.00')})
    if balance.amount < amount:
        return Response({'error': 'Insufficient balance'}, status=400)

    old_balance = balance.amount
    balance.amount -= amount
    balance.save()

    # Логируем в BalanceLog
    BalanceLog.objects.create(
        user=master,
        action='fine_by_curator',
        amount=-amount,
        details=f'Fine by curator {request.user.email}: {reason}'
    )

    # Логируем в TransactionLog
    log_transaction(
        user=master,
        transaction_type='balance_deduct',
        amount=amount,
        description=f'Штраф от куратора {request.user.email}: {reason}. Баланс: {old_balance} → {balance.amount}',
        performed_by=request.user
    )

    return Response({'message': f'Master {master_id} fined by {amount}'}, status=200)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['SUPER_ADMIN']])
def profit_distribution(request):
    """API для управления настройками распределения прибыли"""
    settings = ProfitDistributionSettings.get_settings()

    if request.method == 'GET':
        return Response({
            'master_paid_percent': settings.master_paid_percent,
            'master_balance_percent': settings.master_balance_percent,
            'curator_percent': settings.curator_percent,
            'company_percent': settings.company_percent,
            'total_master_percent': settings.total_master_percent,
            'updated_at': settings.updated_at,
            'updated_by': settings.updated_by.email if settings.updated_by else None,
        })

    elif request.method == 'PUT':
        # Сохраняем старые значения для логирования
        old_settings = {
            'master_paid_percent': settings.master_paid_percent,
            'master_balance_percent': settings.master_balance_percent,
            'curator_percent': settings.curator_percent,
            'company_percent': settings.company_percent,
        }
        
        # Обновляем поля
        for field in ['master_paid_percent', 'master_balance_percent', 'curator_percent', 'company_percent']:
            if field in request.data:
                setattr(settings, field, request.data[field])

        # Устанавливаем пользователя, который обновил настройки
        settings.updated_by = request.user

        try:
            # Метод clean() автоматически проверяет валидность процентов
            settings.clean()
            settings.save()
            
            # Создаем детальное описание изменений
            changes = []
            for field, old_value in old_settings.items():
                new_value = getattr(settings, field)
                if old_value != new_value:
                    field_names = {
                        'master_paid_percent': 'Мастеру (выплачено)',
                        'master_balance_percent': 'Мастеру (баланс)',
                        'curator_percent': 'Куратору',
                        'company_percent': 'Компании'
                    }
                    changes.append(f"{field_names[field]}: {old_value}% → {new_value}%")
            
            changes_description = "; ".join(changes) if changes else "Изменений не было"
            
            # Логируем изменение настроек
            log_system_action(
                action='percentage_settings_updated',
                performed_by=request.user,
                description=f'Обновлены настройки распределения прибыли. Изменения: {changes_description}',
                old_value=str(old_settings),
                new_value=str({
                    'master_paid_percent': settings.master_paid_percent,
                    'master_balance_percent': settings.master_balance_percent,
                    'curator_percent': settings.curator_percent,
                    'company_percent': settings.company_percent,
                }),
                metadata={'changes': changes}
            )
            
            return Response({
                'message': 'Настройки распределения прибыли успешно обновлены',
                'settings': {
                    'master_paid_percent': settings.master_paid_percent,
                    'master_balance_percent': settings.master_balance_percent,
                    'curator_percent': settings.curator_percent,
                    'company_percent': settings.company_percent,
                    'total_master_percent': settings.total_master_percent,
                },
                'changes': changes_description
            })
            
        except ValidationError as e:
            return Response({
                'error': 'Ошибка валидации', 
                'details': e.messages if hasattr(e, 'messages') else [str(e)]
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_balance_with_history(request, user_id):
    logs = BalanceLog.objects.filter(user_id=user_id).order_by('created_at')
    balance = Decimal(0)
    history = []

    for log in logs:
        balance += log.amount
        history.append({
            'action': log.action,
            'amount': str(log.amount),
            'balance': str(balance),
            'created_at': log.created_at
        })

    return Response({
        'current_balance': str(balance),
        'history': history
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_events(request):
    """
    GET /mine/
    Returns all events for the authenticated user.
    """
    events = CalendarEvent.objects.filter(master=request.user)
    serializer = CalendarEventSerializer(events, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event(request):
    """
    POST /create/
    Creates a new event. Expects title, start, end, color (optional) in body.
    """
    serializer = CalendarEventSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(master=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_event_time(request, event_id):
    """
    PUT /update/{event_id}/
    Updates start/end of an existing event (used for drag/resize).
    """
    try:
        event = CalendarEvent.objects.get(id=event_id, master=request.user)
    except CalendarEvent.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    data = {}
    if 'start' in request.data:
        data['start'] = request.data['start']
    if 'end' in request.data:
        data['end'] = request.data['end']

    serializer = CalendarEventSerializer(event, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_event(request, event_id):
    """
    DELETE /delete/{event_id}/
    Deletes an event after user confirmation.
    """
    try:
        event = CalendarEvent.objects.get(id=event_id, master=request.user)
    except CalendarEvent.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    event.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def get_all_contacts(request):
    contacts = Contact.objects.all()
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_contact(request):
    serializer = ContactSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_contact(request, contact_id):
    try:
        contact = Contact.objects.get(id=contact_id)
        contact.delete()
        return Response({'detail': 'Удалено успешно'}, status=status.HTTP_204_NO_CONTENT)
    except Contact.DoesNotExist:
        return Response({'detail': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def mark_as_called(request, contact_id):
    try:
        contact = Contact.objects.get(id=contact_id)
        contact.status = 'обзвонен'
        contact.save()
        serializer = ContactSerializer(contact)
        return Response(serializer.data)
    except Contact.DoesNotExist:
        return Response({'detail': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_called_contacts(request):
    contacts = Contact.objects.filter(status='обзвонен')
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_uncalled_contacts(request):
    contacts = Contact.objects.filter(status='не обзвонен')
    serializer = ContactSerializer(contacts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_guaranteed_orders(request, master_id):
    try:
        master = CustomUser.objects.get(id=master_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Мастер не найден'}, status=404)

    orders = Order.objects.filter(transferred_to=master)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_guaranteed_orders(request):
    orders = Order.objects.filter(transferred_to__isnull=False)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_warranty_masters(request):
    warranty_masters = CustomUser.objects.filter(role='warranty_master')
    serializer = CustomUserSerializer(warranty_masters, many=True)
    return Response(serializer.data)



from django.db import transaction


def distribute_profits(order: Order):
    if order.final_cost is None or order.final_cost <= 0:
        raise ValueError("Order must have a valid final cost for distribution.")

    if not order.transferred_to or not order.curator:
        raise ValueError("Order must be assigned to a warranty master and a curator.")

    master = order.transferred_to
    curator = order.curator
    total = order.final_cost

    # Используем индивидуальные настройки мастера или глобальные
    from .models import MasterProfitSettings
    settings = MasterProfitSettings.get_settings_for_master(master)
    
    # Получаем проценты из настроек
    cash_percent = settings['master_paid_percent']
    balance_percent = settings['master_balance_percent']
    curator_percent = settings['curator_percent']
    kassa_percent = settings['company_percent']

    cash_amount = (Decimal(cash_percent) / 100) * total
    balance_amount = (Decimal(balance_percent) / 100) * total
    curator_salary = (Decimal(curator_percent) / 100) * total
    kassa_amount = (Decimal(kassa_percent) / 100) * total

    with transaction.atomic():
        # Update master's balance
        master_balance, _ = Balance.objects.get_or_create(user=master)
        master_balance.amount += balance_amount
        master_balance.save()

        # Log master income с динамическими процентами
        BalanceLog.objects.create(
            user=master, 
            action_type='top_up',
            reason=f"Начисление на баланс ({balance_percent}%)", 
            amount=balance_amount
        )
        BalanceLog.objects.create(
            user=master, 
            action_type='top_up',
            reason=f"Наличные ({cash_percent}%)", 
            amount=cash_amount
        )

        # Log curator salary с динамическими процентами
        BalanceLog.objects.create(
            user=curator, 
            action_type='top_up',
            reason=f"Зарплата за заказ ({curator_percent}%)", 
            amount=curator_salary
        )

        # Update kassa
        kassa = CompanyBalance.get_instance()
        kassa.amount += kassa_amount
        kassa.save()

    return {
        "cash_to_master": round(cash_amount, 2),
        "balance_to_master": round(balance_amount, 2),
        "curator_salary": round(curator_salary, 2),
        "retained_by_company": round(kassa_amount, 2),
        "settings_used": "individual" if settings['is_individual'] else "global",
        "master_total_percent": cash_percent + balance_percent,
        "settings_breakdown": {
            "master_paid_percent": cash_percent,
            "master_balance_percent": balance_percent,
            "curator_percent": curator_percent,
            "company_percent": kassa_percent
        }
    }


@api_view(['POST'])
def distribute_order_profit(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        result = distribute_profits(order)
        return Response({"status": "success", "distribution": result}, status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as ve:
        return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": "Unexpected error", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Эндпоинт для валидации роли пользователя
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validate_user_role(request):
    """Возвращает информацию о роли пользователя"""
    return Response({
        'user_id': request.user.id,
        'email': request.user.email,
        'role': request.user.role,
        'is_valid': True
    })

# Защищенные эндпоинты для панели мастера
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def master_panel_access(request):
    """Доступ к панели мастера - только для мастеров"""
    if request.user.role != ROLES['MASTER']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для мастеров.',
            'user_role': request.user.role,
            'required_role': ROLES['MASTER']
        }, status=403)
    
    return Response({
        'message': 'Добро пожаловать в панель мастера',
        'user_role': request.user.role
    })

# Защищенные эндпоинты для панели куратора
@api_view(['GET']) 
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def curator_panel_access(request):
    """Доступ к панели куратора - только для кураторов"""
    if request.user.role != ROLES['CURATOR']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для кураторов.',
            'user_role': request.user.role,
            'required_role': ROLES['CURATOR']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель куратора',
        'user_role': request.user.role
    })

# Защищенные эндпоинты для панели оператора
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated]) 
def operator_panel_access(request):
    """Доступ к панели оператора - только для операторов"""
    if request.user.role != ROLES['OPERATOR']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для операторов.',
            'user_role': request.user.role,
            'required_role': ROLES['OPERATOR']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель оператора',
        'user_role': request.user.role
    })

# Защищенные эндпоинты для панели гарантийного мастера
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def warrant_master_panel_access(request):
    """Доступ к панели гарантийного мастера - только для гарантийных мастеров"""
    if request.user.role != ROLES['WARRANT_MASTER']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для гарантийных мастеров.',
            'user_role': request.user.role,
            'required_role': ROLES['WARRANT_MASTER']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель гарантийного мастера',
        'user_role': request.user.role
    })

# Защищенные эндпоинты для панели супер-администратора
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def super_admin_panel_access(request):
    """Доступ к панели супер-администратора - только для супер-администраторов"""
    if request.user.role != ROLES['SUPER_ADMIN']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для супер-администраторов.',
            'user_role': request.user.role,
            'required_role': ROLES['SUPER_ADMIN']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель супер-администратора',
        'user_role': request.user.role
    })

# ----------------------------------------
#  Новые эндпоинты для логирования
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_order_logs(request, order_id):
    """
    Получить логи для конкретного заказа
    """
    try:
        order = Order.objects.get(id=order_id)
        logs = OrderLog.objects.filter(order=order).order_by('-created_at')
        serializer = OrderLogSerializer(logs, many=True)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_order_logs(request):
    """
    Получить все логи заказов (с пагинацией)
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit
    
    logs = OrderLog.objects.all().order_by('-created_at')[offset:offset + limit]
    total_count = OrderLog.objects.count()
    
    serializer = OrderLogSerializer(logs, many=True)
    
    return Response({
        'logs': serializer.data,
        'total_count': total_count,
        'page': page,
        'limit': limit,
        'has_next': offset + limit < total_count
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_transaction_logs(request, user_id=None):
    """
    Получить логи транзакций для пользователя или все
    """
    if user_id:
        try:
            user = CustomUser.objects.get(id=user_id)
            logs = TransactionLog.objects.filter(user=user).order_by('-created_at')
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Все логи транзакций (только для администраторов)
        if request.user.role not in ['super-admin', 'admin']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        logs = TransactionLog.objects.all().order_by('-created_at')
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit
    
    paginated_logs = logs[offset:offset + limit]
    total_count = logs.count()
    
    serializer = TransactionLogSerializer(paginated_logs, many=True)
    
    return Response({
        'logs': serializer.data,
        'total_count': total_count,
        'page': page,
        'limit': limit,
        'has_next': offset + limit < total_count
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_order_detail(request, order_id):
    """
    Получить детальную информацию о заказе с email-адресами
    """
    try:
        order = Order.objects.get(id=order_id)
        serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


# ----------------------------------------
#  Улучшенные эндпоинты для гарантийных мастеров
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_warranty_masters(request):
    """
    Получить список всех гарантийных мастеров
    """
    warranty_masters = CustomUser.objects.filter(role='warrant-master')
    serializer = CustomUserSerializer(warranty_masters, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def complete_warranty_order(request, order_id):
    """
    Завершение заказа гарантийным мастером с логированием
    """
    try:
        order = Order.objects.get(id=order_id, transferred_to=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

    try:
        final_cost = Decimal(str(request.data.get('final_cost', 0)))
        expenses = Decimal(str(request.data.get('expenses', 0)))
        completion_notes = request.data.get('completion_notes', '')
    except (InvalidOperation, TypeError):
        return Response({'error': 'Invalid cost/expenses format'}, status=status.HTTP_400_BAD_REQUEST)

    # Сохраняем старые значения
    old_status = order.status
    old_final_cost = order.final_cost
    old_expenses = order.expenses

    # Обновляем заказ
    order.final_cost = final_cost
    order.expenses = expenses
    order.status = 'завершен гарантийным'
    order.save()

    # Логируем завершение
    log_order_action(
        order=order,
        action='completed',
        performed_by=request.user,
        description=f'Заказ #{order.id} завершен гарантийным мастером {request.user.email}. {completion_notes}',
        old_value=f'Статус: {old_status}, Стоимость: {old_final_cost}, Расходы: {old_expenses}',
        new_value=f'Статус: завершен гарантийным, Стоимость: {final_cost}, Расходы: {expenses}'
    )

    # Логируем финансовую операцию если есть расходы
    if expenses > 0:
        log_transaction(
            user=request.user,
            transaction_type='master_payment',
            amount=expenses,
            description=f'Расходы гарантийного мастера по заказу #{order.id}: {completion_notes}',
            order=order,
            performed_by=request.user
        )

    return Response({
        'message': 'Order completed by warranty master',
        'order_id': order.id,
        'final_cost': float(final_cost),
        'expenses': float(expenses)
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def approve_warranty_order(request, order_id):
    """
    Одобрение завершенного гарантийного заказа администратором
    """
    if request.user.role not in ['super-admin', 'admin', 'curator']:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    try:
        order = Order.objects.get(id=order_id, status='завершен гарантийным')
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or not completed by warranty master'}, status=status.HTTP_404_NOT_FOUND)

    old_status = order.status
    order.status = 'одобрен'
    order.save()

    # Логируем одобрение
    log_order_action(
        order=order,
        action='approved',
        performed_by=request.user,
        description=f'Заказ #{order.id} одобрен администратором {request.user.email}',
        old_value=f'Статус: {old_status}',
        new_value='Статус: одобрен'
    )

    # Производим выплату гарантийному мастеру
    if order.transferred_to and order.final_cost:
        warranty_master = order.transferred_to
        payment_amount = order.final_cost * Decimal('0.7')  # 70% от стоимости заказа
        
        # Обновляем баланс
        balance, _ = Balance.objects.get_or_create(user=warranty_master, defaults={'amount': Decimal('0.00')})
        old_balance = balance.amount
        balance.amount += payment_amount
        balance.save()

        # Логируем в BalanceLog
        BalanceLog.objects.create(
            user=warranty_master,
            action='warranty_payment',
            amount=payment_amount,
        )

        # Логируем в TransactionLog
        log_transaction(
            user=warranty_master,
            transaction_type='master_payment',
            amount=payment_amount,
            description=f'Выплата гарантийному мастеру за заказ #{order.id}. Баланс: {old_balance} → {balance.amount}',
            order=order,
            performed_by=request.user
        )

    return Response({
        'message': 'Warranty order approved and payment processed',
        'order_id': order.id
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_warranty_master_stats(request, master_id=None):
    """
    Получить статистику для гарантийного мастера
    """
    if master_id:
        try:
            master = CustomUser.objects.get(id=master_id, role='warrant-master')
        except CustomUser.DoesNotExist:
            return Response({'error': 'Warranty master not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        master = request.user
        if master.role != 'warrant-master':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    # Статистика заказов
    total_orders = Order.objects.filter(transferred_to=master).count()
    completed_orders = Order.objects.filter(transferred_to=master, status__in=['завершен гарантийный', 'одобрен']).count()
    pending_orders = Order.objects.filter(transferred_to=master, status='передан на гарантию').count()
    
    # Финансовая статистика
    total_earnings = TransactionLog.objects.filter(
        user=master,
        transaction_type='master_payment'
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    return Response({
        'master_id': master.id,
        'master_email': master.email,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'completion_rate': round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 2),
        'total_earnings': float(total_earnings)
    })

@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_master(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if order has an assigned master
    if not order.assigned_master:
        return Response({'error': 'No master assigned to this order'}, 
                        status=status.HTTP_400_BAD_REQUEST)

    # Save old values for logging
    old_master = order.assigned_master.email
    old_status = order.status

    # Remove master assignment and set status to 'новый'
    order.assigned_master = None
    order.status = 'новый'
    order.save()

    # Log the action
    log_order_action(
        order=order,
        action='master_removed',
        performed_by=request.user,
        description=f'Мастер {old_master} удален с заказа #{order.id}',
        old_value=f'Мастер: {old_master}, Статус: {old_status}',
        new_value=f'Мастер: None, Статус: новый'
    )

    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_token(request):
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_processing_orders(request):
    orders = Order.objects.filter(status='в обработке')
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_assigned_orders(request):
    orders = Order.objects.filter(assigned_master=request.user)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CustomUserSerializer(user)
    return Response(serializer.data)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # Логируем удаление заказа перед удалением
    log_order_action(
        order=order,
        action='deleted',
        performed_by=request.user,
        description=f'Заказ #{order.id} удален пользователем {request.user.email}',
        old_value=f'Статус: {order.status}, Описание: {order.description}',
        new_value='Заказ удален'
    )

    order.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # Сохраняем старые значения для логирования
    old_values = {
        'status': order.status,
        'description': order.description,
        'estimated_cost': order.estimated_cost,
        'final_cost': order.final_cost,
    }

    serializer = OrderSerializer(order, data=request.data, partial=True)
    if serializer.is_valid():
        updated_order = serializer.save()
        
        # Создаем описание изменений
        changes = []
        for field, old_value in old_values.items():
            new_value = getattr(updated_order, field)
            if old_value != new_value:
                changes.append(f'{field}: {old_value} → {new_value}')
        
        if changes:
            # Логируем изменения заказа
            log_order_action(
                order=updated_order,
                action='updated',
                performed_by=request.user,
                description=f'Заказ #{order.id} обновлен: {", ".join(changes)}',
                old_value=str(old_values),
                new_value=f'Новые значения: {", ".join(changes)}'
            )
        
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_masters(request):
    masters = CustomUser.objects.filter(role='master')
    serializer = CustomUserSerializer(masters, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_operators(request):
    operators = CustomUser.objects.filter(role='operator')
    serializer = CustomUserSerializer(operators, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_curators(request):
    curators = CustomUser.objects.filter(role='curator')
    serializer = CustomUserSerializer(curators, many=True)
    return Response(serializer.data)


# ----------------------------------------
#  Балансы
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_balance(request, user_id):
    balance_obj, _ = Balance.objects.get_or_create(user_id=user_id, defaults={'amount': 0})
    return Response({'balance': balance_obj.amount})


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def top_up_balance(request, user_id):
    # 1) забираем amount
    amount_raw = request.data.get('amount')
    if amount_raw is None:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

    # 2) приводим к Decimal через str(), ловим ошибки
    try:
        amt = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

    # 3) находим пользователя
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # 4) обновляем баланс
    balance, _ = Balance.objects.get_or_create(user=user, defaults={'amount': 0})
    old_balance = balance.amount
    balance.amount += amt
    balance.save()

    # 5) логируем в BalanceLog
    BalanceLog.objects.create(
        user=user,
        action='top_up',
        amount=amt,
    )

    # 6) логируем в TransactionLog
    log_transaction(
        user=user,
        transaction_type='balance_top_up',
        amount=amt,
        description=f'Пополнение баланса пользователя {user.email} на сумму {amt}. Баланс: {old_balance} → {balance.amount}',
        performed_by=request.user
    )

    return Response({'message': 'Balance topped up'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def deduct_balance(request, user_id):
    amount_raw = request.data.get('amount')
    if amount_raw is None:
        return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amt = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    balance, _ = Balance.objects.get_or_create(user=user, defaults={'amount': 0})
    if balance.amount < amt:
        return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

    balance.amount -= amt
    balance.save()

    BalanceLog.objects.create(
        user=user,
        action='deduct',
        amount=amt,
    )

    return Response({'message': 'Balance deducted'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_balance_logs(request, user_id):
    logs = BalanceLog.objects.filter(user_id=user_id).order_by('-created_at')
    serializer = BalanceLogSerializer(logs, many=True)
    return Response(serializer.data)


#########
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_orders(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders_last_4hours(request):
    time_threshold = timezone.now() - timedelta(hours=4)
    orders = Order.objects.filter(created_at__gte=time_threshold)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders_last_day(request):
    time_threshold = timezone.now() - timedelta(days=1)
    orders = Order.objects.filter(created_at__gte=time_threshold)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_active_orders(request):
    active_statuses = ['в обработке', 'назначен', 'выполняется']
    orders = Order.objects.filter(status__in=active_statuses)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_non_active_orders(request):
    inactive_statuses = ['завершен', 'новый']
    orders = Order.objects.filter(status__in=inactive_statuses)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_available_orders(request):
    """Доступные заказы для мастера с учётом дистанционки"""
    if request.user.role != ROLES['MASTER']:
        return Response({'error': 'Доступ запрещён'}, status=403)
    
    # Импортируем функцию из distancionka.py
    from .distancionka import get_visible_orders_for_master
    
    orders = get_visible_orders_for_master(request.user.id)
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders_new(request):
    """
    Получить список заказов со статусом 'новый'
    """
    orders = Order.objects.filter(status='новый').order_by('-created_at')
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


# ----------------------------------------
#  Завершение заказов мастерами
# ----------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['MASTER'], ROLES['SUPER_ADMIN']])
def complete_order(request, order_id):
    """Завершение заказа мастером"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Проверяем, что заказ назначен текущему мастеру (только для роли мастера)
        if request.user.role == ROLES['MASTER'] and order.assigned_master != request.user:
            return Response({
                'error': 'Заказ не назначен вам'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем статус заказа
        if order.status not in ['выполняется', 'назначен']:
            return Response({
                'error': 'Заказ должен быть в статусе "выполняется" или "назначен"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что заказ еще не завершен
        if hasattr(order, 'completion'):
            return Response({
                'error': 'Заказ уже имеет запись о завершении'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Подготавливаем данные
        data = request.data.copy()
        
        # Логирование для отладки
        print(f"DEBUG: Получены данные от фронтенда:")
        print(f"DEBUG: request.data = {request.data}")
        print(f"DEBUG: request.FILES = {request.FILES}")
        
        # Получаем загружаемые фотографии для логирования
        completion_photos = request.FILES.getlist('completion_photos')
        if completion_photos:
            print(f"DEBUG: Найдено {len(completion_photos)} фотографий")
            for i, photo in enumerate(completion_photos):
                print(f"  Фото {i+1}: {photo.name}, размер: {photo.size}, тип: {photo.content_type}")
        else:
            print("DEBUG: Фотографии не найдены")
        
        print(f"DEBUG: Финальные данные для сериализатора: {data}")
        
        # Создаем сериализатор
        serializer = OrderCompletionCreateSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            completion = serializer.save()
            
            # Логируем действие
            log_order_action(
                order=order,
                action='completed_by_master',
                performed_by=request.user,
                description=f'Заказ завершен мастером. Ожидает подтверждения куратора',
                old_value=f'Статус: {order.status}',
                new_value='Статус: ожидает_подтверждения'
            )
            
            return Response(OrderCompletionSerializer(completion).data, status=status.HTTP_201_CREATED)
        
        print(f"DEBUG: Ошибки сериализатора: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Order.DoesNotExist:
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['MASTER']])
def get_master_completions(request):
    """Получение списка завершений заказов мастера"""
    completions = OrderCompletion.objects.filter(master=request.user).order_by('-created_at')
    serializer = OrderCompletionSerializer(completions, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def get_pending_completions(request):
    """Получение списка завершений, ожидающих подтверждения"""
    completions = OrderCompletion.objects.filter(status='ожидает_проверки').order_by('-created_at')
    serializer = OrderCompletionSerializer(completions, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def get_completion_detail(request, completion_id):
    """Получение детальной информации о завершении заказа"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        serializer = OrderCompletionSerializer(completion, context={'request': request})
        return Response(serializer.data)
        
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Запись о завершении не найдена'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def review_completion(request, completion_id):
    """Проверка завершения заказа куратором или супер-админом"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        
        # Проверяем статус
        if completion.status != 'ожидает_проверки':
            return Response({
                'error': 'Завершение уже проверено'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderCompletionReviewSerializer(completion, data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                action = serializer.validated_data.get('action')
                completion = serializer.save()
                
                # Логируем действие
                action_type = 'completion_approved' if completion.status == 'одобрен' else 'completion_rejected'
                log_order_action(
                    order=completion.order,
                    action=action_type,
                    performed_by=request.user,
                    description=f'Завершение заказа {completion.status} куратором',
                    old_value='ожидает_проверки',
                    new_value=completion.status
                )
                
                # Если одобрено, распределяем средства
                result_data = OrderCompletionSerializer(completion).data
                if completion.status == 'одобрен':
                    try:
                        distribution = distribute_completion_funds(completion, request.user)
                        if distribution:
                            result_data.update({
                                'master_payment': distribution.get('master_amount', 0),
                                'curator_payment': distribution.get('curator_amount', 0),
                                'company_payment': distribution.get('company_amount', 0)
                            })
                    except Exception as dist_error:
                        # Если ошибка в распределении средств, возвращаем успешный ответ но с предупреждением
                        result_data['distribution_error'] = f'Ошибка распределения средств: {str(dist_error)}'
                
                return Response(result_data)
                
            except Exception as save_error:
                return Response({
                    'error': 'Ошибка при сохранении завершения',
                    'details': str(save_error)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Запись о завершении не найдена'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Внутренняя ошибка сервера',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def get_completion_distribution(request, completion_id):
    """Просмотр расчета распределения средств"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        distribution = completion.calculate_distribution()
        
        if distribution:
            distribution['net_profit'] = completion.net_profit
            serializer = OrderCompletionDistributionSerializer(distribution)
            return Response(serializer.data)
        else:
            return Response({'error': 'Распределение недоступно'}, status=status.HTTP_400_BAD_REQUEST)
            
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Запись о завершении не найдена'}, status=status.HTTP_404_NOT_FOUND)


def distribute_completion_funds(completion, curator):
    """Распределение средств после одобрения завершения с учетом настроек"""
    if completion.is_distributed:
        return {
            'master_amount': 0,
            'curator_amount': 0,
            'company_amount': 0,
        }
    
    distribution = completion.calculate_distribution()
    if not distribution:
        return {
            'master_amount': 0,
            'curator_amount': 0,
            'company_amount': 0,
        }
    
    try:
        # Ensure all monetary values are Decimal to avoid type errors
        master_immediate = Decimal(str(distribution['master_immediate']))
        master_deferred = Decimal(str(distribution['master_deferred']))
        curator_share = Decimal(str(distribution['curator_share']))
        company_share = Decimal(str(distribution['company_share']))
        
        # Логируем начало распределения
        log_order_action(
            order=completion.order,
            action='distribution_started',
            performed_by=curator,
            description=f'Начало распределения средств: {distribution["settings_used"]} для заказа #{completion.order.id}'
        )
        
        # 1. Выплата мастеру (процент из настроек)
        master_balance, created = Balance.objects.get_or_create(user=completion.master)
        old_master_balance = master_balance.amount
        master_balance.amount += master_immediate
        master_balance.save()
        
        # Логируем транзакцию выплаты мастеру
        FinancialTransaction.objects.create(
            user=completion.master,
            order_completion=completion,
            transaction_type='master_payment',
            amount=master_immediate,
            description=f'Выплата за завершение заказа #{completion.order.id} ({distribution["settings_used"]["cash_percent"]}%)'
        )
        
        # Логируем изменение выплаченного баланса мастера
        BalanceLog.objects.create(
            user=completion.master,
            action_type='top_up',  # Используем правильный action_type
            amount=master_immediate,
            reason=f'Выплата за заказ #{completion.order.id} ({distribution["settings_used"]["cash_percent"]}%)',
            performed_by=curator,
            old_value=old_master_balance,
            new_value=master_balance.paid_amount  # Используем правильное поле
        )
        
        # 2. Отложенная выплата мастеру (процент из настроек)
        FinancialTransaction.objects.create(
            user=completion.master,
            order_completion=completion,
            transaction_type='master_deferred',
            amount=master_deferred,
            description=f'Отложенная выплата за заказ #{completion.order.id} ({distribution["settings_used"]["balance_percent"]}%)'
        )
        
        # 3. Выплата куратору (процент из настроек)
        curator_balance, created = Balance.objects.get_or_create(user=curator)
        old_curator_balance = curator_balance.amount
        curator_balance.amount += curator_share
        curator_balance.save()
        
        FinancialTransaction.objects.create(
            user=curator,
            order_completion=completion,
            transaction_type='curator_payment',
            amount=curator_share,
            description=f'Выплата куратору за одобрение заказа #{completion.order.id} ({distribution["settings_used"]["curator_percent"]}%)'
        )
        
        BalanceLog.objects.create(
            user=curator,
            action_type='top_up',  # Используем правильный action_type
            amount=curator_share,
            reason=f'Выплата за проверку заказа #{completion.order.id} ({distribution["settings_used"]["curator_percent"]}%)',
            performed_by=curator,
            old_value=old_curator_balance,
            new_value=curator_balance.amount
        )
        
        # 4. Доход компании (процент из настроек)
        company_balance = CompanyBalance.objects.first()
        if company_balance:
            old_company_balance = company_balance.amount
            company_balance.amount += company_share
            company_balance.save()
            
            CompanyBalanceLog.objects.create(
                action_type='top_up',  # Используем правильный action_type
                amount=company_share,
                reason=f'Доход от завершения заказа #{completion.order.id} ({distribution["settings_used"]["final_kassa_percent"]}%)',
                performed_by=curator,
                old_value=old_company_balance,
                new_value=company_balance.amount
            )
        
        FinancialTransaction.objects.create(
            user=curator,
            order_completion=completion,
            transaction_type='company_income',
            amount=company_share,
            description=f'Доход компании от заказа #{completion.order.id} ({distribution["settings_used"]["final_kassa_percent"]}%)'
        )
        
        # Отмечаем как распределено
        completion.is_distributed = True
        completion.save()
        
        # Логируем успешное завершение
        log_order_action(
            order=completion.order,
            action='distribution_completed',
            performed_by=curator,
            description=f'Распределение средств завершено: мастер {master_immediate}, куратор {curator_share}, компания {company_share}'
        )
        
        # Возвращаем информацию о распределенных средствах
        return {
            'master_amount': master_immediate,
            'curator_amount': curator_share,
            'company_amount': company_share,
        }
        
    except Exception as e:
        # В случае ошибки логируем
        log_order_action(
            order=completion.order,
            action='distribution_error',
            performed_by=curator,
            description=f'Ошибка распределения средств: {str(e)}'
        )
        raise


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_financial_transactions(request):
    """Получение финансовых транзакций пользователя"""
    transactions = FinancialTransaction.objects.filter(user=request.user).order_by('-created_at')
    serializer = FinancialTransactionSerializer(transactions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['SUPER_ADMIN']])
def get_all_financial_transactions(request):
    """Получение всех финансовых транзакций (только для админа)"""
    transactions = FinancialTransaction.objects.all().order_by('-created_at')
    serializer = FinancialTransactionSerializer(transactions, many=True)
    return Response(serializer.data)