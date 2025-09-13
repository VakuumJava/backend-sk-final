"""
API представления для заказов
"""
from .utils import *
from ..models import MasterAvailability, OrderSlot, OrderCompletion
from ..serializers import OrderCompletionCreateSerializer
from django.db import models


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
        master = CustomUser.objects.get(id=master_id, role__in=['master', 'warrant-master'])
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
            
            # Проверяем нет ли уже заказа в это время (для обычных и гарантийных мастеров)
            conflicting_orders = Order.objects.filter(
                models.Q(assigned_master=master) | models.Q(transferred_to=master),
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
    old_transferred_to = order.transferred_to.email if order.transferred_to else None
    old_status = order.status

    # Для гарантийных мастеров используем transferred_to, для обычных мастеров - assigned_master
    if master.role == 'warrant-master':
        order.transferred_to = master
        order.status = 'передан на гарантию'
        # Сбрасываем assigned_master если он был установлен
        order.assigned_master = None
    else:
        order.assigned_master = master
        order.status = 'назначен'
        # Сбрасываем transferred_to если он был установлен
        order.transferred_to = None
    
    order.curator = request.user
    order.save()

    # Создаем OrderSlot если указана дата и время
    if scheduled_date and scheduled_time:
        from datetime import timedelta
        
        # Определяем номер слота в дне (основан на времени начала)
        time_to_slot_number = {
            '09:00:00': 1, '10:00:00': 2, '11:00:00': 3, '12:00:00': 4,
            '13:00:00': 5, '14:00:00': 6, '15:00:00': 7, '16:00:00': 8, 
            '17:00:00': 9, '18:00:00': 10, '19:00:00': 11, '20:00:00': 12
        }
        
        slot_number = time_to_slot_number.get(scheduled_time, 1)
        
        # Создаем или обновляем OrderSlot
        order_slot, created = OrderSlot.objects.get_or_create(
            order=order,
            defaults={
                'master': master,
                'slot_date': schedule_date,
                'slot_time': schedule_time,
                'slot_number': slot_number,
                'slot_duration': timedelta(hours=1),  # 1 час по умолчанию
                'status': 'confirmed',
                'notes': f'Автоматически создан при назначении заказа #{order.id}'
            }
        )
        
        if not created and order_slot.master != master:
            # Обновляем существующий слот если изменился мастер
            order_slot.master = master
            order_slot.slot_date = schedule_date
            order_slot.slot_time = schedule_time
            order_slot.slot_number = slot_number
            order_slot.status = 'confirmed'
            order_slot.save()

    # Логируем назначение мастера
    action_type = 'warranty_transfer' if master.role == 'warrant-master' else 'master_assigned'
    description = f'{"Передан гарантийному мастеру" if master.role == "warrant-master" else "Мастер назначен"} {master.email} на заказ #{order.id}' + \
                 (f' на {scheduled_date} в {scheduled_time}' if scheduled_date and scheduled_time else '')
    
    old_value = f'Мастер: {old_master}, Передан: {old_transferred_to}, Статус: {old_status}'
    new_value = f'Мастер: {order.assigned_master.email if order.assigned_master else None}, ' + \
               f'Передан: {order.transferred_to.email if order.transferred_to else None}, ' + \
               f'Статус: {order.status}' + \
               (f', Дата: {scheduled_date}, Время: {scheduled_time}' if scheduled_date and scheduled_time else '')
    
    log_order_action(
        order=order,
        action=action_type,
        performed_by=request.user,
        description=description,
        old_value=old_value,
        new_value=new_value
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

    # Удаляем связанный OrderSlot если он существует
    try:
        order_slot = OrderSlot.objects.get(order=order)
        order_slot.delete()
    except OrderSlot.DoesNotExist:
        pass  # Слот не существует, ничего не делаем

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
    if request.user.role not in [ROLES['MASTER'], ROLES['WARRANT_MASTER']]:
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


@api_view(['PATCH'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def start_order(request, order_id):
    """Start working on an order (set status to 'выполняется')"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if the order is assigned to the current user (for regular masters) or transferred to them (for warranty masters)
        user_can_start = False
        if request.user.role == 'master' and order.assigned_master == request.user:
            user_can_start = True
        elif request.user.role == 'warrant-master' and order.transferred_to == request.user:
            user_can_start = True
            
        if not user_can_start:
            return Response({
                'error': 'Вы можете начать только свои назначенные/переданные заказы'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if order is in correct status for regular masters or warranty masters
        valid_statuses = ['назначен'] if request.user.role == 'master' else ['передан на гарантию', 'назначен']
        if order.status not in valid_statuses:
            return Response({
                'error': f'Заказ не может быть начат. Текущий статус: {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if master already has an active order
        if request.user.role == 'master':
            active_orders = Order.objects.filter(
                assigned_master=request.user,
                status='выполняется'
            )
        else:  # warrant-master
            active_orders = Order.objects.filter(
                transferred_to=request.user,
                status='выполняется'
            )
        
        if active_orders.exists():
            active_order = active_orders.first()
            return Response({
                'error': f'У вас уже есть активный заказ #{active_order.id} в работе. Завершите его перед началом нового.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start the order
        order.status = 'выполняется'
        order.save()
        
        return Response({
            'message': f'Заказ #{order.id} начат',
            'order_id': order.id,
            'status': order.status
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({
            'error': 'Заказ не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Ошибка при начале заказа: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def complete_order(request, order_id):
    """Complete an order and create OrderCompletion record for curator review"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Check if the order is assigned to the current user (for regular masters) or transferred to them (for warranty masters)
        user_can_complete = False
        if request.user.role == 'master' and order.assigned_master == request.user:
            user_can_complete = True
        elif request.user.role == 'warrant-master' and order.transferred_to == request.user:
            user_can_complete = True
            
        if not user_can_complete:
            return Response({
                'error': 'Вы можете завершить только свои заказы'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if order is in correct status
        if order.status not in ['выполняется', 'назначен', 'в работе']:
            return Response({
                'error': f'Заказ не может быть завершен. Текущий статус: {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if completion already exists
        if hasattr(order, 'completion'):
            return Response({
                'error': 'Заказ уже имеет запись о завершении'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # If POST request with completion data, create OrderCompletion
        if request.method == 'POST':
            print(f"DEBUG: POST completion data received: {request.data}")
            
            # Prepare data for OrderCompletion
            completion_data = request.data.copy()
            completion_data['order'] = order_id
            
            # Create completion using serializer
            serializer = OrderCompletionCreateSerializer(data=completion_data, context={'request': request})
            
            if serializer.is_valid():
                completion = serializer.save()
                
                # Log the action
                log_order_action(
                    order=order,
                    action='completed_by_master',
                    performed_by=request.user,
                    description=f'Заказ завершен мастером. Ожидает подтверждения куратора',
                    old_value=f'Статус: {order.status}',
                    new_value='Статус: ожидает_подтверждения'
                )
                
                # Remove the order slot to free up the time slot
                OrderSlot.objects.filter(order=order).delete()
                
                return Response({
                    'message': f'Заказ #{order.id} завершен и отправлен на проверку',
                    'order_id': order.id,
                    'completion_id': completion.id,
                    'status': order.status
                }, status=status.HTTP_201_CREATED)
            else:
                print(f"DEBUG: Serializer errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # If PATCH request (old behavior), just change status
        elif request.method == 'PATCH':
            order.status = 'завершен'
            order.save()
            
            # Log action
            log_order_action(
                order=order,
                action='order_completed',
                performed_by=request.user,
                description='Заказ завершен (без создания записи о завершении)',
                old_value='в работе',
                new_value='завершен'
            )
            
            # Remove the order slot
            OrderSlot.objects.filter(order=order).delete()
        
        # If GET request, just return order info
        return Response({
            'order_id': order.id,
            'status': order.status,
            'message': 'Используйте POST запрос с данными завершения'
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({
            'error': 'Заказ не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"DEBUG: Error completing order: {str(e)}")
        return Response({
            'error': f'Ошибка при завершении заказа: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def transfer_order_to_warranty_master(request, order_id):
    """Transfer order to warranty master"""
    try:
        # Debug logging
        print(f"Transfer request from user: {request.user.email}, role: {request.user.role}")
        
        # Check if user has permission (should be super admin or curator)
        if request.user.role not in ['super-admin', 'curator']:
            return Response({
                'error': f'Недостаточно прав для выполнения действия. Ваша роль: {request.user.role}'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get the order
        order = Order.objects.get(id=order_id)
        
        # Get warranty master ID and optional slot data from request
        warranty_master_id = request.data.get('warranty_master_id')
        scheduled_date = request.data.get('scheduled_date')
        scheduled_time = request.data.get('scheduled_time')
        
        if not warranty_master_id:
            return Response({
                'error': 'ID гарантийного мастера обязателен'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get warranty master
        try:
            warranty_master = CustomUser.objects.get(
                id=warranty_master_id, 
                role='warrant-master'  # Fixed: only use the correct role name
            )
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Гарантийный мастер не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update order
        old_status = order.status
        order.transferred_to = warranty_master
        order.status = 'передан на гарантию'
        
        # Update slot information if provided
        if scheduled_date and scheduled_time:
            order.scheduled_date = scheduled_date
            order.scheduled_time = scheduled_time
            
            # Try to create or update OrderSlot for warranty master
            try:
                from datetime import datetime, timedelta
                from ..models import OrderSlot, MasterDailySchedule
                
                # Parse date and time
                slot_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                slot_time = datetime.strptime(scheduled_time, '%H:%M').time()
                
                # Check if warranty master has availability at this time
                from ..models import MasterAvailability
                availability_slots = MasterAvailability.objects.filter(
                    master=warranty_master,
                    date=slot_date,
                    start_time__lte=slot_time,
                    end_time__gt=slot_time
                )
                
                if availability_slots.exists():
                    # Get or create OrderSlot
                    daily_schedule = MasterDailySchedule.get_or_create_for_master_date(warranty_master, slot_date)
                    
                    # Find the appropriate slot number for the requested time
                    slot_number = None
                    
                    # Simple slot calculation based on time ranges
                    time_to_slot_map = {
                        # 09:00-11:00 = slot 1
                        (datetime.strptime("09:00", "%H:%M").time(), datetime.strptime("11:00", "%H:%M").time()): 1,
                        # 11:00-13:00 = slot 2  
                        (datetime.strptime("11:00", "%H:%M").time(), datetime.strptime("13:00", "%H:%M").time()): 2,
                        # 13:00-15:00 = slot 3
                        (datetime.strptime("13:00", "%H:%M").time(), datetime.strptime("15:00", "%H:%M").time()): 3,
                        # 15:00-17:00 = slot 4
                        (datetime.strptime("15:00", "%H:%M").time(), datetime.strptime("17:00", "%H:%M").time()): 4,
                        # 17:00-19:00 = slot 5
                        (datetime.strptime("17:00", "%H:%M").time(), datetime.strptime("19:00", "%H:%M").time()): 5,
                        # 19:00-21:00 = slot 6
                        (datetime.strptime("19:00", "%H:%M").time(), datetime.strptime("21:00", "%H:%M").time()): 6,
                    }
                    
                    # Find which slot the requested time falls into
                    for (start_time, end_time), slot_num in time_to_slot_map.items():
                        if start_time <= slot_time < end_time:
                            # Check if this slot is available
                            existing_slots = OrderSlot.objects.filter(
                                master=warranty_master,
                                slot_date=slot_date,
                                slot_number=slot_num
                            )
                            
                            if not existing_slots.exists():
                                slot_number = slot_num
                                break
                    
                    # Fallback to first available slot if time-specific slot not found
                    if slot_number is None:
                        available_slots = OrderSlot.get_available_slots_for_master(warranty_master, slot_date)
                        if available_slots:
                            slot_number = available_slots[0]
                    
                    if slot_number is not None:
                        
                        order_slot, created = OrderSlot.objects.get_or_create(
                            order=order,
                            defaults={
                                'master': warranty_master,
                                'slot_date': slot_date,
                                'slot_time': slot_time,
                                'slot_number': slot_number,
                                'slot_duration': timedelta(hours=1),
                                'status': 'confirmed',
                                'notes': f'Автоматически создан при передаче заказа #{order.id} гарантийному мастеру'
                            }
                        )
                        
                        if not created and order_slot.master != warranty_master:
                            # Update existing slot
                            order_slot.master = warranty_master
                            order_slot.slot_date = slot_date
                            order_slot.slot_time = slot_time
                            order_slot.slot_number = slot_number
                            order_slot.status = 'confirmed'
                            order_slot.save()
                            
                        print(f"✅ Создан/обновлен слот для гарантийного мастера: {slot_date} {slot_time}")
                    else:
                        print(f"⚠️ Нет доступных слотов у гарантийного мастера на {slot_date}")
                else:
                    print(f"⚠️ Гарантийный мастер недоступен в указанное время: {slot_date} {slot_time}")
                    
            except Exception as slot_error:
                print(f"Ошибка создания слота для гарантийного мастера: {slot_error}")
        
        order.save()
        
        # Create log entry
        try:
            from ..models import OrderLog
            OrderLog.objects.create(
                order=order,
                action='transferred',
                performed_by=request.user,
                description=f'Заказ #{order.id} передан на гарантию мастеру {warranty_master.email}',
                old_value=old_status,
                new_value='передан на гарантию'
            )
        except Exception as log_error:
            print(f"Error creating log: {log_error}")
        
        # Apply fine if needed (you can customize this logic)
        fine_applied = None
        if old_status in ['выполняется', 'завершен']:
            # Apply fine to original master if order was already started/completed
            try:
                from decimal import Decimal
                fine_amount = Decimal('5000.00')  # 5000 tenge fine
                if order.assigned_master:
                    order.assigned_master.balance -= fine_amount
                    order.assigned_master.save()
                    fine_applied = str(fine_amount)
                    
                    # Log the fine
                    OrderLog.objects.create(
                        order=order,
                        action='status_changed',
                        performed_by=request.user,
                        description=f'Штраф {fine_amount} ₸ за передачу заказа #{order.id} на гарантию',
                        old_value=str(order.assigned_master.balance + fine_amount),
                        new_value=str(order.assigned_master.balance)
                    )
            except Exception as fine_error:
                print(f"Error applying fine: {fine_error}")
        
        return Response({
            'message': 'Заказ успешно передан гарантийному мастеру',
            'order_id': order.id,
            'warranty_master': warranty_master.email,
            'new_status': order.status,
            'fine_applied': fine_applied
        }, status=status.HTTP_200_OK)
        
    except Order.DoesNotExist:
        return Response({
            'error': 'Заказ не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Ошибка при передаче заказа: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
