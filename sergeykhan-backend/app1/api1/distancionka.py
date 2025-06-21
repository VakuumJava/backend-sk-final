from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum, Avg
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Order, CustomUser, Balance, DistanceSettingsModel


def calculate_average_check(master_id, orders_count=10):
    """Расчет среднего чека за последние N заказов"""
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return 0
    
    # Получаем последние завершенные заказы мастера
    recent_orders = Order.objects.filter(
        assigned_master=master,
        status='завершен',
        final_cost__isnull=False
    ).order_by('-created_at')[:orders_count]
    
    if not recent_orders:
        return 0
    
    total_cost = sum(order.final_cost for order in recent_orders)
    return total_cost / len(recent_orders)


def calculate_daily_revenue(master_id):
    """Расчет суммы заказов за последние 24 часа"""
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return 0
    
    yesterday = timezone.now() - timedelta(days=1)
    
    daily_orders = Order.objects.filter(
        assigned_master=master,
        status='завершен',
        final_cost__isnull=False,
        created_at__gte=yesterday
    )
    
    return daily_orders.aggregate(total=Sum('final_cost'))['total'] or 0


def calculate_net_turnover(master_id, days=10):
    """Расчет чистого вала за последние N дней"""
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return 0
    
    period_start = timezone.now() - timedelta(days=days)
    
    orders = Order.objects.filter(
        assigned_master=master,
        status='завершен',
        final_cost__isnull=False,
        expenses__isnull=False,
        created_at__gte=period_start
    )
    
    # Чистый вал = доходы - расходы
    total_revenue = orders.aggregate(total=Sum('final_cost'))['total'] or 0
    total_expenses = orders.aggregate(total=Sum('expenses'))['total'] or 0
    
    return total_revenue - total_expenses


def check_distance_level(master_id):
    """Проверка уровня дистанционки мастера"""
    settings = DistanceSettingsModel.get_settings()
    
    # Расчет показателей
    avg_check = calculate_average_check(master_id)
    daily_revenue = calculate_daily_revenue(master_id)
    net_turnover = calculate_net_turnover(master_id)
    
    # Проверка на суточную дистанционку (уровень 2)
    if (daily_revenue >= settings.daily_order_sum_threshold or 
        net_turnover >= settings.net_turnover_threshold):
        return 2
    
    # Проверка на обычную дистанционку (уровень 1)
    if avg_check >= settings.average_check_threshold:
        return 1
    
    # Нет дистанционки
    return 0


def update_master_distance_status(master_id):
    """Обновление статуса дистанционки мастера (только если не установлено вручную)"""
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
        
        # Если дистанционка установлена вручную, не изменяем её
        if master.distance_manual_override:
            return False
            
        new_level = check_distance_level(master_id)
        
        if master.dist != new_level:
            master.dist = new_level
            master.save()
            return True
        return False
    except CustomUser.DoesNotExist:
        return False


def get_visible_orders_for_master(master_id):
    """Получение видимых заказов для мастера с учетом дистанционки"""
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Order.objects.none()
    
    # Обновляем статус дистанционки перед получением заказов
    update_master_distance_status(master_id)
    master.refresh_from_db()
    
    now = timezone.now()
    
    # Определяем временной порог в зависимости от уровня дистанционки
    # Мастер видит заказы созданные за последние X часов
    if master.dist == 2:  # Суточная дистанционка - видит заказы за последние 48 часов
        time_threshold = now - timedelta(hours=48)
    elif master.dist == 1:  # Дневная дистанционка - видит заказы за последние 28 часов
        time_threshold = now - timedelta(hours=28)
    else:  # Нет дистанционки - видит заказы за последние 24 часа
        time_threshold = now - timedelta(hours=24)
    
    print(f"DEBUG: Master {master_id} (dist level {master.dist}) sees orders from {time_threshold}")
    
    # Возвращаем только НОВЫЕ заказы, которые видны мастеру в зависимости от дистанционки
    orders = Order.objects.filter(
        status='новый',  # Только новые заказы!
        assigned_master__isnull=True,  # Только неназначенные заказы
        created_at__gte=time_threshold  # Созданные после временного порога (в пределах временного окна)
    ).order_by('-created_at')
    
    print(f"DEBUG: Found {orders.count()} orders for master {master_id}")
    
    return orders


# API Endpoints

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_distance_settings(request):
    """Получение текущих настроек дистанционки"""
    if request.user.role != 'super-admin':
        return Response({'error': 'Access denied'}, status=403)
    
    settings = DistanceSettingsModel.get_settings()
    return Response({
        'averageCheckThreshold': float(settings.average_check_threshold),
        'visiblePeriodStandard': settings.visible_period_standard,
        'dailyOrderSumThreshold': float(settings.daily_order_sum_threshold),
        'netTurnoverThreshold': float(settings.net_turnover_threshold),
        'visiblePeriodDaily': settings.visible_period_daily
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_distance_settings(request):
    """Обновление настроек дистанционки (только для супер-админа)"""
    if request.user.role != 'super-admin':
        return Response({'error': 'Access denied'}, status=403)
    
    try:
        data = request.data
        settings = DistanceSettingsModel.get_settings()
        
        # Обновляем настройки
        if 'averageCheckThreshold' in data:
            settings.average_check_threshold = data['averageCheckThreshold']
        if 'visiblePeriodStandard' in data:
            settings.visible_period_standard = data['visiblePeriodStandard']
        if 'dailyOrderSumThreshold' in data:
            settings.daily_order_sum_threshold = data['dailyOrderSumThreshold']
        if 'netTurnoverThreshold' in data:
            settings.net_turnover_threshold = data['netTurnoverThreshold']
        if 'visiblePeriodDaily' in data:
            settings.visible_period_daily = data['visiblePeriodDaily']
        
        settings.updated_by = request.user
        settings.save()
        
        return Response({
            'message': 'Settings updated successfully',
            'settings': {
                'averageCheckThreshold': float(settings.average_check_threshold),
                'visiblePeriodStandard': settings.visible_period_standard,
                'dailyOrderSumThreshold': float(settings.daily_order_sum_threshold),
                'netTurnoverThreshold': float(settings.net_turnover_threshold),
                'visiblePeriodDaily': settings.visible_period_daily
            }
        })
    except Exception as e:
        return Response({'error': f'Failed to update settings: {str(e)}'}, status=400)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_distance_info(request, master_id=None):
    """Получение информации о дистанционке мастера"""
    if request.user.role not in ['super-admin', 'curator']:
        return Response({'error': 'Access denied'}, status=403)
    
    if master_id is None:
        master_id = request.user.id
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=404)
    
    # Обновляем статус дистанционки
    update_master_distance_status(master_id)
    master.refresh_from_db()
    
    # Получаем статистику
    avg_check = calculate_average_check(master_id)
    daily_revenue = calculate_daily_revenue(master_id)
    net_turnover = calculate_net_turnover(master_id)
    
    settings = DistanceSettingsModel.get_settings()
    
    return Response({
        'master_id': master.id,
        'master_email': master.email,
        'distance_level': master.dist,
        'manual_override': master.distance_manual_override,
        'distance_level_name': {
            0: 'Нет дистанционки',
            1: 'Обычная дистанционка (+4 часа)',
            2: 'Суточная дистанционка (+24 часа)'
        }.get(master.dist, 'Неизвестно'),
        'statistics': {
            'average_check': float(avg_check),
            'daily_revenue': float(daily_revenue),
            'net_turnover_10_days': float(net_turnover),
        },
        'thresholds': {
            'average_check_threshold': settings.average_check_threshold,
            'daily_order_sum_threshold': settings.daily_order_sum_threshold,
            'net_turnover_threshold': settings.net_turnover_threshold,
        },
        'meets_requirements': {
            'standard_distance': avg_check >= settings.average_check_threshold,
            'daily_distance_by_revenue': daily_revenue >= settings.daily_order_sum_threshold,
            'daily_distance_by_turnover': net_turnover >= settings.net_turnover_threshold,
        }
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_masters_distance(request):
    """Получение информации о дистанционке всех мастеров"""
    if request.user.role != 'super-admin':
        return Response({'error': 'Access denied'}, status=403)
    
    masters = CustomUser.objects.filter(
        role__in=['master', 'garant-master', 'warrant-master']
    )
    result = []
    
    for master in masters:
        master.refresh_from_db()
        
        avg_check = calculate_average_check(master.id)
        daily_revenue = calculate_daily_revenue(master.id)
        net_turnover = calculate_net_turnover(master.id)
        
        # Получаем настройки дистанционки
        settings = DistanceSettingsModel.get_settings()
        
        result.append({
            'master_id': master.id,
            'master_email': master.email,
            'distance_level': master.dist,
            'manual_override': master.distance_manual_override,
            'distance_level_name': {
                0: 'Нет дистанционки',
                1: 'Обычная дистанционка (+4 часа)',
                2: 'Суточная дистанционка (+24 часа)'
            }.get(master.dist, 'Неизвестно'),
            'statistics': {
                'average_check': float(avg_check),
                'daily_revenue': float(daily_revenue),
                'net_turnover_10_days': float(net_turnover),
            },
            'thresholds': {
                'average_check_threshold': settings.average_check_threshold,
                'daily_order_sum_threshold': settings.daily_order_sum_threshold,
                'net_turnover_threshold': settings.net_turnover_threshold,
            },
            'meets_requirements': {
                'standard_distance': avg_check >= settings.average_check_threshold,
                'daily_distance_by_revenue': daily_revenue >= settings.daily_order_sum_threshold,
                'daily_distance_by_turnover': net_turnover >= settings.net_turnover_threshold,
            }
        })
    
    return Response(result)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_available_orders_with_distance(request):
    """Получение доступных заказов для мастера с учетом дистанционки"""
    if request.user.role not in ['master', 'garant-master', 'warrant-master']:
        return Response({'error': 'Access denied'}, status=403)
    
    orders = get_visible_orders_for_master(request.user.id)
    
    # Используем публичный сериализатор для мастеров, которые еще не взяли заказ
    from .serializers import OrderPublicSerializer
    serializer = OrderPublicSerializer(orders, many=True)
    
    # Получаем информацию о дистанционке мастера
    master = request.user
    distance_info = {
        'distance_level': master.dist,
        'distance_level_name': {
            0: 'Нет дистанционки',
            1: 'Дневная дистанционка',
            2: 'Суточная дистанционка'
        }.get(master.dist, 'Неизвестно'),
        'orders_count': len(serializer.data)
    }
    
    return Response({
        'orders': serializer.data,
        'distance_info': distance_info
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def force_update_all_masters_distance(request):
    """Принудительное обновление дистанционки для всех мастеров"""
    if request.user.role != 'super-admin':
        return Response({'error': 'Access denied'}, status=403)
    
    masters = CustomUser.objects.filter(
        role__in=['master', 'garant-master', 'warrant-master']
    )
    updated_count = 0
    
    for master in masters:
        if update_master_distance_status(master.id):
            updated_count += 1
    
    return Response({
        'message': f'Distance status updated for {updated_count} masters',
        'total_masters': masters.count(),
        'updated_masters': updated_count
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def set_master_distance_manually(request, master_id):
    """Ручная установка уровня дистанционки мастера"""
    if request.user.role not in ['super-admin']:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    distance_level = request.data.get('distance_level')
    if distance_level not in [0, 1, 2]:
        return Response({'error': 'Invalid distance level. Must be 0, 1, or 2'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    master.dist = distance_level
    master.distance_manual_override = True  # Устанавливаем флаг ручной установки
    master.save()
    
    return Response({
        'message': f'Distance level set to {distance_level} for master {master.email}',
        'master_id': master.id,
        'new_distance_level': distance_level,
        'manual_override': True
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def reset_master_distance_to_automatic(request, master_id):
    """Сброс ручной установки дистанционки и переход к автоматическому расчету"""
    if request.user.role not in ['super-admin']:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Сбрасываем флаг ручной установки
    master.distance_manual_override = False
    master.save()
    
    # Пересчитываем дистанционку автоматически
    update_master_distance_status(master_id)
    master.refresh_from_db()
    
    return Response({
        'message': f'Distance level reset to automatic for master {master.email}',
        'master_id': master.id,
        'new_distance_level': master.dist,
        'manual_override': False
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_distance_with_orders(request):
    """Получение информации о дистанционке мастера с заказами"""
    if request.user.role not in ['master', 'garant-master', 'warrant-master']:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    master_id = request.user.id
    master = request.user
    
    # Используем фактический уровень дистанции мастера, а не пересчитанный
    distance_level = master.dist
    
    # Получаем видимые заказы с учетом дистанционки
    visible_orders = get_visible_orders_for_master(master_id)
    
    # Сериализуем заказы с публичной информацией (без apartment/entrance/phone)
    orders_data = []
    for order in visible_orders:
        orders_data.append({
            'id': order.id,
            'client_name': order.client_name,
            'description': order.description,
            'status': order.status,
            'estimated_cost': str(order.estimated_cost) if order.estimated_cost else None,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'public_address': order.get_public_address(),  # Только улица и дом
            'street': order.street,
            'house_number': order.house_number
        })
    
    # Получаем статистику мастера
    settings = DistanceSettingsModel.get_settings()
    avg_check = calculate_average_check(master_id)
    daily_revenue = calculate_daily_revenue(master_id)
    net_turnover = calculate_net_turnover(master_id)
    
    distance_names = {0: 'Нет дистанционки', 1: 'Обычная (+4ч)', 2: 'Суточная (+24ч)'}
    
    # Определяем часы видимости
    visibility_hours = 24  # базовая видимость
    if distance_level == 1:
        visibility_hours = 28  # +4 часа
    elif distance_level == 2:
        visibility_hours = 48  # +24 часа
    
    return Response({
        'distance_info': {
            'distance_level': distance_level,
            'distance_level_name': distance_names.get(distance_level, 'Неизвестно'),
            'visibility_hours': visibility_hours,
            'statistics': {
                'average_check': float(avg_check),
                'daily_revenue': float(daily_revenue),
                'net_turnover_10_days': float(net_turnover)
            },
            'thresholds': {
                'average_check_threshold': settings.average_check_threshold,
                'daily_revenue_threshold': settings.daily_order_sum_threshold,
                'net_turnover_threshold': settings.net_turnover_threshold
            },
            'meets_requirements': {
                'level_1': float(avg_check) >= settings.average_check_threshold,
                'level_2': (float(daily_revenue) >= settings.daily_order_sum_threshold or 
                           float(net_turnover) >= settings.net_turnover_threshold)
            }
        },
        'orders': orders_data,
        'total_orders': len(orders_data)
    })


def get_visible_orders_for_master_enhanced(master_id):
    """Улучшенная функция получения видимых заказов с учетом дистанционки"""
    distance_level = check_distance_level(master_id)
    now = timezone.now()
    
    # Определяем период видимости в зависимости от уровня дистанционки
    if distance_level == 0:
        # Без дистанционки: 24 часа вперед
        visible_until = now + timedelta(hours=24)
    elif distance_level == 1:
        # Обычная дистанционка: 28 часов вперед (+4 часа)
        visible_until = now + timedelta(hours=28)
    elif distance_level == 2:
        # Суточная дистанционка: 48 часов вперед (+24 часа)
        visible_until = now + timedelta(hours=48)
    else:
        visible_until = now + timedelta(hours=24)
    
    # Получаем заказы в пределах видимого периода
    visible_orders = Order.objects.filter(
        status__in=['новый', 'в обработке'],
        created_at__lte=visible_until,
        assigned_master__isnull=True  # Только неназначенные заказы
    ).order_by('created_at')
    
    return visible_orders


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_distance_status(request):
    """Получение краткой информации о статусе дистанционки текущего мастера"""
    if request.user.role not in ['master', 'garant-master', 'warrant-master']:
        return Response({'error': 'Access denied. Only masters can access this endpoint.'}, status=403)
    
    master_id = request.user.id
    
    try:
        master = CustomUser.objects.get(
            id=master_id, 
            role__in=['master', 'garant-master', 'warrant-master']
        )
    except CustomUser.DoesNotExist:
        return Response({'error': 'Master not found'}, status=404)
    
    # Обновляем статус дистанционки
    update_master_distance_status(master_id)
    master.refresh_from_db()
    
    # Определяем часы видимости заказов
    if master.dist == 2:  # Суточная дистанционка
        visibility_hours = 48
    elif master.dist == 1:  # Обычная дистанционка
        visibility_hours = 28
    else:  # Нет дистанционки
        visibility_hours = 24
    
    return Response({
        'distance_level': master.dist,
        'distance_level_name': {
            0: 'Нет дистанционки',
            1: 'Обычная дистанционка',
            2: 'Суточная дистанционка'
        }.get(master.dist, 'Неизвестно'),
        'visibility_hours': visibility_hours
    })