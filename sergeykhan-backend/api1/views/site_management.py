from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone

from ..models import SiteSettings, Service, FeedbackRequest, CustomUser
from ..serializers import (
    SiteSettingsSerializer, ServiceSerializer, FeedbackRequestSerializer,
    FeedbackRequestCreateSerializer
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
        if not request.user.is_authenticated or request.user.role not in ['super_admin', 'super-admin']:
            return Response(
                {'error': 'Доступ запрещен. Только супер-админы могут изменять настройки.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Если pk передан, используем его, иначе получаем первый объект
        if pk:
            try:
                settings_obj = SiteSettings.objects.get(pk=pk)
            except SiteSettings.DoesNotExist:
                return Response(
                    {'error': 'Настройки не найдены'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            settings_obj, created = SiteSettings.objects.get_or_create()
            
        serializer = self.get_serializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Частичное обновление настроек сайта"""
        return self.update(request, pk)
    
    def retrieve(self, request, pk=None):
        """Получить конкретные настройки по ID"""
        try:
            settings_obj = SiteSettings.objects.get(pk=pk)
            serializer = self.get_serializer(settings_obj)
            return Response(serializer.data)
        except SiteSettings.DoesNotExist:
            return Response(
                {'error': 'Настройки не найдены'},
                status=status.HTTP_404_NOT_FOUND
            )
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
            self.request.user.role in ['super_admin', 'super-admin'] or 
            self.request.user.is_superuser
        ):
            # Админы видят все услуги, включая неактивные
            return Service.objects.all()
        # Обычные пользователи видят только активные услуги
        return Service.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Создание услуги"""
        if not self.request.user.is_authenticated or self.request.user.role not in ['super_admin', 'super-admin']:
            raise PermissionError('Доступ запрещен')
        serializer.save()
    
    def perform_update(self, serializer):
        """Обновление услуги"""
        if not self.request.user.is_authenticated or self.request.user.role not in ['super_admin', 'super-admin']:
            raise PermissionError('Доступ запрещен')
        serializer.save()
    
    def perform_destroy(self, instance):
        """Мягкое удаление услуги"""
        if not self.request.user.is_authenticated or self.request.user.role not in ['super_admin', 'super-admin']:
            raise PermissionError('Доступ запрещен')
        instance.is_active = False
        instance.save()


class FeedbackRequestViewSet(viewsets.ModelViewSet):
    """API для управления заявками"""
    queryset = FeedbackRequest.objects.all()
    serializer_class = FeedbackRequestSerializer
    permission_classes = [IsAuthenticated]
    
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
        
        if not user.is_authenticated:
            return FeedbackRequest.objects.none()
        
        # Супер-админы видят все заявки
        if user.role in ['super_admin', 'super-admin'] or user.is_superuser:
            return queryset
        
        # Операторы видят все заявки
        if user.role == 'operator':
            return queryset
        
        # Мастера видят только назначенные им заявки
        if user.role == 'master':
            return queryset.filter(assigned_to=user)
        
        return FeedbackRequest.objects.none()
    
    @action(detail=False, methods=['get'])
    def not_called(self, request):
        """Получить непрозвоненные заявки"""
        queryset = self.get_queryset().filter(is_called=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_called(self, request, pk=None):
        """Отметить заявку как прозвоненную"""
        feedback = get_object_or_404(FeedbackRequest, pk=pk)
        
        # Проверяем права доступа
        if request.user.role not in ['super_admin', 'super-admin', 'operator'] and not request.user.is_superuser:
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
            master = CustomUser.objects.get(id=master_id, role='master')
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
