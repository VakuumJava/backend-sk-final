from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import CalendarEvent, CustomUser
from .serializers import CalendarEventSerializer

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_events(request, master_id):
    """
    GET /master/{master_id}/events/
    Returns all events for a specific master.
    Requires authentication and curator or super-admin role.
    """
    # Проверяем, что пользователь имеет роль куратора или супер-админа
    if not request.user.role in ['curator', 'super-admin']:
        return Response(
            {'error': 'Нет доступа. Только кураторы и супер-админы могут просматривать календарь мастеров.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Проверяем, что мастер существует
        master = CustomUser.objects.get(id=master_id, role='master')
    except CustomUser.DoesNotExist:
        return Response({'error': 'Мастер не найден'}, status=status.HTTP_404_NOT_FOUND)
    
    # Получаем события календаря мастера
    events = CalendarEvent.objects.filter(master=master)
    serializer = CalendarEventSerializer(events, many=True)
    return Response(serializer.data)
