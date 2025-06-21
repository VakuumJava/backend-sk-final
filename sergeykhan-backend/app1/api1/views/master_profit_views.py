"""
Модуль для управления индивидуальными настройками прибыли мастеров.
Позволяет администраторам настраивать процентные ставки для каждого мастера индивидуально.
"""

from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import CustomUser, MasterProfitSettings, ProfitDistributionSettings
from ..serializers import MasterProfitSettingsSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_master_profit_settings(request, master_id):
    """
    Получить настройки распределения прибыли для конкретного мастера.
    Доступно: администраторам и самому мастеру.
    """
    try:
        master = get_object_or_404(CustomUser, id=master_id, role='master')
        
        # Проверяем права доступа
        if request.user.role not in ['super-admin'] and request.user.id != master_id:
            return Response(
                {'error': 'У вас нет прав для просмотра этих настроек'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем настройки для мастера
        settings_data = MasterProfitSettings.get_settings_for_master(master)
        
        return Response({
            'master_id': master.id,
            'master_name': master.get_full_name() or master.email,
            'settings': settings_data
        })
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения настроек: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def set_master_profit_settings(request, master_id):
    """
    Создать или обновить индивидуальные настройки распределения прибыли для мастера.
    Доступно только администраторам.
    """
    if request.user.role not in ['super-admin']:
        return Response(
            {'error': 'У вас нет прав для изменения настроек'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        master = get_object_or_404(CustomUser, id=master_id, role='master')
        
        # Получаем данные из запроса
        data = request.data.copy()
        data['master'] = master.id
        
        # Проверяем что сумма процентов = 100%
        total_percent = (
            data.get('master_paid_percent', 0) +
            data.get('master_balance_percent', 0) +
            data.get('curator_percent', 0) +
            data.get('company_percent', 0)
        )
        
        if total_percent != 100:
            return Response(
                {'error': f'Сумма всех процентов должна быть 100%. Текущая сумма: {total_percent}%'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Получаем или создаем настройки
            settings, created = MasterProfitSettings.objects.get_or_create(
                master=master,
                defaults={
                    'master_paid_percent': data.get('master_paid_percent', 30),
                    'master_balance_percent': data.get('master_balance_percent', 30),
                    'curator_percent': data.get('curator_percent', 5),
                    'company_percent': data.get('company_percent', 35),
                    'is_active': data.get('is_active', True),
                    'created_by': request.user,
                    'updated_by': request.user,
                }
            )
            
            if not created:
                # Обновляем существующие настройки
                settings.master_paid_percent = data.get('master_paid_percent', settings.master_paid_percent)
                settings.master_balance_percent = data.get('master_balance_percent', settings.master_balance_percent)
                settings.curator_percent = data.get('curator_percent', settings.curator_percent)
                settings.company_percent = data.get('company_percent', settings.company_percent)
                settings.is_active = data.get('is_active', settings.is_active)
                settings.updated_by = request.user
                settings.save()
            
            serializer = MasterProfitSettingsSerializer(settings)
            
            return Response({
                'message': 'Настройки успешно сохранены',
                'settings': serializer.data,
                'created': created
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
    except Exception as e:
        return Response(
            {'error': f'Ошибка сохранения настроек: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_master_profit_settings(request, master_id):
    """
    Удалить индивидуальные настройки мастера (вернуться к глобальным).
    Доступно только администраторам.
    """
    if request.user.role not in ['super-admin']:
        return Response(
            {'error': 'У вас нет прав для удаления настроек'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        master = get_object_or_404(CustomUser, id=master_id, role='master')
        
        settings = MasterProfitSettings.objects.filter(master=master).first()
        if settings:
            settings.delete()
            return Response({'message': 'Индивидуальные настройки удалены. Мастер будет использовать глобальные настройки.'})
        else:
            return Response({'message': 'У мастера нет индивидуальных настроек.'})
            
    except Exception as e:
        return Response(
            {'error': f'Ошибка удаления настроек: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_masters_with_settings(request):
    """
    Получить список всех мастеров с их настройками прибыли.
    Доступно только администраторам.
    """
    if request.user.role not in ['super-admin']:
        return Response(
            {'error': 'У вас нет прав для просмотра этой информации'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        masters = CustomUser.objects.filter(role='master').order_by('first_name', 'last_name')
        masters_data = []
        
        for master in masters:
            settings_data = MasterProfitSettings.get_settings_for_master(master)
            masters_data.append({
                'id': master.id,
                'name': master.get_full_name() or master.email,
                'email': master.email,
                'has_individual_settings': settings_data['is_individual'],
                'settings': settings_data
            })
        
        return Response({
            'masters': masters_data,
            'total_count': len(masters_data)
        })
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения данных: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_profit_preview(request, order_id):
    """
    Получить предварительный расчет распределения прибыли для заказа.
    Показывает какие проценты будут применены к заказу.
    """
    try:
        from ..models import Order
        
        order = get_object_or_404(Order, id=order_id)
        
        # Проверяем права доступа
        if request.user.role not in ['super-admin'] and request.user.id != order.assigned_master_id:
            return Response(
                {'error': 'У вас нет прав для просмотра этой информации'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем настройки прибыли для заказа
        profit_settings = order.get_profit_settings()
        
        return Response({
            'order_id': order.id,
            'assigned_master': {
                'id': order.assigned_master.id if order.assigned_master else None,
                'name': order.assigned_master.get_full_name() if order.assigned_master else None
            },
            'profit_settings': profit_settings,
            'final_cost': str(order.final_cost) if order.final_cost else None,
            'estimated_distribution': {
                'master_paid': str((order.final_cost or 0) * profit_settings['master_paid_percent'] / 100) if order.final_cost else None,
                'master_balance': str((order.final_cost or 0) * profit_settings['master_balance_percent'] / 100) if order.final_cost else None,
                'curator_balance': str((order.final_cost or 0) * profit_settings['curator_percent'] / 100) if order.final_cost else None,
                'company_cash': str((order.final_cost or 0) * profit_settings['company_percent'] / 100) if order.final_cost else None,
            } if order.final_cost else None
        })
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка получения предварительного расчета: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
