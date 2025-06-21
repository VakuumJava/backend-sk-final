from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, MasterProfitSettings, ProfitDistributionSettings,
)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'role', 'dist', 'is_staff', 'is_active')  # Добавлено dist
    list_filter = ('role', 'dist', 'is_staff', 'is_active')  # Добавлен фильтр по dist

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('role', 'dist')}),  # Добавлено dist
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'dist', 'is_staff', 'is_active')}
        ),  # Добавлено dist в форму создания
    )

    search_fields = ('email',)  # Search by email instead of username
    ordering = ('email',)  # Order by email instead of username

@admin.register(MasterProfitSettings)
class MasterProfitSettingsAdmin(admin.ModelAdmin):
    list_display = ('master', 'master_paid_percent', 'master_balance_percent', 'curator_percent', 'company_percent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('master__email', 'master__first_name', 'master__last_name')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Мастер', {
            'fields': ('master', 'is_active')
        }),
        ('Проценты распределения', {
            'fields': ('master_paid_percent', 'master_balance_percent', 'curator_percent', 'company_percent')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """При сохранении через админку записываем, кто создал/обновил настройки"""
        if not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProfitDistributionSettings)
class ProfitDistributionSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'master_paid_percent', 'master_balance_percent', 'curator_percent', 'company_percent', 'is_active')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    fieldsets = (
        ('Проценты распределения', {
            'fields': ('master_paid_percent', 'master_balance_percent', 'curator_percent', 'company_percent', 'is_active')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """При сохранении через админку записываем, кто создал/обновил настройки"""
        if not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

# Register the CustomUser model with the custom admin
admin.site.register(CustomUser, CustomUserAdmin)
