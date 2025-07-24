from rest_framework import serializers
from django.utils import timezone
from .models import (
    Order, CustomUser, Balance, BalanceLog, CalendarEvent, Contact, OrderLog, 
    TransactionLog, MasterAvailability, CompanyBalance, CompanyBalanceLog, 
    OrderCompletion, FinancialTransaction, SystemLog, MasterProfitSettings,
    ProfitDistributionSettings, SiteSettings, Service, FeedbackRequest
)


class OrderSerializer(serializers.ModelSerializer):
    """Основной сериализатор заказов - возвращает все поля"""
    full_address = serializers.CharField(source='get_full_address', read_only=True)
    public_address = serializers.CharField(source='get_public_address', read_only=True)
    completion = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = '__all__'
    
    def get_completion(self, obj):
        """Возвращает информацию о завершении заказа, если она есть"""
        try:
            if hasattr(obj, 'completion') and obj.completion:
                completion_data = {
                    'id': obj.completion.id,
                    'status': obj.completion.status,
                    'created_at': obj.completion.created_at,
                    'work_description': obj.completion.work_description,
                    'parts_expenses': obj.completion.parts_expenses,
                    'transport_costs': obj.completion.transport_costs,
                    'total_received': obj.completion.total_received,
                    'completion_date': obj.completion.completion_date,
                    'curator_notes': obj.completion.curator_notes,
                    'completion_photos': []
                }
                
                # Преобразуем пути к фотографиям в полные URL
                if obj.completion.completion_photos:
                    request = self.context.get('request')
                    if request:
                        photo_urls = []
                        for photo_path in obj.completion.completion_photos:
                            if photo_path.startswith('completion_photos/'):
                                full_url = request.build_absolute_uri(f'/media/{photo_path}')
                            else:
                                full_url = request.build_absolute_uri(f'/media/completion_photos/{photo_path}')
                            photo_urls.append(full_url)
                        completion_data['completion_photos'] = photo_urls
                    else:
                        completion_data['completion_photos'] = obj.completion.completion_photos
                
                return completion_data
        except:
            pass
        return None


class OrderPublicSerializer(serializers.ModelSerializer):
    """Публичный сериализатор для мастеров до взятия заказа - скрывает приватную информацию"""
    public_address = serializers.CharField(source='get_public_address', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'description', 'status', 'estimated_cost', 'final_cost', 
            'created_at', 'client_name', 'street', 'house_number', 'public_address'
        ]
        # Исключаем квартиру, подъезд и телефон клиента


class OrderDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для взятых заказов - показывает всю информацию включая email-адреса"""
    full_address = serializers.CharField(source='get_full_address', read_only=True)
    public_address = serializers.CharField(source='get_public_address', read_only=True)
    assigned_master_email = serializers.CharField(source='assigned_master.email', read_only=True)
    operator_email = serializers.CharField(source='operator.email', read_only=True)
    curator_email = serializers.CharField(source='curator.email', read_only=True)
    transferred_to_email = serializers.CharField(source='transferred_to.email', read_only=True)
    completion = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = '__all__'
    
    def get_completion(self, obj):
        """Возвращает информацию о завершении заказа, если она есть"""
        try:
            if hasattr(obj, 'completion') and obj.completion:
                completion_data = {
                    'id': obj.completion.id,
                    'status': obj.completion.status,
                    'created_at': obj.completion.created_at,
                    'work_description': obj.completion.work_description,
                    'parts_expenses': obj.completion.parts_expenses,
                    'transport_costs': obj.completion.transport_costs,
                    'total_received': obj.completion.total_received,
                    'completion_date': obj.completion.completion_date,
                    'curator_notes': obj.completion.curator_notes,
                    'completion_photos': []
                }
                
                # Преобразуем пути к фотографиям в полные URL
                if obj.completion.completion_photos:
                    request = self.context.get('request')
                    if request:
                        photo_urls = []
                        for photo_path in obj.completion.completion_photos:
                            if photo_path.startswith('completion_photos/'):
                                full_url = request.build_absolute_uri(f'/media/{photo_path}')
                            else:
                                full_url = request.build_absolute_uri(f'/media/completion_photos/{photo_path}')
                            photo_urls.append(full_url)
                        completion_data['completion_photos'] = photo_urls
                    else:
                        completion_data['completion_photos'] = obj.completion.completion_photos
                
                return completion_data
        except Exception as e:
            print(f"Error getting completion data: {e}")
            pass
        return None


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            password=password,
            role=validated_data.get('role', 'master')
        )
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance



class BalanceSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = Balance
        fields = ['user', 'user_email', 'user_role', 'amount', 'paid_amount']


class BalanceLogSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    balance_type_display = serializers.CharField(source='get_balance_type_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = BalanceLog
        fields = ['id', 'balance_type', 'balance_type_display', 'action_type', 'action_type_display', 
                 'amount', 'reason', 'performed_by', 'performed_by_email', 'old_value', 'new_value', 'created_at']


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = ['id', 'title', 'start', 'end', 'color']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class OrderLogSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    
    class Meta:
        model = OrderLog
        fields = ['id', 'order', 'action', 'performed_by', 'performed_by_email', 'description', 'old_value', 'new_value', 'created_at']


class TransactionLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    
    class Meta:
        model = TransactionLog
        fields = ['id', 'user', 'user_email', 'transaction_type', 'amount', 'description', 'order', 'performed_by', 'performed_by_email', 'created_at']


class MasterAvailabilitySerializer(serializers.ModelSerializer):
    master_email = serializers.CharField(source='master.email', read_only=True)
    
    class Meta:
        model = MasterAvailability
        fields = '__all__'


class CompanyBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBalance
        fields = ['amount']


class CompanyBalanceLogSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = CompanyBalanceLog
        fields = ['id', 'action_type', 'action_type_display', 'amount', 'reason', 
                 'performed_by', 'performed_by_email', 'old_value', 'new_value', 'created_at']
        read_only_fields = ('created_at',)


class MasterWorkloadSerializer(serializers.Serializer):
    """Serializer for master workload data combining availability and orders"""
    master_id = serializers.IntegerField()
    master_email = serializers.CharField()
    availability_slots = MasterAvailabilitySerializer(many=True)
    orders_count_by_date = serializers.DictField()
    next_available_slot = serializers.DictField(allow_null=True)
    total_orders_today = serializers.IntegerField()


class OrderCompletionSerializer(serializers.ModelSerializer):
    """Сериализатор для завершения заказов мастерами"""
    # Подробная информация о заказе
    order = serializers.SerializerMethodField()
    # Подробная информация о мастере  
    master = serializers.SerializerMethodField()
    curator_email = serializers.CharField(source='curator.email', read_only=True)
    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_profit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    completion_photos = serializers.SerializerMethodField()
    submitted_at = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderCompletion
        fields = [
            'id', 'order', 'master', 'work_description', 'completion_photos', 
            'parts_expenses', 'transport_costs', 'total_received', 'total_expenses', 
            'net_profit', 'completion_date', 'status', 'curator', 'curator_email', 
            'review_date', 'curator_notes', 'is_distributed', 'created_at', 
            'updated_at', 'submitted_at'
        ]
        read_only_fields = ('total_expenses', 'net_profit', 'is_distributed', 'created_at', 'updated_at')
    
    def get_submitted_at(self, obj):
        """Используем created_at как submitted_at"""
        return obj.created_at.isoformat() if obj.created_at else None
    
    def get_order(self, obj):
        """Возвращает подробную информацию о заказе"""
        if obj.order:
            return {
                'id': obj.order.id,
                'client_name': obj.order.client_name,
                'client_phone': obj.order.client_phone,                'address': obj.order.address,
                'description': obj.order.description,
                'final_cost': str(obj.order.final_cost),
                'created_at': obj.order.created_at.isoformat() if obj.order.created_at else None,
                'status': obj.order.status,
            }
        return None
    
    def get_master(self, obj):
        """Возвращает подробную информацию о мастере"""
        if obj.master:
            # Создаем полное имя из first_name и last_name
            full_name = f"{obj.master.first_name} {obj.master.last_name}".strip()
            if not full_name:
                full_name = obj.master.email  # Fallback to email if no name
            
            return {
                'id': obj.master.id,
                'full_name': full_name,
                'email': obj.master.email,
                'phone': getattr(obj.master, 'phone', None),
            }
        return None
    
    def get_completion_photos(self, obj):
        """Преобразуем относительные пути в полные URL"""
        if not obj.completion_photos:
            return []
        
        request = self.context.get('request')
        if request:
            # Строим полные URL для каждой фотографии
            photo_urls = []
            for photo_path in obj.completion_photos:
                if photo_path.startswith('completion_photos/'):
                    # Путь уже содержит папку
                    full_url = request.build_absolute_uri(f'/media/{photo_path}')
                else:
                    # Добавляем папку к пути
                    full_url = request.build_absolute_uri(f'/media/completion_photos/{photo_path}')
                photo_urls.append(full_url)
            return photo_urls
        
        # Fallback: если нет request в контексте, возвращаем относительные пути
        return obj.completion_photos


class OrderCompletionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания завершения заказа мастером"""
    
    completion_date = serializers.DateTimeField(required=False)  # Делаем поле необязательным
    
    class Meta:
        model = OrderCompletion
        fields = [
            'order', 'work_description', 'parts_expenses',
            'transport_costs', 'total_received', 'completion_date'
        ]
    
    def validate_order(self, value):
        """Проверяем, что заказ можно завершить"""
        if not hasattr(value, 'assigned_master') or not value.assigned_master:
            raise serializers.ValidationError("Заказ не назначен мастеру")
        
        if value.status not in ['выполняется', 'назначен', 'в работе']:
            raise serializers.ValidationError("Заказ должен быть в статусе 'выполняется', 'назначен' или 'в работе'")
        
        if hasattr(value, 'completion'):
            raise serializers.ValidationError("Заказ уже имеет запись о завершении")
        
        return value
    
    def create(self, validated_data):
        """Создаем завершение заказа и обновляем статус заказа"""
        import os
        from django.conf import settings
        from django.utils import timezone
        from datetime import datetime
        import uuid
        
        request = self.context.get('request')
        validated_data['master'] = request.user
        
        # Устанавливаем completion_date если не передана
        if 'completion_date' not in validated_data or not validated_data['completion_date']:
            validated_data['completion_date'] = timezone.now()
        
        # Получаем фотографии из request.FILES напрямую
        completion_photos = request.FILES.getlist('completion_photos') if request else []
        
        # Создаем завершение сначала без фотографий
        completion = super().create(validated_data)
        
        # Валидация и сохранение фотографий (если есть)
        if completion_photos:
            # Проверяем количество фотографий
            if len(completion_photos) > 5:
                raise serializers.ValidationError("Максимум 5 фотографий")
            
            try:
                # Создаем папку для фотографий завершения заказов, если её нет
                completion_photos_dir = os.path.join(settings.MEDIA_ROOT, 'completion_photos')
                os.makedirs(completion_photos_dir, exist_ok=True)
                
                photo_paths = []
                for i, photo in enumerate(completion_photos):
                    # Валидация файла
                    if photo.size > 5 * 1024 * 1024:
                        print(f"Файл {photo.name} слишком большой: {photo.size} байт")
                        continue
                    
                    if not photo.content_type.startswith('image/'):
                        print(f"Файл {photo.name} не является изображением: {photo.content_type}")
                        continue
                    
                    # Генерируем уникальное имя файла
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_id = str(uuid.uuid4())[:8]
                    file_extension = os.path.splitext(photo.name)[1].lower()
                    
                    # Ограничиваем допустимые расширения
                    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                    if file_extension not in allowed_extensions:
                        file_extension = '.jpg'
                    
                    filename = f"completion_{completion.id}_{timestamp}_{unique_id}_{i}{file_extension}"
                    file_path = os.path.join(completion_photos_dir, filename)
                    
                    # Сохраняем файл
                    try:
                        with open(file_path, 'wb') as f:
                            for chunk in photo.chunks():
                                f.write(chunk)
                        
                        # Сохраняем относительный путь (для URL)
                        relative_path = f"completion_photos/{filename}"
                        photo_paths.append(relative_path)
                        print(f"Сохранен файл: {relative_path}")
                    except Exception as e:
                        print(f"Ошибка сохранения файла {photo.name}: {e}")
                        continue
                
                # Обновляем completion с путями к фотографиям
                completion.completion_photos = photo_paths
                completion.save()
                print(f"Сохранено {len(photo_paths)} фотографий")
                
            except Exception as e:
                print(f"Ошибка обработки фотографий: {e}")
                # Продолжаем без фотографий, если произошла ошибка
        
        # Обновляем статус заказа
        completion.order.status = 'ожидает_подтверждения'
        completion.order.save()
        
        return completion


class OrderCompletionReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для проверки завершения заказа куратором"""
    action = serializers.CharField(write_only=True)
    comment = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    class Meta:
        model = OrderCompletion
        fields = ['status', 'curator_notes', 'action', 'comment']
        read_only_fields = ['status', 'curator_notes']
    
    def validate_action(self, value):
        """Проверяем корректность действия"""
        if value not in ['approve', 'reject']:
            raise serializers.ValidationError("Действие должно быть 'approve' или 'reject'")
        return value
    
    def update(self, instance, validated_data):
        """Обновляем статус и устанавливаем куратора"""
        request = self.context.get('request')
        
        # Устанавливаем статус в зависимости от action
        action = validated_data.pop('action')
        if action == 'approve':
            validated_data['status'] = 'одобрен'
        else:
            validated_data['status'] = 'отклонен'
            
        # Устанавливаем комментарий
        comment = validated_data.pop('comment', None)
        if comment:
            validated_data['curator_notes'] = comment
            
        validated_data['curator'] = request.user
        validated_data['review_date'] = timezone.now()
        
        completion = super().update(instance, validated_data)
        
        # Обновляем статус заказа
        if completion.status == 'одобрен':
            completion.order.status = 'завершен'
        else:
            # Если отклонен, возвращаем в "в процессе"
            completion.order.status = 'в процессе'
        
        completion.order.save()
        
        return completion


class FinancialTransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для финансовых транзакций"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    order_id = serializers.IntegerField(source='order_completion.order.id', read_only=True)
    
    class Meta:
        model = FinancialTransaction
        fields = [
            'id', 'user', 'user_email', 'order_completion', 'order_id',
            'transaction_type', 'transaction_type_display', 'amount',
            'description', 'created_at'
        ]
        read_only_fields = ('created_at',)


class OrderCompletionDistributionSerializer(serializers.Serializer):
    """Сериализатор для отображения расчета распределения средств"""
    master_immediate = serializers.DecimalField(max_digits=10, decimal_places=2)
    master_deferred = serializers.DecimalField(max_digits=10, decimal_places=2)
    master_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    company_share = serializers.DecimalField(max_digits=10, decimal_places=2)
    curator_share = serializers.DecimalField(max_digits=10, decimal_places=2)
    settings_used = serializers.CharField()
    settings_details = serializers.DictField()


class ProfitDistributionSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор для глобальных настроек распределения прибыли"""
    class Meta:
        model = ProfitDistributionSettings
        fields = [
            'id', 'master_paid_percent', 'master_balance_percent',
            'curator_percent', 'company_percent', 'created_at',
            'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class MasterProfitSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор для индивидуальных настроек прибыли мастера"""
    master_name = serializers.CharField(source='master.get_full_name', read_only=True)
    master_email = serializers.CharField(source='master.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    total_master_percent = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = MasterProfitSettings
        fields = [
            'id', 'master', 'master_name', 'master_email',
            'master_paid_percent', 'master_balance_percent', 
            'curator_percent', 'company_percent', 'total_master_percent',
            'is_active', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def validate(self, data):
        """Проверяем что сумма процентов равна 100%"""
        total = (
            data.get('master_paid_percent', 0) + 
            data.get('master_balance_percent', 0) + 
            data.get('curator_percent', 0) + 
            data.get('company_percent', 0)
        )
        if total != 100:
            raise serializers.ValidationError(
                f'Сумма всех процентов должна быть равна 100%. Текущая сумма: {total}%'
            )
        return data


# Сериализаторы для управления контентом сайта
class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            'id', 'phone', 'email', 'address', 'working_hours',
            'facebook_url', 'instagram_url', 'telegram_url', 'whatsapp_url',
            'hero_title', 'hero_subtitle', 'about_title', 'about_description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'price_from', 'is_active', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeedbackRequestSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = FeedbackRequest
        fields = [
            'id', 'name', 'phone', 'email', 'service', 'service_name', 'message',
            'status', 'is_called', 'assigned_to', 'assigned_to_name',
            'created_at', 'updated_at', 'called_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeedbackRequestCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заявки с сайта"""
    class Meta:
        model = FeedbackRequest
        fields = ['name', 'phone', 'email', 'service', 'message']
