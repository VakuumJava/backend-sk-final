"""
API представления для завершения заказов
"""
from .utils import *


# ----------------------------------------
#  Завершение заказов мастерами
# ----------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['MASTER'], ROLES['SUPER_ADMIN']])
def complete_order(request, order_id):
    """Завершение заказа мастером"""
    try:
        order = Order.objects.get(id=order_id)
        
        # Проверяем, что заказ назначен текущему мастеру (только для роли мастера)
        if request.user.role == ROLES['MASTER'] and order.assigned_master != request.user:
            return Response({
                'error': 'Заказ не назначен вам'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем статус заказа
        if order.status not in ['выполняется', 'назначен', 'в работе']:
            return Response({
                'error': 'Заказ должен быть в статусе "выполняется", "назначен" или "в работе"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что заказ еще не завершен
        if hasattr(order, 'completion'):
            return Response({
                'error': 'Заказ уже имеет запись о завершении'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Подготавливаем данные
        data = request.data.copy()
        data['order'] = order_id  # Добавляем ID заказа из URL
        
        # Логирование для отладки
        print(f"DEBUG: Получены данные от фронтенда:")
        print(f"DEBUG: request.data = {request.data}")
        print(f"DEBUG: order_id from URL = {order_id}")
        print(f"DEBUG: request.FILES = {request.FILES}")
        
        # Получаем загружаемые фотографии для логирования
        completion_photos = request.FILES.getlist('completion_photos')
        if completion_photos:
            print(f"DEBUG: Найдено {len(completion_photos)} фотографий")
            for i, photo in enumerate(completion_photos):
                print(f"  Фото {i+1}: {photo.name}, размер: {photo.size}, тип: {photo.content_type}")
        else:
            print("DEBUG: Фотографии не найдены")
        
        print(f"DEBUG: Финальные данные для сериализатора: {data}")
        
        # Создаем сериализатор
        serializer = OrderCompletionCreateSerializer(data=data, context={'request': request})
        
        if serializer.is_valid():
            completion = serializer.save()
            
            # Полностью освобождаем слот в расписании - удаляем его
            try:
                from .models import OrderSlot
                order_slots = OrderSlot.objects.filter(order=order)
                if order_slots.exists():
                    slots_count = order_slots.count()
                    order_slots.delete()
                    print(f"DEBUG: Удалено {slots_count} слот(ов) для заказа {order.id} - расписание полностью освобождено")
                else:
                    print(f"DEBUG: У заказа {order.id} нет слотов в расписании")
            except Exception as slot_error:
                print(f"DEBUG: Ошибка при освобождении слота: {str(slot_error)}")
            
            # АВТОМАТИЧЕСКАЯ ОЧИСТКА: удаляем все слоты завершенных заказов у этого мастера
            try:
                master = order.assigned_master
                if master:
                    # Находим все слоты этого мастера с завершенными заказами
                    completed_slots = OrderSlot.objects.filter(
                        master=master,
                        order__status__in=['завершен', 'отклонен']
                    )
                    if completed_slots.exists():
                        completed_count = completed_slots.count()
                        completed_slots.delete()
                        print(f"DEBUG: АВТООЧИСТКА - Удалено {completed_count} слотов завершенных заказов у мастера {master.email}")
                    
                    # Также очищаем слоты с неактуальными статусами
                    outdated_slots = OrderSlot.objects.filter(
                        master=master,
                        status__in=['completed', 'cancelled']
                    )
                    if outdated_slots.exists():
                        outdated_count = outdated_slots.count()
                        outdated_slots.delete()
                        print(f"DEBUG: АВТООЧИСТКА - Удалено {outdated_count} устаревших слотов у мастера {master.email}")
                        
            except Exception as cleanup_error:
                print(f"DEBUG: Ошибка автоматической очистки расписания: {str(cleanup_error)}")
            
            # Логируем действие
            log_order_action(
                order=order,
                action='completed_by_master',
                performed_by=request.user,
                description=f'Заказ завершен мастером. Ожидает подтверждения куратора',
                old_value=f'Статус: {order.status}',
                new_value='Статус: ожидает_подтверждения'
            )
            
            return Response(OrderCompletionSerializer(completion, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        print(f"DEBUG: Ошибки сериализатора: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Order.DoesNotExist:
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"DEBUG: Неожиданная ошибка: {str(e)}")
        return Response({
            'error': 'Внутренняя ошибка сервера',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def get_pending_completions(request):
    """Получение завершений, ожидающих проверки куратором"""
    completions = OrderCompletion.objects.filter(status='ожидает_проверки').order_by('-created_at')
    serializer = OrderCompletionSerializer(completions, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def review_completion(request, completion_id):
    """Проверка завершения заказа куратором"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        
        # Проверяем статус
        if completion.status != 'ожидает_проверки':
            return Response({
                'error': 'Завершение уже проверено'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderCompletionReviewSerializer(completion, data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                action = serializer.validated_data.get('action')
                completion = serializer.save()
                
                # Логируем действие
                action_type = 'completion_approved' if completion.status == 'одобрен' else 'completion_rejected'
                log_order_action(
                    order=completion.order,
                    action=action_type,
                    performed_by=request.user,
                    description=f'Завершение заказа {completion.status} куратором',
                    old_value='ожидает_проверки',
                    new_value=completion.status
                )
                
                # Если одобрено, распределяем средства и завершаем заказ
                result_data = OrderCompletionSerializer(completion, context={'request': request}).data
                if completion.status == 'одобрен':
                    # Обновляем статус заказа на "завершен"
                    completion.order.status = 'завершен'
                    completion.order.save()
                    print(f"DEBUG: Заказ {completion.order.id} переведен в статус 'завершен'")
                    
                    try:
                        distribution = distribute_completion_funds(completion, request.user)
                        if distribution:
                            result_data.update({
                                'master_payment': distribution.get('master_amount', 0),
                                'curator_payment': distribution.get('curator_amount', 0),
                                'company_payment': distribution.get('company_amount', 0)
                            })
                    except Exception as dist_error:
                        # Если ошибка в распределении средств, возвращаем успешный ответ но с предупреждением
                        result_data['distribution_error'] = f'Ошибка распределения средств: {str(dist_error)}'
                    
                    # Полностью удаляем все слоты для завершенного заказа
                    try:
                        from .models import OrderSlot
                        remaining_slots = OrderSlot.objects.filter(order=completion.order)
                        if remaining_slots.exists():
                            slots_count = remaining_slots.count()
                            remaining_slots.delete()
                            print(f"DEBUG: Удалено {slots_count} слотов для одобренного заказа {completion.order.id} - расписание освобождено")
                        else:
                            print(f"DEBUG: У одобренного заказа {completion.order.id} нет слотов для удаления")
                            
                        # АВТОМАТИЧЕСКАЯ ОЧИСТКА при одобрении: удаляем все слоты завершенных заказов у этого мастера
                        master = completion.order.assigned_master
                        if master:
                            # Находим все слоты этого мастера с завершенными заказами
                            completed_slots = OrderSlot.objects.filter(
                                master=master,
                                order__status__in=['завершен', 'отклонен']
                            )
                            if completed_slots.exists():
                                completed_count = completed_slots.count()
                                completed_slots.delete()
                                print(f"DEBUG: АВТООЧИСТКА при одобрении - Удалено {completed_count} слотов завершенных заказов у мастера {master.email}")
                            
                            # Также очищаем слоты с неактуальными статусами
                            outdated_slots = OrderSlot.objects.filter(
                                master=master,
                                status__in=['completed', 'cancelled']
                            )
                            if outdated_slots.exists():
                                outdated_count = outdated_slots.count()
                                outdated_slots.delete()
                                print(f"DEBUG: АВТООЧИСТКА при одобрении - Удалено {outdated_count} устаревших слотов у мастера {master.email}")
                                
                    except Exception as slot_error:
                        print(f"DEBUG: Ошибка при удалении слотов: {str(slot_error)}")
                        result_data['slot_warning'] = f'Предупреждение: не удалось освободить слоты - {str(slot_error)}'
                
                elif completion.status == 'отклонен':
                    # Если завершение отклонено, возвращаем заказ в статус "выполняется"
                    completion.order.status = 'выполняется'
                    completion.order.save()
                    print(f"DEBUG: Заказ {completion.order.id} возвращен в статус 'выполняется'")
                    
                    # Восстанавливаем слот для продолжения работы
                    try:
                        from .models import OrderSlot, MasterDailySchedule
                        order = completion.order
                        
                        # Создаем слот для продолжения работы
                        from datetime import date, time
                        today = date.today()
                        master = order.assigned_master
                        
                        if master:
                            # Создаем простой слот без привязки к расписанию
                            OrderSlot.objects.create(
                                master=master,
                                order=order,
                                slot_date=today,
                                slot_time=time(9, 0),  # 9:00 утра
                                slot_number=1,
                                status='in_progress'
                            )
                            print(f"DEBUG: Создан новый слот для отклоненного заказа {order.id}")
                            
                            # АВТОМАТИЧЕСКАЯ ОЧИСТКА при отклонении: удаляем завершенные заказы из расписания
                            completed_slots = OrderSlot.objects.filter(
                                master=master,
                                order__status__in=['завершен', 'отклонен']
                            ).exclude(order=order)  # Исключаем текущий заказ
                            if completed_slots.exists():
                                completed_count = completed_slots.count()
                                completed_slots.delete()
                                print(f"DEBUG: АВТООЧИСТКА при отклонении - Удалено {completed_count} слотов завершенных заказов у мастера {master.email}")
                        
                    except Exception as slot_error:
                        print(f"DEBUG: Ошибка при восстановлении слота: {str(slot_error)}")
                        result_data['slot_warning'] = f'Предупреждение: не удалось восстановить слот - {str(slot_error)}'
                
                return Response(result_data)
                
            except Exception as save_error:
                return Response({
                    'error': 'Ошибка при сохранении завершения',
                    'details': str(save_error)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Запись о завершении не найдена'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Внутренняя ошибка сервера',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def get_completion_distribution(request, completion_id):
    """Просмотр расчета распределения средств"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        distribution = completion.calculate_distribution()
        
        if distribution:
            distribution['net_profit'] = completion.net_profit
            serializer = OrderCompletionDistributionSerializer(distribution)
            return Response(serializer.data)
        else:
            return Response({'error': 'Распределение недоступно'}, status=status.HTTP_400_BAD_REQUEST)
            
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Запись о завершении не найдена'}, status=status.HTTP_404_NOT_FOUND)


def distribute_completion_funds(completion, curator):
    """Распределение средств после одобрения завершения с учетом настроек"""
    if completion.is_distributed:
        return {
            'master_amount': 0,
            'curator_amount': 0,
            'company_amount': 0,
        }
    
    distribution = completion.calculate_distribution()
    if not distribution:
        return {
            'master_amount': 0,
            'curator_amount': 0,
            'company_amount': 0,
        }
    
    try:
        # Ensure all monetary values are Decimal to avoid type errors
        master_immediate = Decimal(str(distribution['master_immediate']))
        master_deferred = Decimal(str(distribution['master_deferred']))
        curator_share = Decimal(str(distribution['curator_share']))
        company_share = Decimal(str(distribution['company_share']))
        
        # Логируем начало распределения
        log_order_action(
            order=completion.order,
            action='distribution_started',
            performed_by=curator,
            description=f'Начало распределения средств: {distribution["settings_used"]} для заказа #{completion.order.id}'
        )
        
        # 1. Выплата мастеру: к выплате идет в "Выплачено", к балансу = выплата + баланс
        
        # 1.1. К выплате (идет в кошелек "Выплачено")
        master_balance, created = Balance.objects.get_or_create(user=completion.master)
        old_master_balance = master_balance.amount
        master_balance.amount += master_immediate
        master_balance.save()
        
        # 1.2. К балансу (сумма выплаты + баланса, идет отдельно)
        # Здесь нужно добавить логику для баланса мастера, если есть отдельная модель
        total_to_balance = master_immediate + master_deferred
        
        # Логируем транзакцию выплаты (идет в "Выплачено")
        FinancialTransaction.objects.create(
            user=completion.master,
            order_completion=completion,
            transaction_type='master_payment',
            amount=master_immediate,
            description=f'К выплате за завершение заказа #{completion.order.id} ({distribution["settings_details"]["master_paid_percent"]}%)'
        )
        
        # Логируем транзакцию баланса (общая сумма)
        FinancialTransaction.objects.create(
            user=completion.master,
            order_completion=completion,
            transaction_type='master_balance_total',
            amount=total_to_balance,
            description=f'К балансу за завершение заказа #{completion.order.id}: выплата {master_immediate} ({distribution["settings_details"]["master_paid_percent"]}%) + баланс {master_deferred} ({distribution["settings_details"]["master_balance_percent"]}%) = {total_to_balance}'
        )
        
        # Логируем изменение выплаченного баланса мастера (только к выплате)
        BalanceLog.objects.create(
            user=completion.master,
            action_type='top_up',
            amount=master_immediate,
            reason=f'К выплате за заказ #{completion.order.id} ({distribution["settings_details"]["master_paid_percent"]}%)',
            performed_by=curator,
            old_value=old_master_balance,
            new_value=master_balance.amount
        )
        
        # 2. Выплата куратору (процент из настроек)
        curator_balance, created = Balance.objects.get_or_create(user=curator)
        old_curator_balance = curator_balance.amount
        curator_balance.amount += curator_share
        curator_balance.save()
        
        FinancialTransaction.objects.create(
            user=curator,
            order_completion=completion,
            transaction_type='curator_payment',
            amount=curator_share,
            description=f'Выплата куратору за одобрение заказа #{completion.order.id} ({distribution["settings_details"]["curator_percent"]}%)'
        )
        
        BalanceLog.objects.create(
            user=curator,
            action_type='top_up',  # Используем правильный action_type
            amount=curator_share,
            reason=f'Выплата за проверку заказа #{completion.order.id} ({distribution["settings_details"]["curator_percent"]}%)',
            performed_by=curator,
            old_value=old_curator_balance,
            new_value=curator_balance.amount
        )
        
        # 3. Доход компании (процент из настроек)
        company_balance = CompanyBalance.objects.first()
        if company_balance:
            old_company_balance = company_balance.amount
            company_balance.amount += company_share
            company_balance.save()
            
            CompanyBalanceLog.objects.create(
                action_type='top_up',  # Используем правильный action_type
                amount=company_share,
                reason=f'Доход от завершения заказа #{completion.order.id} ({distribution["settings_details"]["company_percent"]}%)',
                performed_by=curator,
                old_value=old_company_balance,
                new_value=company_balance.amount
            )
        
        FinancialTransaction.objects.create(
            user=curator,
            order_completion=completion,
            transaction_type='company_income',
            amount=company_share,
            description=f'Доход компании от заказа #{completion.order.id} ({distribution["settings_details"]["company_percent"]}%)'
        )
        
        # Отмечаем как распределено
        completion.is_distributed = True
        completion.save()
        
        # Логируем успешное завершение
        total_to_balance = master_immediate + master_deferred
        total_master_percent = distribution["settings_details"]["master_paid_percent"] + distribution["settings_details"]["master_balance_percent"]
        log_order_action(
            order=completion.order,
            action='distribution_completed',
            performed_by=curator,
            description=f'Распределение средств завершено: мастер к выплате {master_immediate} ({distribution["settings_details"]["master_paid_percent"]}%), к балансу {total_to_balance} ({total_master_percent}%), куратор {curator_share} ({distribution["settings_details"]["curator_percent"]}%), компания {company_share} ({distribution["settings_details"]["company_percent"]}%)'
        )
        
        # Возвращаем информацию о распределенных средствах
        return {
            'master_amount_paid': master_immediate,  # К выплате
            'master_amount_balance': total_to_balance,  # К балансу
            'curator_amount': curator_share,
            'company_amount': company_share,
        }
        
    except Exception as e:
        # В случае ошибки логируем
        log_order_action(
            order=completion.order,
            action='distribution_error',
            performed_by=curator,
            description=f'Ошибка распределения средств: {str(e)}'
        )
        raise


# Дополнительные функции для завершения заказов
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_master_completions(request):
    """Получение завершений мастера"""
    completions = OrderCompletion.objects.filter(master=request.user).order_by('-created_at')
    serializer = OrderCompletionSerializer(completions, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_all_completions(request):
    """Получение всех завершений (для админов)"""
    completions = OrderCompletion.objects.all().order_by('-created_at')
    serializer = OrderCompletionSerializer(completions, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_completion_detail(request, completion_id):
    """Получение детальной информации о завершении"""
    try:
        completion = OrderCompletion.objects.get(id=completion_id)
        serializer = OrderCompletionSerializer(completion, context={'request': request})
        return Response(serializer.data)
    except OrderCompletion.DoesNotExist:
        return Response({'error': 'Completion not found'}, status=status.HTTP_404_NOT_FOUND)


# ----------------------------------------
#  Утилиты для очистки расписания
# ----------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['MASTER'], ROLES['CURATOR'], ROLES['SUPER_ADMIN']])
def cleanup_completed_orders_from_schedule(request):
    """
    Очистка расписания от завершенных заказов.
    Удаляет слоты для заказов в статусе 'завершен'.
    """
    try:
        from .models import Order, OrderSlot
        
        # Найдем все завершенные заказы со слотами
        completed_orders = Order.objects.filter(status='завершен')
        cleaned_count = 0
        
        for order in completed_orders:
            slots = OrderSlot.objects.filter(order=order)
            if slots.exists():
                slots_count = slots.count()
                slots.delete()
                cleaned_count += slots_count
                print(f"DEBUG: Удалено {slots_count} слотов для завершенного заказа #{order.id}")
        
        # Также очистим заказы в статусе 'ожидает_подтверждения' с одобренным завершением
        pending_orders = Order.objects.filter(status='ожидает_подтверждения')
        for order in pending_orders:
            if hasattr(order, 'completion') and order.completion.status == 'одобрен':
                # Такой заказ должен иметь статус 'завершен'
                order.status = 'завершен'
                order.save()
                print(f"DEBUG: Заказ #{order.id} переведен в статус 'завершен'")
                
                # Удалим слоты
                slots = OrderSlot.objects.filter(order=order)
                if slots.exists():
                    slots_count = slots.count()
                    slots.delete()
                    cleaned_count += slots_count
                    print(f"DEBUG: Удалено {slots_count} слотов для заказа #{order.id}")
        
        return Response({
            'success': True,
            'message': f'Расписание очищено',
            'cleaned_slots': cleaned_count
        })
        
    except Exception as e:
        return Response({
            'error': 'Ошибка при очистке расписания',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
