"""
Утилиты и константы для API
"""
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta, datetime
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

from ..models import Order, CustomUser, Balance, BalanceLog, ProfitDistribution, CalendarEvent, Contact, CompanyBalance, OrderLog, TransactionLog, MasterAvailability, OrderCompletion, FinancialTransaction, CompanyBalanceLog, ProfitDistributionSettings
from ..serializers import (
    OrderSerializer,
    CustomUserSerializer,
    BalanceSerializer,
    BalanceLogSerializer, CalendarEventSerializer, ContactSerializer,
    OrderLogSerializer, TransactionLogSerializer, OrderDetailSerializer,
    OrderPublicSerializer, OrderCompletionSerializer, OrderCompletionCreateSerializer,
    OrderCompletionReviewSerializer, FinancialTransactionSerializer, OrderCompletionDistributionSerializer
)
from ..middleware import role_required, RolePermission

# Константы ролей
ROLES = {
    'MASTER': 'master',
    'OPERATOR': 'operator', 
    'WARRANT_MASTER': 'warrant-master',
    'SUPER_ADMIN': 'super-admin',
    'CURATOR': 'curator'
}


# ----------------------------------------
#  Вспомогательные функции логирования
# ----------------------------------------

def log_order_action(order, action, performed_by, description, old_value=None, new_value=None):
    """
    Логирует действие с заказом
    """
    OrderLog.objects.create(
        order=order,
        action=action,
        performed_by=performed_by,
        description=description,
        old_value=old_value,
        new_value=new_value
    )

def log_system_action(action, performed_by, description, old_value=None, new_value=None, metadata=None):
    """
    Логирует системное действие (не связанное с конкретным заказом)
    """
    from ..models import SystemLog
    SystemLog.objects.create(
        action=action,
        performed_by=performed_by,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata or {}
    )

def log_transaction(user, transaction_type, amount, description, order=None, performed_by=None):
    """
    Логирует финансовую транзакцию
    """
    TransactionLog.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        order=order,
        performed_by=performed_by
    )
