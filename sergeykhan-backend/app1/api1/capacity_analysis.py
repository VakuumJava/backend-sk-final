"""
Система планирования и контроля нагрузки мастеров
Анализирует пропускную способность и дает рекомендации по принятию заказов
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Q, Count, Sum
from decimal import Decimal

from .models import CustomUser, Order, MasterAvailability
from .middleware import role_required


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['super-admin', 'curator', 'operator', 'master'])
def get_capacity_analysis(request):
    """
    Анализ пропускной способности мастеров и рекомендации по планированию
    """
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Получаем всех активных мастеров
    masters = CustomUser.objects.filter(role='master')
    
    # Анализ на сегодня
    today_analysis = analyze_day_capacity(today, masters)
    
    # Анализ на завтра  
    tomorrow_analysis = analyze_day_capacity(tomorrow, masters)
    
    # Общая статистика по заказам
    total_new_orders = Order.objects.filter(status='новый').count()
    total_processing_orders = Order.objects.filter(status='в обработке').count()
    total_pending_orders = total_new_orders + total_processing_orders
    
    # Рекомендации по планированию
    recommendations = generate_recommendations(
        today_analysis, tomorrow_analysis, total_pending_orders
    )
    
    return Response({
        'today': today_analysis,
        'tomorrow': tomorrow_analysis,
        'pending_orders': {
            'new_orders': total_new_orders,
            'processing_orders': total_processing_orders,
            'total_pending': total_pending_orders
        },
        'recommendations': recommendations,
        'analysis_timestamp': timezone.now().isoformat()
    })


def analyze_day_capacity(target_date, masters):
    """
    Анализирует пропускную способность мастеров на конкретный день
    """
    # Мастера с доступностью на этот день
    masters_with_availability = masters.filter(
        availability_slots__date=target_date
    ).distinct()
    
    # Мастера уже с назначенными заказами на этот день
    masters_with_orders = masters.filter(
        orders__scheduled_date=target_date
    ).distinct()
    
    # Подсчет слотов времени
    total_time_slots = MasterAvailability.objects.filter(
        date=target_date
    ).count()
    
    # Занятые слоты (заказы на этот день)
    occupied_slots = Order.objects.filter(
        scheduled_date=target_date,
        status__in=['назначен', 'выполняется', 'в работе']
    ).count()
    
    # Доступные слоты
    available_slots = max(0, total_time_slots - occupied_slots)
    
    # Средняя продолжительность заказа (предположим 2-4 часа)
    avg_order_duration_hours = 3
    
    # Средняя продолжительность рабочего дня мастера (8 часов)
    avg_workday_hours = 8
    
    # Максимальное количество заказов, которое может выполнить один мастер за день
    max_orders_per_master_per_day = avg_workday_hours // avg_order_duration_hours
    
    # Теоретическая максимальная пропускная способность
    theoretical_max_capacity = len(masters_with_availability) * max_orders_per_master_per_day
    
    # Реальная пропускная способность (с учетом уже занятых слотов)
    realistic_capacity = available_slots
    
    # Мастера по статусам
    free_masters = masters_with_availability.exclude(
        id__in=masters_with_orders.values_list('id', flat=True)
    )
    
    busy_masters = masters_with_orders
    
    # Мастера без расписания на этот день
    masters_without_schedule = masters.exclude(
        availability_slots__date=target_date
    )
    
    return {
        'date': target_date.isoformat(),
        'date_display': target_date.strftime('%Y-%m-%d (%A)'),
        'masters_stats': {
            'total_masters': masters.count(),
            'masters_with_availability': masters_with_availability.count(),
            'free_masters': free_masters.count(),
            'busy_masters': busy_masters.count(),
            'masters_without_schedule': masters_without_schedule.count()
        },
        'capacity': {
            'total_time_slots': total_time_slots,
            'occupied_slots': occupied_slots,
            'available_slots': available_slots,
            'theoretical_max_capacity': theoretical_max_capacity,
            'realistic_capacity': realistic_capacity,
            'capacity_utilization_percent': round(
                (occupied_slots / max(1, total_time_slots)) * 100, 1
            )
        },
        'masters_details': [
            {
                'id': master.id,
                'email': master.email,
                'name': f"{master.first_name} {master.last_name}".strip(),
                'availability_slots': MasterAvailability.objects.filter(
                    master=master, date=target_date
                ).count(),
                'assigned_orders': Order.objects.filter(
                    assigned_master=master,
                    scheduled_date=target_date
                ).count(),
                'status': get_master_status_for_date(master, target_date)
            }
            for master in masters
        ]
    }


def get_master_status_for_date(master, target_date):
    """
    Определяет статус мастера на конкретную дату
    """
    has_availability = MasterAvailability.objects.filter(
        master=master, date=target_date
    ).exists()
    
    has_orders = Order.objects.filter(
        assigned_master=master,
        scheduled_date=target_date
    ).exists()
    
    if not has_availability:
        return 'no_schedule'  # Нет расписания
    elif has_orders:
        return 'busy'  # Занят
    else:
        return 'available'  # Доступен


def generate_recommendations(today_analysis, tomorrow_analysis, total_pending_orders):
    """
    Генерирует рекомендации по планированию заказов
    """
    today_capacity = today_analysis['capacity']['realistic_capacity']
    tomorrow_capacity = tomorrow_analysis['capacity']['realistic_capacity']
    
    recommendations = []
    
    # Анализ сегодняшней нагрузки
    if today_capacity == 0:
        recommendations.append({
            'type': 'warning',
            'title': 'Сегодня нет доступных мастеров',
            'message': 'Все мастера заняты или нет расписания. Переносите заказы на завтра.',
            'action': 'Не принимайте новые заказы на сегодня'
        })
    elif today_capacity < total_pending_orders:
        recommendations.append({
            'type': 'warning',
            'title': 'Перегрузка на сегодня',
            'message': f'Ожидающих заказов: {total_pending_orders}, доступная пропускная способность: {today_capacity}',
            'action': f'Перенесите {total_pending_orders - today_capacity} заказов на завтра'
        })
    else:
        recommendations.append({
            'type': 'success',
            'title': 'Сегодня есть свободные места',
            'message': f'Можете принять до {today_capacity - total_pending_orders} дополнительных заказов',
            'action': 'Можно активно принимать заказы на сегодня'
        })
    
    # Анализ завтрашней нагрузки
    if tomorrow_capacity == 0:
        recommendations.append({
            'type': 'error',
            'title': 'Завтра нет доступных мастеров',
            'message': 'Срочно составьте расписание для мастеров на завтра!',
            'action': 'Настройте расписание мастеров'
        })
    elif tomorrow_capacity < 5:
        recommendations.append({
            'type': 'warning',
            'title': 'Мало свободных мест на завтра',
            'message': f'Завтра доступно только {tomorrow_capacity} слотов',
            'action': 'Расширьте расписание мастеров на завтра'
        })
    else:
        recommendations.append({
            'type': 'info',
            'title': 'Завтра достаточно мест',
            'message': f'Доступно {tomorrow_capacity} слотов для заказов',
            'action': 'Планируйте заказы на завтра'
        })
    
    # Общие рекомендации
    total_capacity_2_days = today_capacity + tomorrow_capacity
    if total_pending_orders > total_capacity_2_days:
        recommendations.append({
            'type': 'error',
            'title': 'КРИТИЧЕСКАЯ ПЕРЕГРУЗКА',
            'message': f'Заказов: {total_pending_orders}, пропускная способность (2 дня): {total_capacity_2_days}',
            'action': 'СРОЧНО: увеличьте количество мастеров или расширьте расписание!'
        })
    
    return recommendations


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required(['super-admin', 'curator', 'operator', 'master'])
def get_weekly_capacity_forecast(request):
    """
    Прогноз пропускной способности на неделю вперед
    """
    today = timezone.now().date()
    week_forecast = []
    
    for i in range(7):
        target_date = today + timedelta(days=i)
        masters = CustomUser.objects.filter(role='master')
        day_analysis = analyze_day_capacity(target_date, masters)
        
        week_forecast.append({
            'date': target_date.isoformat(),
            'day_name': target_date.strftime('%A'),
            'available_capacity': day_analysis['capacity']['realistic_capacity'],
            'masters_available': day_analysis['masters_stats']['masters_with_availability'],
            'utilization_percent': day_analysis['capacity']['capacity_utilization_percent']
        })
    
    return Response({
        'week_forecast': week_forecast,
        'total_week_capacity': sum(day['available_capacity'] for day in week_forecast),
        'avg_daily_capacity': round(
            sum(day['available_capacity'] for day in week_forecast) / 7, 1
        )
    })
