"""
Views for Order Slot Management
Управление слотами заказов: 1 заказ = 1 слот
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime, date, timedelta, time
from django.utils import timezone

from .models import CustomUser, Order, OrderSlot, MasterDailySchedule
from .serializers import OrderSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_master_daily_schedule(request, master_id, schedule_date=None):
    """
    Получить расписание мастера на день со всеми слотами
    GET /api/slots/master/{master_id}/schedule/{date}/
    """
    try:
        master = get_object_or_404(
            CustomUser, 
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
        
        # Если дата не указана в path, проверяем query параметр
        if schedule_date:
            try:
                target_date = datetime.strptime(schedule_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            # Проверяем query параметр 'date'
            date_param = request.GET.get('date')
            if date_param:
                try:
                    target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                except ValueError:
                    return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
            else:
                target_date = date.today()
        
        # Получаем или создаем расписание дня
        daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, target_date)
        
        # Получаем все слоты дня
        slots = daily_schedule.get_all_slots()
        
        # Подготавливаем данные для ответа
        slots_data = []
        for slot in slots:
            slot_data = {
                'slot_number': slot['slot_number'],
                'time': slot['time'].strftime('%H:%M'),
                'end_time': slot['end_time'].strftime('%H:%M'),
                'is_occupied': slot['is_occupied'],
                'status': slot['status'],
                'order_id': slot['order'].id if slot['order'] else None,
                'order': None
            }
            
            # Добавляем информацию о заказе, если слот занят
            if slot['order'] and slot['order'].status not in ['завершен', 'отклонен']:
                slot_data['order'] = {
                    'id': slot['order'].id,
                    'client_name': slot['order'].client_name,
                    'client_phone': slot['order'].client_phone,
                    'address': slot['order'].get_full_address(),
                    'description': slot['order'].description,
                    'status': slot['order'].status,
                    'service_type': slot['order'].service_type,
                    'estimated_cost': float(slot['order'].estimated_cost) if slot['order'].estimated_cost else None
                }
            elif slot['order'] and slot['order'].status in ['завершен', 'отклонен']:
                # Если заказ завершен или отклонен, показываем слот как свободный
                slot_data['is_occupied'] = False
                slot_data['status'] = 'free'
                slot_data['order_id'] = None
            
            slots_data.append(slot_data)
        
        response_data = {
            'master_id': master.id,
            'master_name': master.get_full_name() if hasattr(master, 'get_full_name') else master.email,
            'date': target_date.strftime('%Y-%m-%d'),
            'work_start_time': daily_schedule.work_start_time.strftime('%H:%M'),
            'work_end_time': daily_schedule.work_end_time.strftime('%H:%M'),
            'max_slots': daily_schedule.max_slots,
            'total_slots': len(slots),
            'occupied_slots': daily_schedule.get_occupied_slots_count(),
            'free_slots': daily_schedule.get_free_slots_count(),
            'is_working_day': daily_schedule.is_working_day,
            'slots': slots_data
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_order_to_slot(request):
    """
    Назначить заказ на конкретный слот
    POST /api/slots/assign/
    Body: {
        "order_id": 123,
        "master_id": 1,
        "slot_date": "2025-06-18",
        "slot_number": 3,
        "slot_time": "13:00"  // optional, будет вычислено автоматически
    }
    """
    try:
        order_id = request.data.get('order_id')
        master_id = request.data.get('master_id')
        slot_date_str = request.data.get('slot_date')
        slot_number = request.data.get('slot_number')
        slot_time_str = request.data.get('slot_time')
        
        if not all([order_id, master_id, slot_date_str, slot_number]):
            return Response({
                'error': 'Missing required fields: order_id, master_id, slot_date, slot_number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем объекты
        order = get_object_or_404(Order, id=order_id)
        master = get_object_or_404(
            CustomUser, 
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
        
        # Парсим дату
        try:
            slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что заказ еще не назначен на слот
        if hasattr(order, 'slot') and order.slot:
            return Response({
                'error': f'Order {order_id} is already assigned to slot {order.slot.slot_number}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем расписание дня
        daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, slot_date)
        
        # Проверяем, что номер слота валидный
        if slot_number < 1 or slot_number > daily_schedule.max_slots:
            return Response({
                'error': f'Invalid slot number. Must be between 1 and {daily_schedule.max_slots}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что слот свободен
        existing_slot = OrderSlot.objects.filter(
            master=master,
            slot_date=slot_date,
            slot_number=slot_number,
            status__in=['reserved', 'confirmed', 'in_progress']
        ).first()
        
        if existing_slot:
            return Response({
                'error': f'Slot {slot_number} on {slot_date} is already occupied by order {existing_slot.order.id}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Вычисляем время слота, если не указано
        if slot_time_str:
            try:
                slot_time = datetime.strptime(slot_time_str, '%H:%M').time()
            except ValueError:
                return Response({'error': 'Invalid time format. Use HH:MM'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            # Автоматически вычисляем время на основе номера слота
            start_datetime = datetime.combine(slot_date, daily_schedule.work_start_time)
            slot_datetime = start_datetime + (daily_schedule.slot_duration * (slot_number - 1))
            slot_time = slot_datetime.time()
        
        # Создаем слот в транзакции
        with transaction.atomic():
            order_slot = OrderSlot.create_slot_for_order(
                order=order,
                master=master,
                slot_date=slot_date,
                slot_number=slot_number,
                slot_time=slot_time
            )
            
            # Обновляем статус заказа
            order.status = 'назначен'
            order.assigned_master = master
            order.save()
            
            # АВТОМАТИЧЕСКАЯ ОЧИСТКА при назначении: удаляем слоты завершенных заказов
            try:
                completed_slots = OrderSlot.objects.filter(
                    master=master,
                    order__status__in=['завершен', 'отклонен']
                )
                if completed_slots.exists():
                    completed_count = completed_slots.count()
                    completed_slots.delete()
                    print(f"DEBUG: АВТООЧИСТКА при назначении - Удалено {completed_count} слотов завершенных заказов у мастера {master.email}")
                    
                # Также очищаем устаревшие слоты
                outdated_slots = OrderSlot.objects.filter(
                    master=master,
                    status__in=['completed', 'cancelled']
                )
                if outdated_slots.exists():
                    outdated_count = outdated_slots.count()
                    outdated_slots.delete()
                    print(f"DEBUG: АВТООЧИСТКА при назначении - Удалено {outdated_count} устаревших слотов у мастера {master.email}")
                    
            except Exception as cleanup_error:
                print(f"DEBUG: Ошибка автоматической очистки при назначении: {str(cleanup_error)}")
        
        return Response({
            'message': 'Order assigned to slot successfully',
            'order_id': order.id,
            'master_id': master.id,
            'slot': {
                'slot_number': order_slot.slot_number,
                'slot_date': order_slot.slot_date.strftime('%Y-%m-%d'),
                'slot_time': order_slot.slot_time.strftime('%H:%M'),
                'end_time': order_slot.get_end_time().strftime('%H:%M'),
                'status': order_slot.status,
                'display_name': order_slot.get_slot_display_name()
            },
            'remaining_slots': daily_schedule.get_free_slots_count() - 1  # -1 потому что только что заняли
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_slots_for_master(request, master_id, schedule_date=None):
    """
    Получить доступные слоты для мастера на дату
    GET /api/slots/master/{master_id}/available/{date}/
    """
    try:
        master = get_object_or_404(
            CustomUser, 
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
        
        if schedule_date:
            try:
                target_date = datetime.strptime(schedule_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = date.today()
        
        # Получаем доступные слоты
        available_slot_numbers = OrderSlot.get_available_slots_for_master(master, target_date)
        
        # Получаем расписание дня для дополнительной информации
        daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, target_date)
        
        # Формируем детальную информацию о доступных слотах
        available_slots = []
        for slot_number in available_slot_numbers:
            start_datetime = datetime.combine(target_date, daily_schedule.work_start_time)
            slot_datetime = start_datetime + (daily_schedule.slot_duration * (slot_number - 1))
            end_datetime = slot_datetime + daily_schedule.slot_duration
            
            available_slots.append({
                'slot_number': slot_number,
                'time': slot_datetime.time().strftime('%H:%M'),
                'end_time': end_datetime.time().strftime('%H:%M'),
                'display_name': f"Слот {slot_number} ({slot_datetime.time().strftime('%H:%M')})"
            })
        
        return Response({
            'master_id': master.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'total_slots': daily_schedule.max_slots,
            'available_slots_count': len(available_slots),
            'available_slots': available_slots
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_order_slot(request):
    """
    Освободить слот заказа (отменить назначение)
    POST /api/slots/release/
    Body: {"order_id": 123} или {"slot_id": 456}
    """
    try:
        order_id = request.data.get('order_id')
        slot_id = request.data.get('slot_id')
        
        if not order_id and not slot_id:
            return Response({
                'error': 'Either order_id or slot_id must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Находим слот
        if order_id:
            order = get_object_or_404(Order, id=order_id)
            if not hasattr(order, 'slot') or not order.slot:
                return Response({
                    'error': f'Order {order_id} is not assigned to any slot'
                }, status=status.HTTP_400_BAD_REQUEST)
            order_slot = order.slot
        else:
            order_slot = get_object_or_404(OrderSlot, id=slot_id)
            order = order_slot.order
        
        # Освобождаем слот в транзакции
        with transaction.atomic():
            # Обновляем статус заказа
            order.status = 'новый'
            order.assigned_master = None
            order.scheduled_date = None
            order.scheduled_time = None
            order.save()
            
            # Удаляем слот
            slot_info = {
                'slot_number': order_slot.slot_number,
                'slot_date': order_slot.slot_date.strftime('%Y-%m-%d'),
                'slot_time': order_slot.slot_time.strftime('%H:%M'),
                'master_id': order_slot.master.id
            }
            order_slot.delete()
        
        return Response({
            'message': 'Order slot released successfully',
            'order_id': order.id,
            'released_slot': slot_info
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_slot_info(request, order_id):
    """
    Получить информацию о слоте заказа
    GET /api/slots/order/{order_id}/
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        if not hasattr(order, 'slot') or not order.slot:
            return Response({
                'order_id': order.id,
                'has_slot': False,
                'message': 'Order is not assigned to any slot'
            })
        
        order_slot = order.slot
        
        return Response({
            'order_id': order.id,
            'has_slot': True,
            'slot': {
                'id': order_slot.id,
                'slot_number': order_slot.slot_number,
                'slot_date': order_slot.slot_date.strftime('%Y-%m-%d'),
                'slot_time': order_slot.slot_time.strftime('%H:%M'),
                'end_time': order_slot.get_end_time().strftime('%H:%M'),
                'status': order_slot.status,
                'display_name': order_slot.get_slot_display_name(),
                'duration': str(order_slot.slot_duration),
                'master': {
                    'id': order_slot.master.id,
                    'name': order_slot.master.get_full_name() if hasattr(order_slot.master, 'get_full_name') else order_slot.master.email,
                    'email': order_slot.master.email
                },
                'notes': order_slot.notes,
                'created_at': order_slot.created_at.isoformat(),
                'updated_at': order_slot.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_masters_slots_summary(request, schedule_date=None):
    """
    Получить сводку по слотам всех мастеров на дату
    GET /api/slots/masters/summary/{date}/
    """
    try:
        if schedule_date:
            try:
                target_date = datetime.strptime(schedule_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = date.today()
        
        # Получаем всех мастеров
        masters = CustomUser.objects.filter(
            role__in=['master', 'garant-master', 'warrant-master']
        )
        masters_summary = []
        
        for master in masters:
            daily_schedule = MasterDailySchedule.get_or_create_for_master_date(master, target_date)
            
            summary = {
                'master_id': master.id,
                'master_name': master.get_full_name() if hasattr(master, 'get_full_name') else master.email,
                'master_email': master.email,
                'total_slots': daily_schedule.max_slots,
                'occupied_slots': daily_schedule.get_occupied_slots_count(),
                'free_slots': daily_schedule.get_free_slots_count(),
                'workload_percentage': round((daily_schedule.get_occupied_slots_count() / daily_schedule.max_slots) * 100, 1),
                'is_working_day': daily_schedule.is_working_day
            }
            
            masters_summary.append(summary)
        
        return Response({
            'date': target_date.strftime('%Y-%m-%d'),
            'total_masters': len(masters),
            'masters': masters_summary
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
