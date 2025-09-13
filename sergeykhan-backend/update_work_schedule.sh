#!/bin/bash

# Скрипт для обновления расписания мастеров с 8 до 12 часов работы
# Запуск: bash update_work_schedule.sh

echo "🕘 Обновление расписания мастеров до 12-часового рабочего дня..."

# Применяем миграции
echo "📂 Применение миграций..."
python3 manage.py makemigrations
python3 manage.py migrate

# Проверяем результат
echo "✅ Проверка обновленных данных..."
python3 manage.py shell << EOF
from api1.models import MasterDailySchedule
from datetime import time

# Проверяем обновленные записи
updated_schedules = MasterDailySchedule.objects.filter(work_end_time=time(21, 0))
old_schedules = MasterDailySchedule.objects.filter(work_end_time=time(17, 0))

print(f"✅ Обновлено расписаний: {updated_schedules.count()}")
print(f"⚠️  Старых расписаний осталось: {old_schedules.count()}")

# Показываем пример обновленного расписания
if updated_schedules.exists():
    schedule = updated_schedules.first()
    print(f"📅 Пример обновленного расписания:")
    print(f"   Мастер: {schedule.master.email}")
    print(f"   Время работы: {schedule.work_start_time} - {schedule.work_end_time}")
    print(f"   Максимум слотов: {schedule.max_slots}")
EOF

echo ""
echo "🎉 Обновление расписания завершено!"
echo ""
echo "📝 Что изменилось:"
echo "   • Рабочий день мастеров: 09:00 - 21:00 (было 09:00 - 17:00)"
echo "   • Максимальное количество слотов в день: 12 (было 8)"
echo "   • Добавлены временные слоты: 18:00-19:00, 19:00-20:00, 20:00-21:00"
echo ""
echo "🔄 Не забудьте обновить фронтенд!"
