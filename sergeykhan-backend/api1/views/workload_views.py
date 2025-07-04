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

from ..models import CustomUser, Order, ROLES
from ..serializers import UserSerializer


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_workload(request, master_id):
    """
    Получить информацию о нагрузке конкретного мастера (включая гарантийных)
    """
    try:
        # Support both regular masters and warranty masters
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Подсчитываем заказы мастера в зависимости от роли
    if master.role == 'warrant-master':
        # For warranty masters, count transferred orders
        assigned_orders = Order.objects.filter(
            transferred_to=master,
            status__in=['передан на гарантию', 'выполняется']
        ).count()
    else:
        # For regular masters, count assigned orders
        assigned_orders = Order.objects.filter(
            assigned_master=master,
            status__in=['назначен', 'выполняется']
        ).count()
    
    # Получаем настройки мастера (или используем базовые)
    max_orders_per_day = getattr(master, 'max_orders_per_day', 8)  # базовое значение
    
    workload_data = {
        'master_id': master.id,
        'master_name': master.get_full_name() or master.email,
        'master_email': master.email,
        'master_role': master.role,
        'total_slots': max_orders_per_day,
        'occupied_slots': assigned_orders,
        'free_slots': max(0, max_orders_per_day - assigned_orders),
        'workload_percentage': round((assigned_orders / max_orders_per_day) * 100, 1) if max_orders_per_day > 0 else 0,
        'schedule': []  # TODO: добавить расписание если нужно
    }
    
    # Add availability slots for master
    try:
        from ..models import MasterAvailability
        from datetime import date, timedelta
        
        # Get availability for the next 7 days
        today = date.today()
        end_date = today + timedelta(days=7)
        
        availability_slots = MasterAvailability.objects.filter(
            master=master,
            date__gte=today,
            date__lte=end_date
        ).order_by('date', 'start_time')
        
        workload_data['availability_slots'] = [{
            'id': slot.id,
            'date': slot.date.strftime('%Y-%m-%d'),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M')
        } for slot in availability_slots]
        
        # Find next available slot
        if availability_slots:
            workload_data['next_available_slot'] = {
                'date': availability_slots[0].date.strftime('%Y-%m-%d'),
                'start_time': availability_slots[0].start_time.strftime('%H:%M'),
                'end_time': availability_slots[0].end_time.strftime('%H:%M'),
                'orders_on_date': 0  # Could be calculated if needed
            }
        else:
            workload_data['next_available_slot'] = None
            
        workload_data['total_orders_today'] = assigned_orders
        
    except Exception as e:
        print(f"Error getting availability slots: {e}")
        workload_data['availability_slots'] = []
        workload_data['next_available_slot'] = None
        workload_data['total_orders_today'] = assigned_orders
    
    return Response(workload_data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_masters_workload(request):
    """
    Получить информацию о нагрузке всех мастеров
    """
    masters = CustomUser.objects.filter(role='master', is_active=True)
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
        master = CustomUser.objects.get(id=master_id, role='master')
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
    masters = CustomUser.objects.filter(role='master', is_active=True)
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
    Назначить заказ мастеру с проверкой нагрузки
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    master_id = request.data.get('master_id')
    if not master_id:
        return Response({'error': 'master_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Проверяем доступность мастера
    current_orders = Order.objects.filter(
        assigned_master=master,
        status__in=['назначен', 'выполняется']
    ).count()
    
    max_orders = getattr(master, 'max_orders_per_day', 8)
    
    if current_orders >= max_orders:
        return Response({
            'error': 'Мастер не имеет свободных слотов',
            'current_orders': current_orders,
            'max_orders': max_orders
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Назначаем заказ
    order.assigned_master = master
    order.status = 'назначен'
    order.save()
    
    return Response({
        'message': 'Order assigned successfully',
        'order_id': order.id,
        'master_id': master.id,
        'remaining_slots': max_orders - current_orders - 1
    })
