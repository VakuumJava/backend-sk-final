from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta, time
import uuid


# Custom User Manager
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


# Custom User Model
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('master', 'Мастер'),
        ('operator', 'Оператор'),
        ('warrant-master', 'Гарантийный мастер'),
        ('super-admin', 'Супер админ'),
        ('curator', 'Куратор'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='master')
    # Уровень дистанционки: 0 - нет, 1 - 4 часа, 2 - 24 часа
    dist = models.PositiveSmallIntegerField(default=0)
    # Флаг ручной установки дистанционки (не пересчитывать автоматически)
    distance_manual_override = models.BooleanField(default=False)
    username = None
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"


class Balance(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='balance')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Текущий баланс
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Выплаченная сумма за все время

    def __str__(self):
        return f"Balance: {self.user.email} - Current: {self.amount}, Paid: {self.paid_amount}"


# Order Model
class Order(models.Model):
    STATUS_CHOICES = (
        ('новый', 'Новый'),
        ('в обработке', 'В обработке'),
        ('назначен', 'Назначен мастеру'),
        ('выполняется', 'Выполняется'),
        ('ожидает_подтверждения', 'Ожидает подтверждения'),  # Новый статус
        ('завершен', 'Завершен'),
        ('отклонен', 'Отклонен'),  # Новый статус
    )

    client_name = models.CharField(max_length=255)
    client_phone = models.CharField(max_length=20)
    description = models.TextField()
    
    # Раздельные поля адреса
    street = models.CharField(max_length=255, null=True, blank=True, verbose_name='Улица')
    house_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='Номер дома')
    apartment = models.CharField(max_length=50, null=True, blank=True, verbose_name='Квартира')
    entrance = models.CharField(max_length=50, null=True, blank=True, verbose_name='Подъезд')
    
    # Объединенный адрес для обратной совместимости
    address = models.CharField(max_length=255, null=True, blank=True)
    
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='новый')
    is_test = models.BooleanField(default=False)  # Поле для указания тестового заказа

    operator = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={'role': 'operator'},
        related_name='processed_orders'
    )

    curator = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={'role': 'curator'},
        related_name='assigned_orders'
    )

    assigned_master = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={'role': 'master'},
        related_name='orders'
    )
    transferred_to = models.ForeignKey(
        CustomUser,
        related_name='transferred_orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )    # Scheduling fields
    scheduled_date = models.DateField(null=True, blank=True, verbose_name='Дата выполнения')
    scheduled_time = models.TimeField(null=True, blank=True, verbose_name='Время выполнения')    
    # Дополнительные поля заказа
    service_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='Тип услуги')
    equipment_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='Тип оборудования')
    promotion = models.CharField(max_length=255, null=True, blank=True, verbose_name='Акции')
    due_date = models.DateField(null=True, blank=True, verbose_name='Срок исполнения')
    
    # Планирование и дополнительная информация
    PAYMENT_METHOD_CHOICES = (
        ('наличные', 'Наличные'),
        ('карта', 'Банковская карта'),
        ('перевод', 'Банковский перевод'),
        ('элсом', 'Элсом'),
        ('mbанк', 'МБанк'),
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='наличные', verbose_name='Способ оплаты')
    notes = models.TextField(null=True, blank=True, verbose_name='Дополнительные заметки')
    
    # Financial fields
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.client_name} ({self.status})"
    
    def get_full_address(self):
        """Возвращает полный адрес со всеми деталями"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.house_number:
            parts.append(self.house_number)
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        if self.entrance:
            parts.append(f"подъезд {self.entrance}")
        return ", ".join(parts) if parts else self.address or ""
    
    def get_public_address(self):
        """Возвращает публичный адрес без квартиры и подъезда (для мастеров до взятия заказа)"""
        parts = []
        if self.street:        parts.append(self.street)
        if self.house_number:
            parts.append(self.house_number)
        return ", ".join(parts) if parts else ""
    
    def save(self, *args, **kwargs):
        """Автоматически обновляем поле address при сохранении"""
        if not self.address:
            self.address = self.get_full_address()
        super().save(*args, **kwargs)
    
    def get_profit_settings(self):
        """
        Получить настройки распределения прибыли для данного заказа.
        Использует индивидуальные настройки мастера, если есть и активны,
        иначе глобальные настройки.
        """
        if self.assigned_master:
            return MasterProfitSettings.get_settings_for_master(self.assigned_master)
        else:
            # Если мастер не назначен, используем глобальные настройки
            global_settings = ProfitDistributionSettings.get_settings()
            return {
                'master_paid_percent': global_settings.master_paid_percent,
                'master_balance_percent': global_settings.master_balance_percent,
                'curator_percent': global_settings.curator_percent,
                'company_percent': global_settings.company_percent,
                'is_individual': False,
                'settings_id': None            }


class BalanceLog(models.Model):
    BALANCE_TYPE_CHOICES = (
        ('current', 'Текущий баланс'),
        ('paid', 'Выплаченная сумма'),
    )
    
    ACTION_TYPE_CHOICES = (
        ('top_up', 'Пополнение'),
        ('deduct', 'Списание'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='logs')
    balance_type = models.CharField(max_length=10, choices=BALANCE_TYPE_CHOICES, default='current')
    action_type = models.CharField(max_length=10, choices=ACTION_TYPE_CHOICES, default='top_up')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(default='')  # Причина изменения
    performed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='balance_changes_performed'
    )
    old_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    new_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Сохраняем старые поля для совместимости
    action = models.CharField(max_length=100, default='legacy')  # старое поле для совместимости
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_balance_type_display()} - {self.get_action_type_display()} - {self.amount}"

# Распределение прибыли (старая модель - для совместимости)
class ProfitDistribution(models.Model):
    master_percent = models.PositiveIntegerField(default=60)
    curator_percent = models.PositiveIntegerField(default=5)
    operator_percent = models.PositiveIntegerField(default=5)
    kassa = models.PositiveIntegerField(default=30)

    def __str__(self):
        return "Profit Distribution Settings"


# Улучшенная модель для детального распределения прибыли
class ProfitDistributionSettings(models.Model):
    """
    Настройки для распределения прибыли при завершении заказа:
    - Мастеру: master_paid_percent (сразу выплачено) + master_balance_percent (на баланс)
    - Куратору: curator_percent (на баланс)
    - Компании: company_percent (в кассу)
    """
    
    # Распределение средств при завершении заказа
    master_paid_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Процент мастеру сразу в выплачено"
    )
    master_balance_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Процент мастеру на баланс"
    )
    curator_percent = models.PositiveIntegerField(
        default=5, 
        help_text="Процент куратору на баланс"
    )
    company_percent = models.PositiveIntegerField(
        default=35, 
        help_text="Процент в кассу компании"
    )
    
    # Устаревшие поля для обратной совместимости
    advance_percent = models.PositiveIntegerField(default=30, help_text="Устарело")
    initial_kassa_percent = models.PositiveIntegerField(default=70, help_text="Устарело")
    cash_percent = models.PositiveIntegerField(default=30, help_text="Устарело")
    balance_percent = models.PositiveIntegerField(default=30, help_text="Устарело")
    final_kassa_percent = models.PositiveIntegerField(default=35, help_text="Устарело")    # Метаданные
    is_active = models.BooleanField(default=True, help_text="Активность настроек")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='created_profit_settings',
        limit_choices_to={'role__in': ['super-admin', 'admin']},
        help_text="Кто создал настройки"
    )
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='updated_profit_settings',
        limit_choices_to={'role__in': ['super-admin', 'admin']},
        help_text="Кто последний раз обновил настройки"
    )
    
    class Meta:
        verbose_name = "Настройки распределения прибыли"
        verbose_name_plural = "Настройки распределения прибыли"
    
    def __str__(self):
        return f"Настройки распределения прибыли (обновлено: {self.updated_at})"
    
    @staticmethod
    def get_settings():
        """Получить текущие настройки (создать если не существуют)"""
        settings, created = ProfitDistributionSettings.objects.get_or_create(
            id=1,
            defaults={
                'master_paid_percent': 30,
                'master_balance_percent': 30,
                'curator_percent': 5,
                'company_percent': 35,
                # Устаревшие значения для совместимости
                'advance_percent': 30,
                'initial_kassa_percent': 70,
                'cash_percent': 30,
                'balance_percent': 30,
                'final_kassa_percent': 35
            }
        )
        return settings
    
    def clean(self):
        """Валидация: проверяем, что сумма процентов = 100%"""
        from django.core.exceptions import ValidationError
        
        # Проверяем новую схему распределения
        total = (
            self.master_paid_percent + self.master_balance_percent + 
            self.curator_percent + self.company_percent
        )
        if total != 100:
            raise ValidationError(
                f'Сумма всех процентов должна быть 100%, а не {total}%'
            )
    
    @property
    def total_master_percent(self):
        """Общий процент мастера"""
        return self.master_paid_percent + self.master_balance_percent
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)



class CalendarEvent(models.Model):
    master = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='calendar_events')
    title = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    color = models.CharField(max_length=7, default='#6366F1')

    def __str__(self):
        return f'{self.title} ({self.start} - {self.end})'



class Contact(models.Model):
    STATUS_CHOICES = (
        ('обзвонен', 'Обзвонен'),
        ('не обзвонен', 'Не обзвонен'),
    )
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='не обзвонен'
    )

    def __str__(self):
        return f"{self.name} ({self.number}) - {self.status}"




class CompanyBalance(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Company Kassa: {self.amount}"

    @staticmethod
    def get_instance():
        instance, _ = CompanyBalance.objects.get_or_create(id=1)
        return instance


class CompanyBalanceLog(models.Model):
    ACTION_TYPE_CHOICES = (
        ('top_up', 'Пополнение'),
        ('deduct', 'Списание'),
    )
    
    action_type = models.CharField(max_length=10, choices=ACTION_TYPE_CHOICES, default='top_up')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(default='')  # Причина изменения
    performed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='company_balance_changes_performed'
    )
    old_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    new_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Company Balance - {self.get_action_type_display()} - {self.amount}"


class DistanceSettingsModel(models.Model):
    """Модель для хранения настроек дистанционки в базе данных"""
    
    # Обычная дистанционка
    average_check_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=65000,
        help_text="Пороговое значение среднего чека для обычной дистанционки"
    )
    visible_period_standard = models.PositiveIntegerField(
        default=28,
        help_text="Количество часов видимости для обычной дистанционки"
    )
    
    # Суточная дистанционка
    daily_order_sum_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=350000,
        help_text="Пороговое значение суммы заказов в сутки для суточной дистанционки"
    )
    net_turnover_threshold = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=1500000,
        help_text="Пороговое значение чистого вала за 10 дней для суточной дистанционки"
    )
    visible_period_daily = models.PositiveIntegerField(
        default=48,
        help_text="Количество часов видимости для суточной дистанционки"
    )
    
    # Метаданные
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'role': 'super-admin'}
    )
    
    class Meta:
        verbose_name = "Настройки дистанционки"
        verbose_name_plural = "Настройки дистанционки"
    
    def __str__(self):
        return f"Настройки дистанционки (обновлено: {self.updated_at})"
    
    @staticmethod
    def get_settings():
        """Получить текущие настройки (создать если не существуют)"""
        settings, created = DistanceSettingsModel.objects.get_or_create(
            id=1,
            defaults={
                'average_check_threshold': 65000,
                'visible_period_standard': 28,
                'daily_order_sum_threshold': 350000,
                'net_turnover_threshold': 1500000,
                'visible_period_daily': 48
            }
        )
        return settings

# Модель для логирования изменений заказов
class OrderLog(models.Model):
    ACTION_CHOICES = (
        ('created', 'Заказ создан'),
        ('status_changed', 'Статус изменен'),
        ('master_assigned', 'Мастер назначен'),
        ('master_removed', 'Мастер снят'),
        ('transferred', 'Переведен на гарантию'),
        ('completed', 'Завершен'),
        ('deleted', 'Удален'),
        ('updated', 'Обновлен'),
        ('cost_updated', 'Стоимость обновлена'),
        ('approved', 'Одобрен'),
    )
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    description = models.TextField()
    old_value = models.TextField(null=True, blank=True)  # Старое значение
    new_value = models.TextField(null=True, blank=True)  # Новое значение
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order {self.order.id} - {self.action} by {self.performed_by}"


# Модель для логирования транзакций
class TransactionLog(models.Model):
    TRANSACTION_TYPES = (
        ('balance_top_up', 'Пополнение баланса'),
        ('balance_deduct', 'Списание с баланса'),
        ('paid_amount_top_up', 'Пополнение выплаченной суммы'),
        ('paid_amount_deduct', 'Списание с выплаченной суммы'),
        ('profit_distribution', 'Распределение прибыли'),
        ('master_payment', 'Выплата мастеру'),
        ('curator_salary', 'Зарплата куратору'),
        ('company_income', 'Доход компании'),
        ('company_expense', 'Расход компании'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)  # Связь с заказом, если применимо
    performed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='performed_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.user}"


# Master Availability Model for scheduling
class MasterAvailability(models.Model):
    master = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'master'},
        related_name='availability_slots'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'date', 'start_time'], 
                name='unique_master_availability'
            )
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        
        # Check for overlapping availability slots
        if self.pk:
            overlapping = MasterAvailability.objects.filter(
                master=self.master,
                date=self.date,
            ).exclude(pk=self.pk).filter(
                models.Q(start_time__lt=self.end_time) & 
                models.Q(end_time__gt=self.start_time)
            )
        else:
            overlapping = MasterAvailability.objects.filter(
                master=self.master,
                date=self.date,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            )
        
        if overlapping.exists():
            raise ValidationError("This time slot overlaps with existing availability")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.master.email} - {self.date} ({self.start_time}-{self.end_time})"


# Order Completion Model - новая модель для завершения заказов мастером
class OrderCompletion(models.Model):
    COMPLETION_STATUS_CHOICES = [
        ('ожидает_проверки', 'Ожидает проверки'),
        ('одобрен', 'Одобрен'),
        ('отклонен', 'Отклонен'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='completion')
    master = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'master'})
    
    # Данные о завершении работы
    work_description = models.TextField(verbose_name="Описание выполненных работ")
    completion_photos = models.JSONField(default=list, blank=True, verbose_name="Фотографии выполненных работ")
    
    # Финансовые данные
    parts_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Расходы на запчасти (₸)")
    transport_costs = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Транспортные расходы (₸)")
    total_received = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Полная сумма получена за заказ (₸)")
    
    # Автоматически рассчитываемые поля
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Общие расходы (₸)")
    net_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Чистая прибыль (₸)")
    
    # Даты и статус
    completion_date = models.DateTimeField(verbose_name="Дата завершения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    status = models.CharField(max_length=20, choices=COMPLETION_STATUS_CHOICES, default='ожидает_проверки', verbose_name="Статус")
      # Проверка куратором
    curator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_completions', limit_choices_to={'role': 'curator'})
    review_date = models.DateTimeField(null=True, blank=True, verbose_name="Дата проверки")
    curator_notes = models.TextField(blank=True, null=True, verbose_name="Заметки куратора")
    
    # Распределение средств
    is_distributed = models.BooleanField(default=False, verbose_name="Средства распределены")
    
    def save(self, *args, **kwargs):
        # Автоматический расчет общих расходов и чистой прибыли        self.total_expenses = self.parts_expenses + self.transport_costs
        self.net_profit = self.total_received - self.total_expenses
        super().save(*args, **kwargs)
        
    def calculate_distribution(self):
        """Рассчитывает распределение средств на основе настроек - индивидуальных для мастера или глобальных"""
        if self.status != 'одобрен' or self.is_distributed:
            return None
            
        # Получаем настройки распределения для этого мастера
        master = self.order.assigned_master or self.order.transferred_to
        if not master:
            return None
            
        # Получаем индивидуальные настройки мастера или глобальные
        from .models import MasterProfitSettings  # Избегаем циклического импорта
        settings = MasterProfitSettings.get_settings_for_master(master)
        
        # Используем новые поля для распределения
        master_immediate = self.net_profit * (Decimal(settings['master_paid_percent']) / 100)
        master_deferred = self.net_profit * (Decimal(settings['master_balance_percent']) / 100)
        master_total = master_immediate + master_deferred
        
        # Доля компании
        company_share = self.net_profit * (Decimal(settings['company_percent']) / 100)        
        # Доля куратору
        curator_share = self.net_profit * (Decimal(settings['curator_percent']) / 100)
        
        return {
            'master_immediate': master_immediate,
            'master_deferred': master_deferred,
            'master_total': master_total,
            'company_share': company_share,
            'curator_share': curator_share,
            'settings_used': 'individual' if settings['is_individual'] else 'global',
            'settings_details': {
                'master_paid_percent': settings['master_paid_percent'],
                'master_balance_percent': settings['master_balance_percent'],
                'curator_percent': settings['curator_percent'],
                'company_percent': settings['company_percent']
            }
        }
    
    class Meta:
        verbose_name = "Завершение заказа"
        verbose_name_plural = "Завершения заказов"
    
    def __str__(self):
        return f"Завершение заказа {self.order.id} мастером {self.master.email if self.master else 'не указан'}"


# Модель для логирования финансовых транзакций
class FinancialTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('order_completion', 'Завершение заказа'),
        ('master_payment', 'Выплата мастеру'),
        ('curator_payment', 'Выплата куратору'),
        ('company_income', 'Доход компании'),
        ('master_deferred', 'Отложенная выплата мастеру'),
        ('master_balance_total', 'К балансу мастера (общая сумма)'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions')
    order_completion = models.ForeignKey(OrderCompletion, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=25, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Финансовая транзакция"
        verbose_name_plural = "Финансовые транзакции"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_transaction_type_display()} - {self.amount}₸"


# Модель для логирования системных действий
class SystemLog(models.Model):
    ACTION_CHOICES = [
        ('settings_updated', 'Настройки обновлены'),
        ('percentage_settings_updated', 'Настройки процентов обновлены'),
        ('company_balance_updated', 'Баланс компании обновлён'),
        ('system_maintenance', 'Системное обслуживание'),
        ('user_role_changed', 'Роль пользователя изменена'),
        ('backup_created', 'Резервная копия создана'),
        ('data_import', 'Импорт данных'),
        ('data_export', 'Экспорт данных'),
    ]
    
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Дополнительные данные
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Системный лог"
        verbose_name_plural = "Системные логи"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.performed_by.email if self.performed_by else 'Система'} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# Индивидуальные настройки распределения прибыли для каждого мастера
class MasterProfitSettings(models.Model):
    """
    Индивидуальные настройки распределения прибыли для конкретного мастера.
    Если для мастера не настроены индивидуальные проценты, используются глобальные.
    """
    
    master = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'master'},
        related_name='profit_settings',
        verbose_name='Мастер'
    )
    
    # Распределение средств при завершении заказа
    master_paid_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Процент мастеру сразу в выплачено",
        verbose_name="Процент на выплату (%)"
    )
    master_balance_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Процент мастеру на баланс",
        verbose_name="Процент на баланс (%)"
    )
    curator_percent = models.PositiveIntegerField(
        default=5, 
        help_text="Процент куратору на баланс",
        verbose_name="Процент куратору (%)"
    )
    company_percent = models.PositiveIntegerField(
        default=35, 
        help_text="Процент в кассу компании",
        verbose_name="Процент компании (%)"
    )
    
    # Активность настроек
    is_active = models.BooleanField(
        default=True,
        help_text="Использовать индивидуальные настройки или глобальные",
        verbose_name="Активно"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        limit_choices_to={'role__in': ['super-admin']},
        related_name='created_master_profit_settings',
        verbose_name="Создал"
    )
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        limit_choices_to={'role__in': ['super-admin']},
        related_name='updated_master_profit_settings',
        verbose_name="Обновил"
    )
    
    class Meta:
        verbose_name = 'Настройки распределения прибыли мастера'
        verbose_name_plural = 'Настройки распределения прибыли мастеров'
        ordering = ['master__first_name', 'master__last_name']
    
    def __str__(self):
        status = "активные" if self.is_active else "неактивные"
        return f'Настройки для {self.master.get_full_name() or self.master.email} ({status})'
    
    def clean(self):
        """Валидация: сумма процентов должна быть 100%"""
        total = (
            self.master_paid_percent + 
            self.master_balance_percent + 
            self.curator_percent + 
            self.company_percent
        )
        if total != 100:
            raise ValidationError(
                f'Сумма всех процентов должна быть равна 100%. '
                f'Текущая сумма: {total}%'
            )
    
    @property
    def total_master_percent(self):
        """Общий процент мастера (выплачено + баланс)"""
        return self.master_paid_percent + self.master_balance_percent
    
    @staticmethod
    def get_settings_for_master(master):
        """
        Получить настройки распределения для конкретного мастера.
        Если у мастера нет индивидуальных настроек или они неактивны,
        возвращает глобальные настройки.
        """
        try:
            settings = MasterProfitSettings.objects.get(master=master, is_active=True)
            return {
                'master_paid_percent': settings.master_paid_percent,
                'master_balance_percent': settings.master_balance_percent,
                'curator_percent': settings.curator_percent,
                'company_percent': settings.company_percent,
                'is_individual': True,
                'settings_id': settings.id
            }
        except MasterProfitSettings.DoesNotExist:
            # Используем глобальные настройки
            global_settings = ProfitDistributionSettings.get_settings()
            return {
                'master_paid_percent': global_settings.master_paid_percent,
                'master_balance_percent': global_settings.master_balance_percent,
                'curator_percent': global_settings.curator_percent,
                'company_percent': global_settings.company_percent,
                'is_individual': False,
                'settings_id': None
            }
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# Website Content Management Models
class Service(models.Model):
    """Модель для услуг сайта"""
    name = models.CharField(max_length=255, verbose_name='Название услуги')
    description = models.TextField(verbose_name='Описание услуги')
    price_from = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, 
        verbose_name='Цена от'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class SiteSettings(models.Model):
    """Модель для настроек сайта"""
    phone = models.CharField(
        max_length=20, 
        default='+7 (777) 123-45-67',
        verbose_name='Телефон'
    )
    email = models.EmailField(
        default='info@sergeykhan.kz',
        verbose_name='Email'
    )
    address = models.CharField(
        max_length=255,
        default='г. Алматы',
        verbose_name='Адрес'
    )
    working_hours = models.CharField(
        max_length=100,
        default='24/7',
        verbose_name='Часы работы'
    )
    facebook_url = models.URLField(null=True, blank=True, verbose_name='Facebook URL')
    instagram_url = models.URLField(null=True, blank=True, verbose_name='Instagram URL')
    telegram_url = models.URLField(null=True, blank=True, verbose_name='Telegram URL')
    whatsapp_url = models.URLField(null=True, blank=True, verbose_name='WhatsApp URL')
    hero_title = models.CharField(
        max_length=255,
        default='Профессиональный ремонт бытовой техники',
        verbose_name='Заголовок Hero секции'
    )
    hero_subtitle = models.TextField(
        default='Быстро, качественно, с гарантией',
        verbose_name='Подзаголовок Hero секции'
    )
    about_title = models.CharField(
        max_length=255,
        default='Почему выбирают нас',
        verbose_name='Заголовок О нас'
    )
    about_description = models.TextField(
        default='Мы предоставляем качественные услуги ремонта',
        verbose_name='Описание О нас'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return f"Настройки сайта (ID: {self.id})"


class FeedbackRequest(models.Model):
    """Модель для заявок с сайта"""
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    ]

    name = models.CharField(max_length=255, verbose_name='Имя')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(null=True, blank=True, verbose_name='Email')
    service = models.ForeignKey(
        Service, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        verbose_name='Услуга'
    )
    message = models.TextField(blank=True, verbose_name='Сообщение')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name='Статус'
    )
    is_called = models.BooleanField(default=False, verbose_name='Прозвонен')
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Назначен'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True)
    called_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата звонка')

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка от {self.name} ({self.phone})"


# Order Slot Model for Slot-based Scheduling
class OrderSlot(models.Model):
    """
    Модель для связывания заказов со слотами времени.
    1 заказ = 1 слот, каждый слот имеет определенное время и дату.
    """
    
    master = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'master'},
        related_name='order_slots',
        verbose_name='Мастер'
    )
    
    order = models.OneToOneField(
        'Order',
        on_delete=models.CASCADE,
        related_name='slot',
        verbose_name='Заказ'
    )
    
    # Слот информация
    slot_date = models.DateField(verbose_name='Дата слота')
    slot_time = models.TimeField(verbose_name='Время слота')
    slot_number = models.PositiveIntegerField(verbose_name='Номер слота в дне')  # 1, 2, 3, 4, etc.
    slot_duration = models.DurationField(default=timedelta(hours=2), verbose_name='Длительность слота')  # По умолчанию 2 часа
    
    # Статус слота
    STATUS_CHOICES = [
        ('reserved', 'Зарезервирован'),
        ('confirmed', 'Подтвержден'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reserved', verbose_name='Статус слота')
    
    # Дополнительные поля
    notes = models.TextField(blank=True, verbose_name='Заметки к слоту')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['slot_date', 'slot_time', 'slot_number']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'slot_date', 'slot_number'],
                name='unique_master_daily_slot'
            )
        ]
        verbose_name = 'Слот заказа'
        verbose_name_plural = 'Слоты заказов'
    
    def __str__(self):
        return f"Слот {self.slot_number} - {self.master.email} ({self.slot_date} {self.slot_time})"
    
    def get_slot_display_name(self):
        """Возвращает наглядное название слота"""
        return f"Слот {self.slot_number} ({self.slot_time.strftime('%H:%M')})"
    
    def get_end_time(self):
        """Вычисляет время окончания слота"""
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(self.slot_date, self.slot_time)
        end_datetime = start_datetime + self.slot_duration
        return end_datetime.time()
    
    def is_available_for_new_order(self):
        """Проверяет, доступен ли слот для нового заказа"""
        return self.status in ['cancelled'] or not self.order
    
    @classmethod
    def get_available_slots_for_master(cls, master, date=None):
        """Получить доступные слоты для мастера на определенную дату"""
        from datetime import date as dt_date
        if date is None:
            date = dt_date.today()
        
        # Получаем все слоты мастера на дату
        occupied_slots = cls.objects.filter(
            master=master,
            slot_date=date,
            status__in=['reserved', 'confirmed', 'in_progress']
        ).values_list('slot_number', flat=True)
        
        # Возвращаем номера свободных слотов (предполагаем максимум 8 слотов в день)
        max_slots = 8
        all_slots = set(range(1, max_slots + 1))
        available_slot_numbers = all_slots - set(occupied_slots)
        
        return sorted(list(available_slot_numbers))
    
    @classmethod
    def create_slot_for_order(cls, order, master, slot_date, slot_number, slot_time):
        """Создать слот для заказа"""
        slot = cls.objects.create(
            master=master,
            order=order,
            slot_date=slot_date,
            slot_time=slot_time,
            slot_number=slot_number,
            status='reserved'
        )
        
        # Обновляем поля заказа
        order.scheduled_date = slot_date
        order.scheduled_time = slot_time
        order.save()
        
        return slot


# Master Daily Schedule Model для отображения всех слотов дня
class MasterDailySchedule(models.Model):
    """
    Модель для отображения расписания мастера на день со всеми слотами
    """
    
    master = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'master'},
        related_name='daily_schedules',
        verbose_name='Мастер'
    )
    
    date = models.DateField(verbose_name='Дата')
    
    # Конфигурация рабочего дня
    work_start_time = models.TimeField(default='09:00:00', verbose_name='Начало рабочего дня')
    work_end_time = models.TimeField(default='17:00:00', verbose_name='Конец рабочего дня')
    slot_duration = models.DurationField(default=timedelta(hours=2), verbose_name='Длительность слота')
    max_slots = models.PositiveIntegerField(default=8, verbose_name='Максимум слотов в день')
    
    # Статус дня
    is_working_day = models.BooleanField(default=True, verbose_name='Рабочий день')
    notes = models.TextField(blank=True, verbose_name='Заметки к дню')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
        constraints = [
            models.UniqueConstraint(
                fields=['master', 'date'],
                name='unique_master_daily_schedule'
            )
        ]
        verbose_name = 'Расписание дня мастера'
        verbose_name_plural = 'Расписания дней мастеров'
    
    def __str__(self):
        return f"{self.master.email} - {self.date}"
    
    def get_all_slots(self):
        """Получить все слоты дня с информацией о занятости"""
        from datetime import datetime, timedelta
        
        slots = []
        current_time = datetime.combine(self.date, self.work_start_time)
        end_time = datetime.combine(self.date, self.work_end_time)
        
        slot_number = 1
        while current_time + self.slot_duration <= end_time and slot_number <= self.max_slots:
            # Проверяем, есть ли заказ в этом слоте
            try:
                order_slot = OrderSlot.objects.get(
                    master=self.master,
                    slot_date=self.date,
                    slot_number=slot_number
                )
                slot_info = {
                    'slot_number': slot_number,
                    'time': current_time.time(),
                    'end_time': (current_time + self.slot_duration).time(),
                    'is_occupied': True,
                    'order': order_slot.order,
                    'order_slot': order_slot,
                    'status': order_slot.status
                }
            except OrderSlot.DoesNotExist:
                slot_info = {
                    'slot_number': slot_number,
                    'time': current_time.time(),
                    'end_time': (current_time + self.slot_duration).time(),
                    'is_occupied': False,
                    'order': None,
                    'order_slot': None,
                    'status': 'free'                }
            slots.append(slot_info)
            current_time += self.slot_duration
            slot_number += 1
        
        return slots
    
    def get_free_slots_count(self):
        """Получить количество свободных слотов"""
        slots = self.get_all_slots()
        return len([slot for slot in slots if not slot['is_occupied']])
    
    def get_occupied_slots_count(self):
        """Получить количество занятых слотов"""
        slots = self.get_all_slots()
        return len([slot for slot in slots if slot['is_occupied']])
    
    @classmethod
    def get_or_create_for_master_date(cls, master, date):
        """Получить или создать расписание для мастера на дату"""
        schedule, created = cls.objects.get_or_create(
            master=master,
            date=date,
            defaults={
                'work_start_time': time(9, 0),  # 09:00
                'work_end_time': time(17, 0),   # 17:00
                'slot_duration': timedelta(hours=2),
                'max_slots': 8,
                'is_working_day': True
            }
        )
        return schedule
