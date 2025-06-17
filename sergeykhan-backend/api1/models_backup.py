from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from rest_framework import serializers, viewsets, permissions
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
        return f"{self.username} ({self.role})"


class Balance(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='balance')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Balance: {self.user.email} - {self.amount}"


# Order Model
class Order(models.Model):
    STATUS_CHOICES = (
        ('новый', 'Новый'),
        ('в обработке', 'В обработке'),
        ('назначен', 'Назначен мастеру'),
        ('выполняется', 'Выполняется'),
        ('завершен', 'Завершен'),
    )



    client_name = models.CharField(max_length=255)
    client_phone = models.CharField(max_length=20)
    description = models.TextField()
    address = models.CharField(max_length=255, null=True, blank=True)  # Добавляем адрес
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='новый')
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
    )

    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expenses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.client_name} ({self.status})"


# Contact Model
class Contact(models.Model):
    STATUS_CHOICES = (
        ('обзвонен', 'Обзвонен'),
        ('не обзвонен', 'Не обзвонен'),
    )
    
    name = models.CharField(max_length=255)
    number = models.CharField(max_length=50)
    date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='не обзвонен')
    
    def __str__(self):
        return f"{self.name} - {self.number} ({self.status})"


class IsCurator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'curator'

class IsOperator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'operator'

class IsMaster(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'master'



class BalanceLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=100)  # пополнение, списание и т.п.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.amount}"

# Распределение прибыли
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
    Настройки для двухэтапного распределения прибыли:
    1. Автоматический расчёт чистой прибыли и авансов
    2. Распределение финансов куратором
    """
    
    # Этап 1: Автоматический расчёт чистой прибыли
    # Чистая прибыль = сумма заказа - расходы мастера
    advance_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Аванс мастеру (% от чистой прибыли)"
    )
    initial_kassa_percent = models.PositiveIntegerField(
        default=70, 
        help_text="Сумма для передачи в кассу (% от чистой прибыли)"
    )
    
    # Этап 2: Распределение финансов куратором
    # Куратор распределяет деньги, полученные от мастера
    cash_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Наличные мастеру сразу (% от общей суммы)"
    )
    balance_percent = models.PositiveIntegerField(
        default=30, 
        help_text="Зачисление на баланс мастеру (% от общей суммы)"
    )
    curator_percent = models.PositiveIntegerField(
        default=5, 
        help_text="Зарплата куратору (% от общей суммы)"
    )
    final_kassa_percent = models.PositiveIntegerField(
        default=35, 
        help_text="Касса компании (% от общей суммы)"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'role__in': ['super-admin', 'admin']}
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
                'advance_percent': 30,
                'initial_kassa_percent': 70,
                'cash_percent': 30,
                'balance_percent': 30,
                'curator_percent': 5,
                'final_kassa_percent': 35
            }
        )
        return settings
    
    def clean(self):
        """Валидация: проверяем, что сумма процентов в каждом этапе = 100%"""
        from django.core.exceptions import ValidationError
        
        # Этап 1: Аванс + Касса = 100%
        stage1_total = self.advance_percent + self.initial_kassa_percent
        if stage1_total != 100:
            raise ValidationError(
                f'Сумма процентов этапа 1 должна быть 100%, а не {stage1_total}%'
            )
        
        # Этап 2: Наличные + Баланс + Куратор + Касса = 100%
        stage2_total = (
            self.cash_percent + self.balance_percent + 
            self.curator_percent + self.final_kassa_percent
        )
        if stage2_total != 100:
            raise ValidationError(
                f'Сумма процентов этапа 2 должна быть 100%, а не {stage2_total}%'
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# История распределения прибыли по заказам
class OrderProfitDistribution(models.Model):
    """
    Модель для хранения истории распределения прибыли по конкретному заказу
    """
    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        related_name='profit_distribution'
    )
    
    # Расчёты этапа 1 (автоматические)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    master_expenses = models.DecimalField(max_digits=10, decimal_places=2)
    net_profit = models.DecimalField(max_digits=10, decimal_places=2)  # order_total - master_expenses
    
    master_advance = models.DecimalField(max_digits=10, decimal_places=2)  # 30% от чистой прибыли
    kassa_amount_stage1 = models.DecimalField(max_digits=10, decimal_places=2)  # 70% от чистой прибыли
    
    # Расчёты этапа 2 (куратором)
    master_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 30% наличными
    master_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 30% на баланс
    curator_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 5% куратору
    final_kassa_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 35% в кассу
    
    # Статус и метаданные
    is_stage1_completed = models.BooleanField(default=True)  # Этап 1 всегда автоматический
    is_stage2_completed = models.BooleanField(default=False)  # Этап 2 выполняется куратором
    
    calculated_at = models.DateTimeField(auto_now_add=True)
    stage2_completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_curator = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        limit_choices_to={'role': 'curator'}
    )
    
    def __str__(self):
        return f"Распределение прибыли для заказа #{self.order.id}"
    
    @property
    def total_distributed(self):
        """Общая сумма распределённых средств"""
        return (
            self.master_advance + self.master_cash + self.master_balance + 
            self.curator_salary + self.final_kassa_amount
        )
    
    def calculate_stage1(self, settings=None):
        """Автоматический расчёт этапа 1"""
        if not settings:
            settings = ProfitDistributionSettings.get_settings()
        
        self.order_total = self.order.final_cost or 0
        self.master_expenses = self.order.expenses or 0
        self.net_profit = self.order_total - self.master_expenses
        
        self.master_advance = (Decimal(settings.advance_percent) / 100) * self.net_profit
        self.kassa_amount_stage1 = (Decimal(settings.initial_kassa_percent) / 100) * self.net_profit
        
        self.is_stage1_completed = True
    
    def complete_stage2(self, curator_user, settings=None):
        """Завершение этапа 2 куратором"""
        if not settings:
            settings = ProfitDistributionSettings.get_settings()
        
        # Рассчитываем от общей суммы заказа
        total = self.order_total
        
        self.master_cash = (Decimal(settings.cash_percent) / 100) * total
        self.master_balance = (Decimal(settings.balance_percent) / 100) * total
        self.curator_salary = (Decimal(settings.curator_percent) / 100) * total
        self.final_kassa_amount = (Decimal(settings.final_kassa_percent) / 100) * total
        
        self.is_stage2_completed = True
        self.stage2_completed_at = timezone.now()
        self.completed_by_curator = curator_user


class CompanyBalance(models.Model):
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    @classmethod
    def get_instance(cls):
        instance, created = cls.objects.get_or_create(id=1)
        return instance

    def __str__(self):
        return f"Company Balance: {self.amount}"

# Календарные события для мастеров
class CalendarEvent(models.Model):
    master = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'master'},
        related_name='calendar_events'
    )
    title = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')  # HEX цвет
    all_day = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start']
        verbose_name = 'Календарное событие'
        verbose_name_plural = 'Календарные события'

    def __str__(self):
        return f"{self.title} - {self.master.email} ({self.start})"


class OrderLog(models.Model):
    """Модель для логирования действий с заказами"""
    ACTION_CHOICES = [
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
    ]
      order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Log for Order {self.order.id}: {self.get_action_display()}"
    
    class Meta:
        ordering = ['-created_at']


class TransactionLog(models.Model):
    """Модель для логирования финансовых транзакций"""
    TRANSACTION_TYPE_CHOICES = [
        ('balance_top_up', 'Пополнение баланса'),
        ('balance_deduct', 'Списание с баланса'),
        ('profit_distribution', 'Распределение прибыли'),
        ('master_payment', 'Выплата мастеру'),
        ('curator_salary', 'Зарплата куратору'),
        ('company_income', 'Доход компании'),
    ]
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='performed_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.amount} - {self.description[:50]}"
    
    class Meta:
        ordering = ['-created_at']
