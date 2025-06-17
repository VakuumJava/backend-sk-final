from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
import json
from .models import CustomUser as User, MasterAvailability
from .serializers import MasterAvailabilitySerializer
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def master_schedule_view(request, master_id=None):
    """
    GET: Получить расписание мастера
    POST: Сохранить расписание мастера
    """
    try:
        # Получаем пользователя из токена
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Token '):
            return JsonResponse({'error': 'Token required'}, status=401)
        
        token = auth_header.split(' ')[1]
        try:
            from django.contrib.auth.models import Group
            from rest_framework.authtoken.models import Token as AuthToken
            auth_token = AuthToken.objects.get(key=token)
            user = auth_token.user
        except:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        # Определяем мастера для работы
        if master_id:
            # Куратор/супер-админ запрашивает расписание конкретного мастера
            if user.role not in ['curator', 'super-admin']:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            try:
                target_user = User.objects.get(id=master_id, role='master')
            except User.DoesNotExist:
                return JsonResponse({'error': 'Master not found'}, status=404)
        else:
            # Мастер запрашивает свое расписание
            if user.role != 'master':
                return JsonResponse({'error': 'Only masters can access their schedule'}, status=403)
            target_user = user

        if request.method == 'GET':
            return get_master_schedule(target_user)
        elif request.method == 'POST':
            return save_master_schedule(request, target_user)
            
    except Exception as e:
        logger.error(f"Error in master_schedule_view: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def get_master_schedule(master_user):
    """Получить расписание мастера из базы данных"""
    try:
        # Получаем все доступные слоты мастера
        availability_slots = MasterAvailability.objects.filter(
            master=master_user,
            date__gte=date.today()
        ).order_by('date', 'start_time')
        
        # Группируем слоты по датам
        schedule_by_date = {}
        for slot in availability_slots:
            date_str = slot.date.strftime('%Y-%m-%d')
            if date_str not in schedule_by_date:
                schedule_by_date[date_str] = []
            
            schedule_by_date[date_str].append({
                'id': slot.id,
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'created_at': slot.created_at.isoformat() if slot.created_at else None
            })
        
        # Формируем итоговое расписание
        schedule = []
        for date_str, slots in schedule_by_date.items():
            schedule.append({
                'date': date_str,
                'slots': slots
            })
        
        return JsonResponse({
            'success': True,
            'schedule': schedule,
            'master_id': master_user.id,
            'master_email': master_user.email,
            'total_slots': availability_slots.count()
        })
    except Exception as e:
        logger.error(f"Error getting schedule for master {master_user.id}: {str(e)}")
        return JsonResponse({'error': 'Failed to get schedule'}, status=500)

def save_master_schedule(request, master_user):
    """Сохранить расписание мастера в базу данных"""
    try:
        data = json.loads(request.body)
        schedule_data = data.get('schedule', [])
        
        logger.info(f"Saving schedule for master {master_user.id}: {schedule_data}")
        
        # Валидируем данные
        for day_schedule in schedule_data:
            if 'date' not in day_schedule or 'slots' not in day_schedule:
                return JsonResponse({'error': 'Invalid schedule format'}, status=400)
            
            # Проверяем формат даты
            try:
                datetime.strptime(day_schedule['date'], '%Y-%m-%d')
            except ValueError:
                return JsonResponse({'error': 'Invalid date format'}, status=400)
            
            # Проверяем слоты
            if not isinstance(day_schedule['slots'], list):
                return JsonResponse({'error': 'Slots must be a list'}, status=400)
                
            # Валидируем каждый слот
            for slot in day_schedule['slots']:
                if 'start_time' not in slot or 'end_time' not in slot:
                    return JsonResponse({'error': 'Each slot must have start_time and end_time'}, status=400)
                
                try:
                    start_time = datetime.strptime(slot['start_time'], '%H:%M').time()
                    end_time = datetime.strptime(slot['end_time'], '%H:%M').time()
                    if start_time >= end_time:
                        return JsonResponse({'error': 'End time must be after start time'}, status=400)
                except ValueError:
                    return JsonResponse({'error': 'Invalid time format. Use HH:MM'}, status=400)
        
        # Сохраняем в базу данных с транзакцией
        with transaction.atomic():
            # Удаляем существующие слоты для будущих дат
            dates_to_update = [day_schedule['date'] for day_schedule in schedule_data]
            MasterAvailability.objects.filter(
                master=master_user,
                date__in=dates_to_update,
                date__gte=date.today()
            ).delete()
            
            # Создаем новые слоты
            created_slots = []
            for day_schedule in schedule_data:
                schedule_date = datetime.strptime(day_schedule['date'], '%Y-%m-%d').date()
                
                # Проверяем, что дата не в прошлом
                if schedule_date < date.today():
                    continue
                    
                for slot in day_schedule['slots']:
                    start_time = datetime.strptime(slot['start_time'], '%H:%M').time()
                    end_time = datetime.strptime(slot['end_time'], '%H:%M').time()
                    
                    # Создаем слот
                    availability_slot = MasterAvailability.objects.create(
                        master=master_user,
                        date=schedule_date,
                        start_time=start_time,
                        end_time=end_time
                    )
                    created_slots.append(availability_slot)
            
            logger.info(f"Successfully created {len(created_slots)} availability slots for master {master_user.id}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Schedule saved successfully. Created {len(created_slots)} slots.',
            'created_slots': len(created_slots),
            'master_id': master_user.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error saving schedule for master {master_user.id}: {str(e)}")
        return JsonResponse({'error': f'Failed to save schedule: {str(e)}'}, status=500)
        
        return JsonResponse({
            'success': True,
            'message': 'Schedule saved successfully',
            'master_id': master_user.id,
            'saved_days': len(schedule_data)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error saving schedule for master {master_user.id}: {str(e)}")
        return JsonResponse({'error': 'Failed to save schedule'}, status=500)
