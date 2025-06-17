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
    Получить информацию о нагрузке конкретного мастера
    """
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Подсчитываем заказы мастера
    assigned_orders = Order.objects.filter(
        assigned_master=master,
        status__in=['назначен', 'выполняется']
    ).count()
    
    # Получаем настройки мастера (или используем базовые)
    max_orders_per_day = getattr(master, 'max_orders_per_day', 8)  # базовое значение
    
    workload_data = {
        'master_id': master.id,
        'master_name': master.full_name or master.email,
        'total_slots': max_orders_per_day,
        'occupied_slots': assigned_orders,
        'free_slots': max(0, max_orders_per_day - assigned_orders),
        'workload_percentage': round((assigned_orders / max_orders_per_day) * 100, 1) if max_orders_per_day > 0 else 0,
        'schedule': []  # TODO: добавить расписание если нужно
    }
    
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
    print(f"   master_id из запроса: {master_id}")
    
    if not master_id:
        return Response({'error': 'master_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        print(f"   ✅ Мастер найден: {master.first_name} {master.last_name} (ID: {master.id})")
    except CustomUser.DoesNotExist:
        print(f"   ❌ Мастер с ID {master_id} не найден")
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Проверяем доступность мастера
    current_orders = Order.objects.filter(
        assigned_master=master,
        status__in=['назначен', 'выполняется']
    )
    current_count = current_orders.count()
    print(f"   📊 Текущие заказы мастера ({current_count}):")
    for o in current_orders:
        print(f"     - Заказ #{o.id}: {o.client_name} ({o.status})")
    
    max_orders = getattr(master, 'max_orders_per_day', 8)
    print(f"   📏 Лимит заказов: {max_orders}")
    print(f"   🔢 Свободных слотов: {max_orders - current_count}")
    
    if current_count >= max_orders:
        print(f"   ❌ Нет свободных слотов!")
        return Response({
            'error': 'Мастер не имеет свободных слотов',
            'current_orders': current_count,
            'max_orders': max_orders
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Назначаем заказ
    order.assigned_master = master
    order.status = 'назначен'
    order.save()
    print(f"   ✅ Заказ #{order.id} назначен мастеру {master.first_name} {master.last_name}")
    
    return Response({
        'message': 'Order assigned successfully',
        'order_id': order.id,
        'master_id': master.id,
        'remaining_slots': max_orders - current_count - 1
    })
