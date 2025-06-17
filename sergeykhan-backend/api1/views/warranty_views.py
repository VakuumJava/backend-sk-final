"""
API представления для гарантийных мастеров
"""
from .utils import *


# ----------------------------------------
#  Гарантийные мастера
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
        new_value=f'Статус: одобрен'
    )

    # Начисляем выплату гарантийному мастеру если есть расходы
    if order.expenses > 0:
        master = order.transferred_to
        if master:
            balance, _ = Balance.objects.get_or_create(user=master, defaults={'amount': 0})
            old_balance = balance.amount
            balance.amount += order.expenses
            balance.save()

            # Логируем пополнение баланса
            BalanceLog.objects.create(
                user=master,
                action='top_up',
                amount=order.expenses,
                reason=f'Выплата за гарантийный заказ #{order.id}'
            )

            log_transaction(
                user=master,
                transaction_type='warranty_payment',
                amount=order.expenses,
                description=f'Выплата гарантийному мастеру за заказ #{order.id}. Баланс: {old_balance} → {balance.amount}',
                order=order,
                performed_by=request.user
            )

    return Response({
        'message': 'Warranty order approved and master paid',
        'order_id': order.id,
        'expenses': float(order.expenses)
    }, status=status.HTTP_200_OK)


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


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def complete_transferred_order(request, order_id):
    """Завершение переданного заказа"""
    try:
        order = Order.objects.get(id=order_id, transferred_to=request.user, status__in=['передан на гарантию', 'выполняется'])
        
        # Простая логика завершения
        order.status = 'завершен гарантийным'
        order.final_cost = request.data.get('final_cost', order.estimated_cost)
        order.expenses = request.data.get('expenses', 0)
        order.save()
        
        # Логируем завершение
        log_order_action(
            order=order,
            action='completed_transferred',
            performed_by=request.user,
            description=f'Переданный заказ #{order.id} завершен гарантийным мастером',
            old_value='передан на гарантию',
            new_value='завершен гарантийным'
        )
        
        return Response({
            'message': 'Transferred order completed successfully',
            'order_id': order.id
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or access denied'}, status=status.HTTP_404_NOT_FOUND)
