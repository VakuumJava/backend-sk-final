"""
Представления для работы с нагрузкой мастеров и расписанием
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from collections import defaultdict

from .models import CustomUser, Order


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_workload(request, master_id):
    """
    Получить информацию о нагрузке конкретного мастера (на основе слотов)
    """
    from .models import OrderSlot, MasterDailySchedule
    from datetime import date
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Проверка прав доступа: мастер может видеть только свою нагрузку, 
    # куратор и супер-админ могут видеть нагрузку любого мастера
    user = request.user
    if user.role in ['master', 'garant-master', 'warrant-master'] and user.id != master_id:
        return Response({
            'error': 'Недостаточно прав. Мастер может видеть только свою нагрузку.',
            'user_role': user.role
        }, status=status.HTTP_403_FORBIDDEN)
    elif user.role not in ['master', 'garant-master', 'warrant-master', 'curator', 'super-admin']:
        return Response({
            'error': 'Недостаточно прав. Требуется одна из ролей: master, garant-master, warrant-master (для себя), curator, super-admin',
            'user_role': user.role
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Получаем дату для расчета (по умолчанию сегодня)
    target_date_str = request.GET.get('date')
    if target_date_str:
        try:
            from datetime import datetime
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # Получаем расписание дня мастера
    daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, target_date)
    
    # Подсчитываем занятые слоты через OrderSlot
    occupied_slots = OrderSlot.objects.filter(
        master=master,
        slot_date=target_date,
        status__in=['reserved', 'confirmed', 'in_progress']
    ).count()
    
    # Получаем свободные слоты
    free_slots = daily_schedule.get_free_slots_count()
    total_slots = daily_schedule.max_slots
    
    workload_data = {
        'master_id': master.id,
        'master_name': master.get_full_name() if hasattr(master, 'get_full_name') else master.email,
        'date': target_date.strftime('%Y-%m-%d'),
        'total_slots': total_slots,
        'occupied_slots': occupied_slots,
        'free_slots': free_slots,
        'workload_percentage': round((occupied_slots / total_slots) * 100, 1) if total_slots > 0 else 0,
        'work_start_time': daily_schedule.work_start_time.strftime('%H:%M'),
        'work_end_time': daily_schedule.work_end_time.strftime('%H:%M'),
        'is_working_day': daily_schedule.is_working_day,
        'schedule': []  # TODO: добавить детальное расписание если нужно
    }
    
    return Response(workload_data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_masters_workload(request):
    """
    Получить информацию о нагрузке всех мастеров
    """
    masters = CustomUser.objects.filter(
        role__in=['master', 'garant-master', 'warrant-master'], 
        is_active=True
    )
    workload_data = []
    
    for master in masters:
        # Подсчитываем активные заказы
        assigned_orders = Order.objects.filter(
            assigned_master=master,
            status__in=['назначен', 'выполняется']
        ).count()
        
        # Получаем настройки мастера
        max_orders_per_day = getattr(master, 'max_orders_per_day', 8)
        
        master_workload = {
            'master_id': master.id,
            'master_name': master.get_full_name() or master.email,
            'total_slots': max_orders_per_day,
            'occupied_slots': assigned_orders,
            'free_slots': max(0, max_orders_per_day - assigned_orders),
            'workload_percentage': round((assigned_orders / max_orders_per_day) * 100, 1) if max_orders_per_day > 0 else 0
        }
        
        workload_data.append(master_workload)
    
    # Сортируем по нагрузке
    workload_data.sort(key=lambda x: x['workload_percentage'])
    
    return Response(workload_data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_availability(request, master_id):
    """
    Проверить доступность мастера для новых заказов
    """
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Подсчитываем текущие заказы
    current_orders = Order.objects.filter(
        assigned_master=master,
        status__in=['назначен', 'выполняется']
    ).count()
    
    max_orders = getattr(master, 'max_orders_per_day', 8)
    is_available = current_orders < max_orders
    
    return Response({
        'master_id': master.id,
        'is_available': is_available,
        'current_orders': current_orders,
        'max_orders': max_orders,
        'free_slots': max(0, max_orders - current_orders)
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_best_available_master(request):
    """
    Получить лучшего доступного мастера для назначения заказа
    """
    masters = CustomUser.objects.filter(
        role__in=['master', 'garant-master', 'warrant-master'], 
        is_active=True
    )
    available_masters = []
    
    for master in masters:
        current_orders = Order.objects.filter(
            assigned_master=master,
            status__in=['назначен', 'выполняется']
        ).count()
        
        max_orders = getattr(master, 'max_orders_per_day', 8)
        
        if current_orders < max_orders:
            workload_percentage = (current_orders / max_orders) * 100 if max_orders > 0 else 0
            available_masters.append({
                'master_id': master.id,
                'master_name': master.get_full_name() or master.email,
                'workload_percentage': workload_percentage,
                'free_slots': max_orders - current_orders
            })
    
    if not available_masters:
        return Response({'error': 'No available masters'}, status=status.HTTP_404_NOT_FOUND)
    
    # Сортируем по нагрузке (наименее загруженный первый)
    available_masters.sort(key=lambda x: x['workload_percentage'])
    best_master = available_masters[0]
    
    return Response(best_master)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def assign_order_with_workload_check(request, order_id):
    """
    Назначить заказ мастеру с проверкой нагрузки и автоматическим назначением слота
    """
    from .models import OrderSlot, MasterDailySchedule
    from datetime import date
    
    print(f"🎯 assign_order_with_workload_check: order_id={order_id}")
    print(f"   request.user: {request.user} (ID: {request.user.id if request.user.is_authenticated else 'не авторизован'})")
    print(f"   request.data: {request.data}")
    
    try:
        order = Order.objects.get(id=order_id)
        print(f"   ✅ Заказ найден: {order.client_name} (статус: {order.status})")
    except Order.DoesNotExist:
        print("   ❌ Заказ не найден")
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    master_id = request.data.get('master_id')
    slot_date_str = request.data.get('slot_date')  # Опциональная дата слота
    
    print(f"   master_id из запроса: {master_id}")
    print(f"   slot_date из запроса: {slot_date_str}")
    
    if not master_id:
        return Response({'error': 'master_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
        print(f"   ✅ Мастер найден: {master.get_full_name() if hasattr(master, 'get_full_name') else master.email} (ID: {master.id})")
    except CustomUser.DoesNotExist:
        print(f"   ❌ Мастер с ID {master_id} не найден")
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Определяем дату для слота
    if slot_date_str:
        try:
            from datetime import datetime
            slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid slot_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        slot_date = date.today()
    
    print(f"   📅 Дата слота: {slot_date}")
    
    # Получаем расписание дня мастера
    daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, slot_date)
    print(f"   � Расписание дня: {daily_schedule.max_slots} слотов")
    
    # Проверяем доступность слотов
    available_slots = OrderSlot.get_available_slots_for_master(master, slot_date)
    print(f"   🆓 Доступные слоты: {available_slots}")
    
    if not available_slots:
        print(f"   ❌ Нет свободных слотов на {slot_date}!")
        return Response({
            'error': f'У мастера нет свободных слотов на {slot_date}',
            'available_slots': available_slots,
            'max_slots': daily_schedule.max_slots
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем, что заказ еще не назначен на слот
    if hasattr(order, 'slot') and order.slot:
        print(f"   ⚠️ Заказ уже назначен на слот {order.slot.slot_number}")
        return Response({
            'error': f'Order is already assigned to slot {order.slot.slot_number}',
            'existing_slot': {
                'slot_number': order.slot.slot_number,
                'slot_date': order.slot.slot_date.strftime('%Y-%m-%d'),
                'slot_time': order.slot.slot_time.strftime('%H:%M')
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Берем первый доступный слот
    slot_number = available_slots[0]
    print(f"   🎯 Назначаем на слот номер: {slot_number}")
    
    # Вычисляем время слота
    from datetime import datetime, timedelta
    start_datetime = datetime.combine(slot_date, daily_schedule.work_start_time)
    slot_datetime = start_datetime + (daily_schedule.slot_duration * (slot_number - 1))
    slot_time = slot_datetime.time()
    
    print(f"   ⏰ Время слота: {slot_time}")
    
    try:
        # Создаем слот и назначаем заказ в транзакции
        from django.db import transaction
        with transaction.atomic():
            order_slot = OrderSlot.create_slot_for_order(
                order=order,
                master=master,
                slot_date=slot_date,
                slot_number=slot_number,
                slot_time=slot_time
            )
            
            # Обновляем статус заказа
            order.assigned_master = master
            order.status = 'назначен'
            order.save()
            
        print(f"   ✅ Заказ #{order.id} назначен мастеру {master.get_full_name() if hasattr(master, 'get_full_name') else master.email} на слот {slot_number}")
        
        # Подсчитываем оставшиеся слоты
        remaining_slots = len(OrderSlot.get_available_slots_for_master(master, slot_date))
        
        return Response({
            'message': 'Order assigned successfully',
            'order_id': order.id,
            'master_id': master.id,
            'slot': {
                'slot_number': order_slot.slot_number,
                'slot_date': order_slot.slot_date.strftime('%Y-%m-%d'),
                'slot_time': order_slot.slot_time.strftime('%H:%M'),
                'end_time': order_slot.get_end_time().strftime('%H:%M'),
                'display_name': order_slot.get_slot_display_name()
            },
            'remaining_slots': remaining_slots
        })
        
    except Exception as e:
        print(f"   ❌ Ошибка при создании слота: {str(e)}")
        return Response({'error': f'Failed to create slot: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
