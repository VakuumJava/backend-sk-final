# 🕘 Обновление расписания мастеров до 12-часового рабочего дня

## Что изменилось

### Backend изменения:
- **Рабочее время**: С 09:00-17:00 (8 часов) на 09:00-21:00 (12 часов)
- **Количество слотов**: С 8 до 12 слотов в день
- **Новые временные слоты**: 18:00-19:00, 19:00-20:00, 20:00-21:00

### Обновленные файлы:

#### Backend:
- `api1/models.py` - MasterDailySchedule модель
- `api1/views/order_views.py` - временные слоты для заказов
- `api1/capacity_analysis.py` - анализ пропускной способности
- `api1/migrations/0014_update_work_schedule_to_21_hours.py` - миграция

#### Frontend:
- `apps/curator/components/users-management/MasterAvailabilityCalendar.tsx`
- `packages/ui/src/components/shared/orders/SlotSelectionModal.tsx`
- `packages/ui/src/components/shared/work-schedule/WorkScheduleTable.tsx`

## Применение изменений

### На локальном сервере:
```bash
cd backend-sk-final/sergeykhan-backend
./update_work_schedule.sh
```

### На Railway (продакшен):
1. Деплойте обновленный код
2. Railway автоматически применит миграции
3. Проверьте логи деплоя для подтверждения

### Проверка результата:
```python
# В Django shell:
from api1.models import MasterDailySchedule
from datetime import time

# Проверяем обновленные записи
schedules = MasterDailySchedule.objects.filter(work_end_time=time(21, 0))
print(f"Обновлено расписаний: {schedules.count()}")

# Проверяем пример расписания
if schedules.exists():
    schedule = schedules.first()
    print(f"Время работы: {schedule.work_start_time} - {schedule.work_end_time}")
    print(f"Максимум слотов: {schedule.max_slots}")
```

## Новые временные слоты

| Время | Слот | Описание |
|-------|------|----------|
| 09:00-11:00 | 1 | Утро |
| 11:00-13:00 | 2 | Утро |
| 13:00-15:00 | 3 | День |
| 15:00-17:00 | 4 | День |
| 17:00-19:00 | 5 | **Новый** Вечер |
| 19:00-21:00 | 6 | **Новый** Вечер |

## Влияние на систему

### Увеличенная пропускная способность:
- **Было**: 4 слота × мастеров = пропускная способность
- **Стало**: 6 слотов × мастеров = +50% пропускная способность

### Анализ нагрузки:
- Обновлен расчет в `capacity_analysis.py`
- Новый максимум заказов на мастера в день: 4 заказа (было 2-3)

### Пользовательский интерфейс:
- Добавлены новые временные слоты в календарях
- Обновлены компоненты выбора времени
- Расширена таблица расписания

## Откат изменений (если нужно)

Если требуется откатить изменения:

```python
# В Django shell:
from api1.models import MasterDailySchedule
from datetime import time

# Откат к старому расписанию
MasterDailySchedule.objects.filter(
    work_end_time=time(21, 0)
).update(
    work_end_time=time(17, 0),
    max_slots=8
)
```

## Контроль качества

Убедитесь что после обновления:
- ✅ Мастера могут видеть новые временные слоты
- ✅ Заказы можно назначать на вечернее время (18:00-21:00)  
- ✅ Анализ пропускной способности показывает правильные цифры
- ✅ Календари показывают все 12 слотов в день
