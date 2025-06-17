from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Q, Count
from django.core.exceptions import ValidationError

from .models import MasterAvailability, Order, CustomUser
from .serializers import MasterAvailabilitySerializer, MasterWorkloadSerializer
from .middleware import role_required


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['curator', 'super-admin'])
def master_availability_list(request, master_id):
    """
    GET: List all availability slots for a master
    POST: Create new availability slot for a master
    """
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        availability_slots = MasterAvailability.objects.filter(
            master=master,
            date__gte=timezone.now().date()
        ).order_by('date', 'start_time')
        
        serializer = MasterAvailabilitySerializer(availability_slots, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['master'] = master_id
        
        serializer = MasterAvailabilitySerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['curator', 'super-admin'])
def master_availability_detail(request, master_id, availability_id):
    """
    GET: Retrieve specific availability slot
    PUT: Update availability slot
    DELETE: Delete availability slot
    """
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        availability = MasterAvailability.objects.get(id=availability_id, master=master)
    except (CustomUser.DoesNotExist, MasterAvailability.DoesNotExist):
        return Response({'error': 'Availability slot not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = MasterAvailabilitySerializer(availability)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = MasterAvailabilitySerializer(availability, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                return Response(serializer.data)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        availability.delete()
        return Response({'message': 'Availability slot deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['curator', 'super-admin'])
def master_workload_detail(request, master_id):
    """
    GET: Get complete workload information for a master including availability and orders
    """
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    today = timezone.now().date()
    
    # Get availability slots for future dates
    availability_slots = MasterAvailability.objects.filter(
        master=master,
        date__gte=today
    ).order_by('date', 'start_time')
    
    # Get orders count by date
    orders = Order.objects.filter(
        assigned_master=master,
        scheduled_date__gte=today
    ).values('scheduled_date').annotate(count=Count('id'))
    
    orders_count_by_date = {
        str(order['scheduled_date']): order['count'] 
        for order in orders if order['scheduled_date']
    }
    
    # Calculate next available slot
    next_available_slot = None
    for slot in availability_slots:
        date_str = str(slot.date)
        orders_on_date = orders_count_by_date.get(date_str, 0)
        
        # Check if this slot has conflicts with existing orders
        conflicting_orders = Order.objects.filter(
            assigned_master=master,
            scheduled_date=slot.date,
            scheduled_time__gte=slot.start_time,
            scheduled_time__lt=slot.end_time
        ).count()
        
        if conflicting_orders == 0:
            next_available_slot = {
                'date': slot.date,
                'start_time': slot.start_time,
                'end_time': slot.end_time,
                'orders_on_date': orders_on_date
            }
            break
    
    # Count today's orders
    total_orders_today = Order.objects.filter(
        assigned_master=master,
        scheduled_date=today
    ).count()
    
    workload_data = {
        'master_id': master.id,
        'master_email': master.email,
        'availability_slots': MasterAvailabilitySerializer(availability_slots, many=True).data,
        'orders_count_by_date': orders_count_by_date,
        'next_available_slot': next_available_slot,
        'total_orders_today': total_orders_today
    }
    
    return Response(workload_data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['curator', 'super-admin'])
def all_masters_workload(request):
    """
    GET: Get workload summary for all masters
    """
    masters = CustomUser.objects.filter(role='master')
    masters_workload = []
    
    today = timezone.now().date()
    
    for master in masters:
        # Get next available slot
        availability_slots = MasterAvailability.objects.filter(
            master=master,
            date__gte=today
        ).order_by('date', 'start_time')
        
        next_available_slot = None
        for slot in availability_slots:
            # Check if this slot has conflicts with existing orders
            conflicting_orders = Order.objects.filter(
                assigned_master=master,
                scheduled_date=slot.date,
                scheduled_time__gte=slot.start_time,
                scheduled_time__lt=slot.end_time
            ).count()
            
            if conflicting_orders == 0:
                next_available_slot = {
                    'date': slot.date,
                    'start_time': slot.start_time,
                    'end_time': slot.end_time
                }
                break
        
        # Count today's orders
        total_orders_today = Order.objects.filter(
            assigned_master=master,
            scheduled_date=today
        ).count()
        
        masters_workload.append({
            'master_id': master.id,
            'master_email': master.email,
            'next_available_slot': next_available_slot,
            'total_orders_today': total_orders_today
        })
    
    return Response(masters_workload)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['curator', 'super-admin'])
def validate_order_scheduling(request):
    """
    POST: Validate if an order can be scheduled at a specific time for a master
    """
    master_id = request.data.get('master_id')
    scheduled_date = request.data.get('scheduled_date')
    scheduled_time = request.data.get('scheduled_time')
    
    if not all([master_id, scheduled_date, scheduled_time]):
        return Response(
            {'error': 'master_id, scheduled_date, and scheduled_time are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        master = CustomUser.objects.get(id=master_id, role='master')
        schedule_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
        schedule_time = datetime.strptime(scheduled_time, '%H:%M:%S').time()
    except (CustomUser.DoesNotExist, ValueError):
        return Response(
            {'error': 'Invalid master_id, scheduled_date, or scheduled_time format'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if master has availability at this time
    availability_slots = MasterAvailability.objects.filter(
        master=master,
        date=schedule_date,
        start_time__lte=schedule_time,
        end_time__gt=schedule_time
    )
    
    if not availability_slots.exists():
        return Response({
            'valid': False,
            'error': 'Master is not available at the requested time'
        })
    
    # Check if there are conflicting orders
    conflicting_orders = Order.objects.filter(
        assigned_master=master,
        scheduled_date=schedule_date,
        scheduled_time=schedule_time
    )
    
    if conflicting_orders.exists():
        return Response({
            'valid': False,
            'error': 'Master already has an order scheduled at this time'
        })
    
    return Response({
        'valid': True,
        'message': 'Time slot is available for scheduling'
    })
