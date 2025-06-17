"""
API представления для заказов
"""
from .utils import *
from ..models import MasterAvailability


# ----------------------------------------
#  Публичные API для заказов
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


# ----------------------------------------
#  Защищённые API для заказов
# ----------------------------------------

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
    scheduled_date = request.data.get('scheduled_date')
    scheduled_time = request.data.get('scheduled_time')
    
    if not master_id:
        return Response({'error': 'Master ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Invalid master ID'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем доступность мастера если указана дата и время
    if scheduled_date and scheduled_time:
        try:
            from datetime import datetime
            
            # Парсим дату и время
            schedule_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
            schedule_time = datetime.strptime(scheduled_time, '%H:%M:%S').time()
            
            # Проверяем есть ли у мастера рабочий слот в это время
            availability_slots = MasterAvailability.objects.filter(
                master=master,
                date=schedule_date,
                start_time__lte=schedule_time,
                end_time__gt=schedule_time
            )
            
            if not availability_slots.exists():
                return Response({
                    'error': f'Мастер {master.email} недоступен {scheduled_date} в {scheduled_time}. Выберите другое время из доступных слотов.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Проверяем нет ли уже заказа в это время
            conflicting_orders = Order.objects.filter(
                assigned_master=master,
                scheduled_date=schedule_date,
                scheduled_time=schedule_time
            ).exclude(id=order_id)
            
            if conflicting_orders.exists():
                return Response({
                    'error': f'У мастера {master.email} уже есть заказ на {scheduled_date} в {scheduled_time}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Устанавливаем дату и время заказа
            order.scheduled_date = schedule_date
            order.scheduled_time = schedule_time
            
        except ValueError:
            return Response({'error': 'Invalid date or time format'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Если дата и время не указаны, проверяем есть ли вообще доступные слоты
        from django.utils import timezone
        
        available_slots = MasterAvailability.objects.filter(
            master=master,
            date__gte=timezone.now().date()
        )
        
        if not available_slots.exists():
            return Response({
                'error': f'Мастер {master.email} не имеет доступных рабочих слотов. Создайте расписание для мастера.'
            }, status=status.HTTP_400_BAD_REQUEST)

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
        description=f'Мастер {master.email} назначен на заказ #{order.id}' + 
                   (f' на {scheduled_date} в {scheduled_time}' if scheduled_date and scheduled_time else ''),
        old_value=f'Мастер: {old_master}, Статус: {old_status}',
        new_value=f'Мастер: {master.email}, Статус: назначен' + 
                  (f', Дата: {scheduled_date}, Время: {scheduled_time}' if scheduled_date and scheduled_time else '')
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


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        # Store order details for logging before deletion
        order_description = f'Заказ #{order.id}: {order.description}'
        log_order_action(
            order=order,
            action='deleted',
            performed_by=request.user,
            description=f'Заказ #{order.id} удален',
            old_value=order_description,
            new_value=None
        )
        order.delete()
        return Response({'message': 'Order deleted successfully'}, status=status.HTTP_200_OK)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


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
def get_orders_new(request):
    """
    Получить список заказов со статусом 'новый'
    """
    orders = Order.objects.filter(status='новый').order_by('-created_at')
    serializer = OrderSerializer(orders, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_order_detail(request, order_id):
    """
    Получить детальную информацию о заказе
    """
    try:
        order = Order.objects.get(id=order_id)
        serializer = OrderDetailSerializer(order, context={'request': request})
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


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
    from ..distancionka import get_visible_orders_for_master
    
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
        'original_master': o.assigned_master.email if o.assigned_master else 'Не назначен'
    } for o in orders]

    return Response({'orders': data}, status=200)


@api_view(['GET'])
def get_orders_by_master(request, master_id):
    """Get orders by master id"""
    try:
        master = CustomUser.objects.get(id=master_id)
        orders = Order.objects.filter(assigned_master=master)
        # Use OrderDetailSerializer to show full address and details for taken orders
        serializer = OrderDetailSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
