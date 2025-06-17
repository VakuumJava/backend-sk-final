"""
API представления для логирования
"""
from .utils import *


# ----------------------------------------
#  Логирование
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_order_logs(request, order_id):
    """
    Получить логи для конкретного заказа
    """
    try:
        order = Order.objects.get(id=order_id)
        logs = OrderLog.objects.filter(order=order).order_by('-created_at')
        serializer = OrderLogSerializer(logs, many=True)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_order_logs(request):
    """
    Получить все логи заказов (с пагинацией)
    """
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit
    
    logs = OrderLog.objects.all().order_by('-created_at')[offset:offset + limit]
    total_count = OrderLog.objects.count()
    
    serializer = OrderLogSerializer(logs, many=True)
    
    return Response({
        'logs': serializer.data,
        'total_count': total_count,
        'page': page,
        'limit': limit,
        'has_next': offset + limit < total_count
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_transaction_logs(request, user_id=None):
    """
    Получить логи транзакций для пользователя или все
    """
    if user_id:
        try:
            user = CustomUser.objects.get(id=user_id)
            logs = TransactionLog.objects.filter(user=user).order_by('-created_at')
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Все логи транзакций (только для администраторов)
        if request.user.role not in ['super-admin', 'admin']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        logs = TransactionLog.objects.all().order_by('-created_at')
    
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 50))
    offset = (page - 1) * limit
    
    paginated_logs = logs[offset:offset + limit]
    total_count = logs.count()
    
    serializer = TransactionLogSerializer(paginated_logs, many=True)
    
    return Response({
        'logs': serializer.data,
        'total_count': total_count,
        'page': page,
        'limit': limit,
        'has_next': offset + limit < total_count
    })
