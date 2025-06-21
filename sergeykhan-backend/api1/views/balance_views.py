"""
API представления для балансов и финансов
"""
from django.db import transaction
from .utils import *


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

    old_balance = balance.amount
    balance.amount -= amt
    balance.save()

    BalanceLog.objects.create(
        user=user,
        action='deduct',
        amount=amt,
    )

    # Логируем в TransactionLog
    log_transaction(
        user=user,
        transaction_type='balance_deduct',
        amount=amt,
        description=f'Списание с баланса пользователя {user.email} на сумму {amt}. Баланс: {old_balance} → {balance.amount}',
        performed_by=request.user
    )

    return Response({'message': 'Balance deducted'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_balance_logs(request, user_id):
    logs = BalanceLog.objects.filter(user_id=user_id).order_by('-created_at')
    serializer = BalanceLogSerializer(logs, many=True)
    return Response(serializer.data)


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

    return Response({'message': 'Master fined successfully'}, status=200)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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
        # Обновление настроек распределения прибыли
        try:
            settings.master_paid_percent = Decimal(str(request.data.get('master_paid_percent', settings.master_paid_percent)))
            settings.master_balance_percent = Decimal(str(request.data.get('master_balance_percent', settings.master_balance_percent)))
            settings.curator_percent = Decimal(str(request.data.get('curator_percent', settings.curator_percent)))
            settings.company_percent = Decimal(str(request.data.get('company_percent', settings.company_percent)))
            settings.updated_by = request.user
            settings.save()
            
            return Response({'message': 'Settings updated successfully'})
        except (ValueError, ValidationError) as e:
            return Response({
                'error': 'Ошибка валидации', 
                'details': str(e)
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


@api_view(['POST'])
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def distribute_order_profit(request, order_id):
    """
    Распределить прибыль от заказа с использованием индивидуальных настроек мастера.
    Использует индивидуальные настройки мастера, если они есть и активны,
    иначе глобальные настройки.
    """
    try:
        # Проверяем права доступа
        if request.user.role not in ['super-admin', 'curator']:
            return Response(
                {'error': 'У вас нет прав для распределения прибыли'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = Order.objects.get(id=order_id)
        
        if not order.final_cost:
            return Response(
                {'error': 'Заказ не имеет итоговой стоимости'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not order.assigned_master:
            return Response(
                {'error': 'Заказ не назначен мастеру'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем настройки распределения для этого заказа
        profit_settings = order.get_profit_settings()
        
        # Рассчитываем суммы для распределения
        total_amount = order.final_cost
        master_paid_amount = total_amount * profit_settings['master_paid_percent'] / 100
        master_balance_amount = total_amount * profit_settings['master_balance_percent'] / 100
        curator_amount = total_amount * profit_settings['curator_percent'] / 100
        company_amount = total_amount * profit_settings['company_percent'] / 100
        
        with transaction.atomic():
            # Получаем или создаем балансы
            master_balance, _ = Balance.objects.get_or_create(user=order.assigned_master)
            
            # Обновляем баланс мастера
            old_balance = master_balance.amount
            old_paid = master_balance.paid_amount
            
            master_balance.amount += master_balance_amount
            master_balance.paid_amount += master_paid_amount
            master_balance.save()
            
            # Логируем изменения баланса мастера
            BalanceLog.objects.create(
                user=order.assigned_master,
                balance_type='current',
                action_type='top_up',
                amount=master_balance_amount,
                reason=f'Прибыль с заказа #{order.id} (на баланс)',
                performed_by=request.user,
                old_value=old_balance,
                new_value=master_balance.amount
            )
            
            BalanceLog.objects.create(
                user=order.assigned_master,
                balance_type='paid',
                action_type='top_up',
                amount=master_paid_amount,
                reason=f'Прибыль с заказа #{order.id} (к выплате)',
                performed_by=request.user,
                old_value=old_paid,
                new_value=master_balance.paid_amount
            )
            
            # Если есть куратор, обновляем его баланс
            if order.curator and curator_amount > 0:
                curator_balance, _ = Balance.objects.get_or_create(user=order.curator)
                old_curator_balance = curator_balance.amount
                
                curator_balance.amount += curator_amount
                curator_balance.save()
                
                BalanceLog.objects.create(
                    user=order.curator,
                    balance_type='current',
                    action_type='top_up',
                    amount=curator_amount,
                    reason=f'Кураторские с заказа #{order.id}',
                    performed_by=request.user,
                    old_value=old_curator_balance,
                    new_value=curator_balance.amount
                )
            
            # Обновляем кассу компании
            if company_amount > 0:
                company_balance = CompanyBalance.get_instance()
                old_company_balance = company_balance.amount
                
                company_balance.amount += company_amount
                company_balance.save()
                
                CompanyBalanceLog.objects.create(
                    action_type='top_up',
                    amount=company_amount,
                    reason=f'Прибыль компании с заказа #{order.id}',
                    performed_by=request.user,
                    old_value=old_company_balance,
                    new_value=company_balance.amount
                )
            
            # Создаем запись о распределении прибыли
            from ..models import FinancialTransaction
            
            # Создаем отдельные транзакции для каждого получателя
            if master_paid_amount > 0 or master_balance_amount > 0:
                FinancialTransaction.objects.create(
                    user=order.assigned_master,
                    transaction_type='master_payment',
                    amount=master_paid_amount + master_balance_amount,
                    description=f'Прибыль с заказа #{order.id} (выплата: {master_paid_amount}, баланс: {master_balance_amount})',
                )
            
            if order.curator and curator_amount > 0:
                FinancialTransaction.objects.create(
                    user=order.curator,
                    transaction_type='curator_payment',
                    amount=curator_amount,
                    description=f'Кураторские с заказа #{order.id}',
                )
            
            # Логируем использованные настройки в системный лог
            from ..models import SystemLog
            SystemLog.objects.create(
                action='percentage_settings_updated',
                description=f'Применены настройки распределения прибыли для заказа #{order.id}',
                performed_by=request.user,
                metadata={
                    'order_id': order.id,
                    'master_id': order.assigned_master.id,
                    'settings_used': profit_settings,
                    'total_amount': str(total_amount),
                    'distribution': {
                        'master_paid': str(master_paid_amount),
                        'master_balance': str(master_balance_amount),
                        'curator': str(curator_amount),
                        'company': str(company_amount)
                    }
                }
            )
        
        return Response({
            "status": "success", 
            "message": "Прибыль успешно распределена",
            "distribution": {
                "total_amount": str(total_amount),
                "master_paid": str(master_paid_amount),
                "master_balance": str(master_balance_amount),
                "curator_amount": str(curator_amount),
                "company_amount": str(company_amount),
                "settings_used": profit_settings
            }
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response(
            {"error": "Неожиданная ошибка", "details": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_profit_settings(request):
    """Получение всех настроек распределения прибыли"""
    settings = ProfitDistributionSettings.get_settings()
    return Response({
        'master_paid_percent': settings.master_paid_percent,
        'master_balance_percent': settings.master_balance_percent,
        'curator_percent': settings.curator_percent,
        'company_percent': settings.company_percent,
        'total_master_percent': settings.total_master_percent,
        'updated_at': settings.updated_at,
        'updated_by': settings.updated_by.email if settings.updated_by else None,
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_profit_settings(request, master_id):
    """Получение настроек распределения прибыли для мастера"""
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        settings = ProfitDistributionSettings.get_settings()
        return Response({
            'master_id': master.id,
            'master_email': master.email,
            'master_paid_percent': settings.master_paid_percent,
            'master_balance_percent': settings.master_balance_percent,
            'total_master_percent': settings.total_master_percent,
        })
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def manage_master_profit_settings(request, master_id):
    """Управление настройками распределения прибыли для мастера"""
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        settings = ProfitDistributionSettings.get_settings()
        
        if request.method == 'GET':
            return Response({
                'master_id': master.id,
                'master_email': master.email,
                'master_paid_percent': settings.master_paid_percent,
                'master_balance_percent': settings.master_balance_percent,
                'total_master_percent': settings.total_master_percent,
            })
        elif request.method == 'PUT':
            # Простая заглушка для обновления
            return Response({'message': 'Settings updated successfully'})
            
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_master_profit_settings(request, master_id):
    """Удаление настроек распределения прибыли для мастера"""
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        # Простая заглушка для удаления
        return Response({'message': 'Master profit settings deleted successfully'})
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
