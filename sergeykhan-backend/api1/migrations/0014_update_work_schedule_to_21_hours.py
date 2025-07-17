# Generated migration to update work schedule from 17:00 to 21:00

from django.db import migrations, models
from datetime import time

def update_work_schedule(apps, schema_editor):
    """
    Обновляет существующие расписания мастеров:
    - Время окончания работы с 17:00 на 21:00
    - Максимальное количество слотов с 8 на 12
    """
    MasterDailySchedule = apps.get_model('api1', 'MasterDailySchedule')
    
    # Обновляем все существующие расписания
    MasterDailySchedule.objects.filter(
        work_end_time='17:00:00'
    ).update(
        work_end_time='21:00:00',
        max_slots=12
    )
    
    # Обновляем записи где max_slots = 8 на 12
    MasterDailySchedule.objects.filter(
        max_slots=8
    ).update(
        max_slots=12
    )

def reverse_work_schedule(apps, schema_editor):
    """
    Откатывает изменения расписания обратно к 17:00
    """
    MasterDailySchedule = apps.get_model('api1', 'MasterDailySchedule')
    
    # Откатываем изменения
    MasterDailySchedule.objects.filter(
        work_end_time='21:00:00'
    ).update(
        work_end_time='17:00:00',
        max_slots=8
    )

class Migration(migrations.Migration):

    dependencies = [
        ('api1', '0013_masterdailyschedule_orderslot'),
    ]

    operations = [
        # Сначала обновляем значения по умолчанию в модели
        migrations.AlterField(
            model_name='masterdailyschedule',
            name='work_end_time',
            field=models.TimeField(default='21:00:00', verbose_name='Конец рабочего дня'),
        ),
        migrations.AlterField(
            model_name='masterdailyschedule',
            name='max_slots',
            field=models.PositiveIntegerField(default=12, verbose_name='Максимум слотов в день'),
        ),
        
        # Затем обновляем существующие данные
        migrations.RunPython(
            update_work_schedule,
            reverse_work_schedule
        ),
    ]
