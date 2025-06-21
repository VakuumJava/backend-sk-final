from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from .models import SiteSettings, Service, FeedbackRequest, CustomUser, Order
from .serializers import (
    SiteSettingsSerializer, ServiceSerializer, FeedbackRequestSerializer,
    FeedbackRequestCreateSerializer, OrderSerializer
)


class SiteSettingsViewSet(viewsets.ModelViewSet):
    """API для управления настройками сайта"""
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        # Разрешаем только чтение для неавторизованных пользователей
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            # Только супер-админы могут изменять настройки
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request):
        """Получить настройки сайта"""
        settings_obj, created = SiteSettings.objects.get_or_create()
        serializer = self.get_serializer(settings_obj)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Обновить настройки сайта"""
        # Проверяем права доступа
        if not request.user.is_authenticated or request.user.role != 'super-admin':
            return Response(
                {'error': 'Доступ запрещен. Только супер-админы могут изменять настройки.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings_obj, created = SiteSettings.objects.get_or_create()
        serializer = self.get_serializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceViewSet(viewsets.ModelViewSet):
    """API для управления услугами"""
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    
    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [AllowAny]  # Публичный доступ для чтения
        else:
            permission_classes = [IsAuthenticated]  # Авторизация для изменений
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Фильтрация услуг"""
        if self.request.user.is_authenticated and (
            self.request.user.role == 'super-admin' or 
            self.request.user.is_superuser
        ):
            # Админы видят все услуги, включая неактивные
            return Service.objects.all()
        # Обычные пользователи видят только активные услуги
        return Service.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Создание услуги"""
        if not self.request.user.is_authenticated or self.request.user.role != 'super-admin':
            raise PermissionError('Доступ запрещен')
        serializer.save()
    
    def perform_update(self, serializer):
        """Обновление услуги"""
        if not self.request.user.is_authenticated or self.request.user.role != 'super-admin':
            raise PermissionError('Доступ запрещен')
        serializer.save()
    
    def perform_destroy(self, instance):
        """Мягкое удаление услуги"""
        if not self.request.user.is_authenticated or self.request.user.role != 'super-admin':
            raise PermissionError('Доступ запрещен')
        instance.is_active = False
        instance.save()


class FeedbackRequestViewSet(viewsets.ModelViewSet):
    """API для управления заявками"""
    queryset = FeedbackRequest.objects.all()
    serializer_class = FeedbackRequestSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]  # Добавляем TokenAuthentication!
    
    def get_serializer_class(self):
        if self.action == 'create' and not self.request.user.is_authenticated:
            return FeedbackRequestCreateSerializer
        return FeedbackRequestSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]  # Разрешаем создание заявок без авторизации
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Фильтрация заявок в зависимости от роли пользователя"""
        user = self.request.user
        queryset = FeedbackRequest.objects.all()
        
        # Временное логирование для отладки
        print(f"DEBUG: User: {user}, Role: {user.role if hasattr(user, 'role') else 'NO ROLE'}, Is authenticated: {user.is_authenticated}")
        print(f"DEBUG: Total feedback requests: {queryset.count()}")
        
        if not user.is_authenticated:
            print("DEBUG: User not authenticated, returning empty queryset")
            return FeedbackRequest.objects.none()
        
        # Супер-админы видят все заявки
        if user.role == 'super-admin' or user.is_superuser:
            print("DEBUG: Super-admin access, returning all")
            return queryset
        
        # Операторы и кураторы видят все заявки
        if user.role in ['operator', 'curator']:
            print("DEBUG: Operator/Curator access, returning all")
            return queryset
        
        # Мастера НЕ должны видеть заявки звонков (как указал пользователь)
        if user.role in ['master', 'warrant-master', 'garant-master']:
            print("DEBUG: Master access, returning empty")
            return FeedbackRequest.objects.none()
        
        print("DEBUG: Unknown role, returning empty")
        return FeedbackRequest.objects.none()
        
        return FeedbackRequest.objects.none()
    
    @action(detail=False, methods=['get'])
    def not_called(self, request):
        """Получить непрозвоненные заявки"""
        print(f"DEBUG not_called: User: {request.user}, Role: {request.user.role}")
        queryset = self.get_queryset().filter(is_called=False)
        print(f"DEBUG not_called: Queryset count: {queryset.count()}")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def called(self, request):
        """Получить обзвоненные заявки"""
        queryset = self.get_queryset().filter(is_called=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_called(self, request, pk=None):
        """Отметить заявку как прозвоненную"""
        feedback = get_object_or_404(FeedbackRequest, pk=pk)
        
        # Проверяем права доступа
        if request.user.role not in ['super-admin', 'operator', 'curator'] and not request.user.is_superuser:
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback.is_called = True
        feedback.called_at = timezone.now()
        feedback.save()
        
        serializer = self.get_serializer(feedback)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_to_master(self, request, pk=None):
        """Назначить заявку мастеру"""
        feedback = get_object_or_404(FeedbackRequest, pk=pk)
        master_id = request.data.get('master_id')
        
        if not master_id:
            return Response(
                {'error': 'Не указан ID мастера'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            master = CustomUser.objects.get(
                id=master_id, 
                role__in=['master', 'garant-master', 'warrant-master']
            )
            feedback.assigned_to = master
            feedback.status = 'in_progress'
            feedback.save()
            
            serializer = self.get_serializer(feedback)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Мастер не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def debug_test(self, request):
        """Debug test endpoint"""
        print(f"DEBUG TEST: User: {request.user}, Role: {request.user.role}")
        print(f"DEBUG TEST: Is authenticated: {request.user.is_authenticated}")
        return Response({"message": "Debug test"})


@api_view(['POST'])
@permission_classes([AllowAny])
def create_feedback_request(request):
    """Создание заявки с лендинг пейджа"""
    serializer = FeedbackRequestCreateSerializer(data=request.data)
    if serializer.is_valid():
        feedback = serializer.save()
        
        # Отправляем уведомление операторам и админам (можно добавить позже)
        # send_notification_to_operators(feedback)
        
        return Response({
            'success': True,
            'message': 'Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.',
            'id': feedback.id
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_public_settings(request):
    """Получить публичные настройки сайта для лендинг пейджа"""
    settings_obj, created = SiteSettings.objects.get_or_create()
    
    # Возвращаем только публичную информацию
    data = {
        'phone': settings_obj.phone,
        'email': settings_obj.email,
        'address': settings_obj.address,
        'working_hours': settings_obj.working_hours,
        'social_media': {
            'facebook': settings_obj.facebook_url,
            'instagram': settings_obj.instagram_url,
            'telegram': settings_obj.telegram_url,
            'whatsapp': settings_obj.whatsapp_url,
        },
        'content': {
            'hero_title': settings_obj.hero_title,
            'hero_subtitle': settings_obj.hero_subtitle,
            'about_title': settings_obj.about_title,
            'about_description': settings_obj.about_description,
        }
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_public_services(request):
    """Получить активные услуги для лендинг пейджа"""
    services = Service.objects.filter(is_active=True).order_by('order', 'name')
    serializer = ServiceSerializer(services, many=True)
    return Response(serializer.data)

# Временная отладочная view
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def debug_feedback(request):
    """Отладочная view для проверки доступа к заявкам"""
    user = request.user
    
    debug_info = {
        'user_id': user.id,
        'user_email': user.email,
        'user_role': user.role,
        'user_is_authenticated': user.is_authenticated,
        'user_is_superuser': user.is_superuser,
    }
    
    # Проверяем условия
    conditions = {
        'is_super_admin': user.role == 'super-admin' or user.is_superuser,
        'is_operator_or_curator': user.role in ['operator', 'curator'],
        'is_master': user.role == 'master',
    }
    
    # Получаем заявки согласно логике
    all_feedback = FeedbackRequest.objects.all()
    
    if not user.is_authenticated:
        allowed_feedback = FeedbackRequest.objects.none()
        reason = "User not authenticated"
    elif user.role == 'super-admin' or user.is_superuser:
        allowed_feedback = all_feedback
        reason = "Super admin - full access"
    elif user.role in ['operator', 'curator']:
        allowed_feedback = all_feedback
        reason = "Operator/Curator - full access"
    elif user.role == 'master':
        allowed_feedback = all_feedback.filter(assigned_to=user)
        reason = "Master - only assigned"
    else:
        allowed_feedback = FeedbackRequest.objects.none()
        reason = f"Unknown role: {user.role}"
    
    result = {
        'debug_info': debug_info,
        'conditions': conditions,
        'reason': reason,
        'total_feedback_in_db': all_feedback.count(),
        'allowed_feedback_count': allowed_feedback.count(),
        'allowed_feedback_items': [
            {
                'id': item.id,
                'name': item.name,
                'phone': item.phone,
                'is_called': item.is_called,
                'assigned_to': item.assigned_to.email if item.assigned_to else None
            }
            for item in allowed_feedback[:5]
        ]
    }
    
    return Response(result)
