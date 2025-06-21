# urls.py in your app

from django.urls import path
from .views import *
from .views.order_views import create_order, start_order, complete_order, transfer_order_to_warranty_master
from .balance_views import (
    get_user_balance_detailed,
    modify_balance,
    get_balance_logs_detailed,
    get_user_permissions,
    get_all_balances,
    get_company_balance,
    modify_company_balance,
    get_company_balance_logs,
    get_user_balance_detailed_for_super_admin
)
from .calendar_views import get_master_events
from .distancionka import (
    get_distance_settings,
    update_distance_settings,
    get_master_distance_info,
    get_all_masters_distance,
    get_master_available_orders_with_distance,
    force_update_all_masters_distance,
    set_master_distance_manually,
    reset_master_distance_to_automatic,
    get_master_distance_with_orders
)
from .master_workload_views import (
    master_availability_list,
    master_availability_detail,
    master_workload_detail,
    all_masters_workload,
    validate_order_scheduling
)
from .views.auth_views import get_masters, get_operators, get_curators
from .capacity_analysis import (
    get_capacity_analysis,
    get_weekly_capacity_forecast
)
from .schedule_views import master_schedule_view
from .workload_views import (
    get_master_workload,
    get_all_masters_workload,
    get_master_availability,
    get_best_available_master,
    assign_order_with_workload_check
)
from .slot_views import (
    get_master_daily_schedule,
    assign_order_to_slot,
    get_available_slots_for_master,
    release_order_slot,
    get_order_slot_info,
    get_all_masters_slots_summary
)
from .views.site_management import (
    get_public_settings,
    get_public_services,
    create_feedback_request,
    SiteSettingsViewSet,
    ServiceViewSet,
    FeedbackRequestViewSet
)

urlpatterns = [
    path('create-test-order/', create_test_order, name='create_test_order'),
    path('get-new-orders/', get_new_orders, name='get_new_orders'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('api/user/', get_user_by_token, name='get_user_by_token'),
    path('orders/create/', create_order, name='create_order'),
    path('get_processing_orders', get_processing_orders, name='get_processing_orders'),    path('assign/<int:order_id>/', assign_master, name='assign'),
    path('assign/<int:order_id>/remove/', remove_master, name='remove_master'),
    path('orders/assigned/', get_assigned_orders, name='get_assigned_orders'),
    path('users/<int:user_id>/', get_user_by_id, name='get_user_by_id'),
    path('orders/<int:order_id>/delete/', delete_order, name='delete_order'),
    path('orders/<int:order_id>/update/', update_order, name='update_order'),
    path('users/masters/', get_masters, name='get_masters'),
    path('users/operators/', get_operators, name='get_operators'),
    path('users/curators/', get_curators, name='get_curators'),    path('balance/<int:user_id>/', get_user_balance, name='get_user_balance'),  # legacy
    path('balance/<int:user_id>/top-up/', top_up_balance, name='top_up_balance'),  # legacy
    path('balance/<int:user_id>/deduct/', deduct_balance, name='deduct_balance'),  # legacy
    path('balance/<int:user_id>/logs/', get_balance_logs, name='get_balance_logs'),  # legacy
    
    # Новая система управления балансами
    path('api/balance/<int:user_id>/detailed/', get_user_balance_detailed, name='get_user_balance_detailed'),
    path('api/balance/<int:user_id>/modify/', modify_balance, name='modify_balance'),
    path('api/balance/<int:user_id>/logs/detailed/', get_balance_logs_detailed, name='get_balance_logs_detailed'),
    path('api/balance/<int:user_id>/permissions/', get_user_permissions, name='get_user_permissions'),
    path('api/balance/all/', get_all_balances, name='get_all_balances'),
    path('api/user/', get_user_by_token, name='get_user_by_token'),
    path('api/users/create/', create_user, name='create_user'),
    path('api/orders/new/', get_orders_new, name='get_orders_new'),
    path('api/orders/all/', get_all_orders, name='all_orders'),    path('api/orders/last-4hours/', get_orders_last_4hours, name='orders_last_4hours'),
    path('api/orders/last-day/', get_orders_last_day, name='orders_last_day'),    path('api/orders/active/', get_active_orders, name='active_orders'),
    path('api/orders/non-active/', get_non_active_orders, name='non_active_orders'),    path('api/orders/master-available/', get_master_available_orders, name='master_available_orders'),    path('api/orders/transferred/', get_transferred_orders, name='transferred_orders'),
    path('api/orders/<int:order_id>/remove-master/', remove_master, name='remove_master'),
    
    # Workload management endpoints
    path('api/workload/master/<int:master_id>/', get_master_workload, name='get_master_workload'),
    path('api/workload/masters/', get_all_masters_workload, name='get_all_masters_workload'),
    path('api/availability/master/<int:master_id>/', get_master_availability, name='get_master_availability'),
    path('api/availability/best-master/', get_best_available_master, name='get_best_available_master'),    path('api/orders/<int:order_id>/assign-with-check/', assign_order_with_workload_check, name='assign_order_with_workload_check'),
    path('api/orders/<int:order_id>/transfer/', transfer_order_to_warranty_master, name='transfer_order_to_warranty_master'),
    # path('orders/transferred/', get_transferred_orders),
    # path('orders/<int:order_id>/complete_transferred/', complete_transferred_order),
    # path('orders/<int:order_id>/approve/', approve_completed_order),
    path('orders/master/<int:master_id>/', get_orders_by_master, name='get_orders_by_master'),
    path('balance/<int:user_id>/history/', get_balance_with_history),
    path('profit-distribution/', profit_distribution),
    path('curator/fine-master/', fine_master),
    path('mine',           get_my_events,      name='calendar-mine-no-slash'),  # support frontend GET /mine    path('mine/',           get_my_events,      name='calendar-mine'),
    path('api/mine',        get_my_events,      name='calendar-mine-api'),  # support frontend without slash
    path('master/<int:master_id>/events/', get_master_events, name='calendar-master-events'),
    path('create/',         create_event,       name='calendar-create'),
    path('update/<int:event_id>/', update_event_time, name='calendar-update'),
    path('delete/<int:event_id>/', delete_event,      name='calendar-delete'),
    path('contacts/', get_all_contacts, name='get_all_contacts'),
    path('contacts/create/', create_contact, name='create_contact'),
    path('contacts/<int:contact_id>/delete/', delete_contact, name='delete_contact'),
    path('contacts/<int:contact_id>/mark_as_called/', mark_as_called, name='mark_as_called'),
    path('contacts/called/', get_called_contacts, name='get_called_contacts'),
    path('contacts/uncalled/', get_uncalled_contacts, name='get_uncalled_contacts'),
    path('orders/guaranteed/<int:master_id>/', get_guaranteed_orders, name='get_guaranteed_orders'),
    path('orders/guaranteed/', get_all_guaranteed_orders, name='get_all_guaranteed_orders'),
    path('users/warranty-masters/', get_all_warranty_masters, name='get_all_warranty_masters'),    path('api/distribute/<int:order_id>/', distribute_order_profit, name='distribute_order_profit'),
    
    # Новые эндпоинты для логирования
    path('api/logs/orders/<int:order_id>/', get_order_logs, name='get_order_logs'),
    path('api/logs/orders/', get_all_order_logs, name='get_all_order_logs'),
    path('api/logs/transactions/', get_transaction_logs, name='get_all_transaction_logs'),
    path('api/logs/transactions/<int:user_id>/', get_transaction_logs, name='get_user_transaction_logs'),
    path('api/orders/<int:order_id>/detail/', get_order_detail, name='get_order_detail'),
    
    # Улучшенные эндпоинты для гарантийных мастеров
    path('api/users/warranty-masters/', get_warranty_masters, name='get_warranty_masters'),
    path('api/orders/<int:order_id>/warranty/complete/', complete_warranty_order, name='complete_warranty_order'),
    path('api/orders/<int:order_id>/warranty/approve/', approve_warranty_order, name='approve_warranty_order'),
    path('api/warranty-masters/<int:master_id>/stats/', get_warranty_master_stats, name='get_warranty_master_stats'),
    path('api/warranty-masters/my-stats/', get_warranty_master_stats, name='get_my_warranty_stats'),
    
    # Валидация ролей
    path('api/validate-role/', validate_user_role, name='validate_user_role'),
    path('api/master-panel/', master_panel_access, name='master_panel_access'),    path('api/curator-panel/', curator_panel_access, name='curator_panel_access'),
    path('api/operator-panel/', operator_panel_access, name='operator_panel_access'),
    path('api/warrant-master-panel/', warrant_master_panel_access, name='warrant_master_panel_access'),
    path('api/super-admin-panel/', super_admin_panel, name='super_admin_panel_access'),
    path('api/orders/master/available/', get_master_available_orders, name='get_master_available_orders'),
      # Distance endpoints
    path('api/distance/settings/', get_distance_settings, name='get_distance_settings'),
    path('api/distance/settings/update/', update_distance_settings, name='update_distance_settings'),
    path('api/distance/master/<int:master_id>/', get_master_distance_info, name='get_master_distance_info'),
    path('api/distance/masters/all/', get_all_masters_distance, name='get_all_masters_distance'),    path('api/distance/orders/available/', get_master_available_orders_with_distance, name='get_master_available_orders_with_distance'),    path('api/distance/force-update/', force_update_all_masters_distance, name='force_update_all_masters_distance'),    path('api/distance/master/<int:master_id>/set/', set_master_distance_manually, name='set_master_distance_manually'),
    path('api/distance/master/<int:master_id>/reset/', reset_master_distance_to_automatic, name='reset_master_distance_to_automatic'),
    path('api/distance/master/orders/', get_master_distance_with_orders, name='get_master_distance_with_orders'),
    
    # Company balance endpoints (only for super-admin)
    path('api/company-balance/', get_company_balance, name='get_company_balance'),
    path('api/company-balance/modify/', modify_company_balance, name='modify_company_balance'),
    path('api/company-balance/logs/', get_company_balance_logs, name='get_company_balance_logs'),
    
    # Universal balance endpoint for dashboard (returns company balance for super-admin, personal balance for others)
    path('api/balance/<int:user_id>/dashboard/', get_user_balance_detailed_for_super_admin, name='get_user_balance_detailed_for_super_admin'),

    # Master Workload and Availability endpoints
    path('api/masters/<int:master_id>/availability/', master_availability_list, name='master_availability_list'),
    path('api/masters/<int:master_id>/availability/<int:availability_id>/', master_availability_detail, name='master_availability_detail'),
    path('api/masters/<int:master_id>/workload/', master_workload_detail, name='master_workload_detail'),    path('api/masters/workload/all/', all_masters_workload, name='all_masters_workload'),
    path('api/orders/validate-scheduling/', validate_order_scheduling, name='validate_order_scheduling'),
      # Capacity Analysis endpoints
    path('api/capacity/analysis/', get_capacity_analysis, name='get_capacity_analysis'),
    path('api/capacity/weekly-forecast/', get_weekly_capacity_forecast, name='get_weekly_capacity_forecast'),
    
    # Master Schedule endpoints
    path('api/master/schedule/', master_schedule_view, name='master_schedule'),
    path('api/master/schedule/<int:master_id>/', master_schedule_view, name='master_schedule_detail'),    # Order Completion endpoints
    path('api/orders/<int:order_id>/start/', start_order, name='start_order'),
    path('api/orders/<int:order_id>/complete/', complete_order, name='complete_order'),
    path('api/completions/master/', get_master_completions, name='get_master_completions'),
    path('api/completions/pending/', get_pending_completions, name='get_pending_completions'),
    path('api/completions/<int:completion_id>/', get_completion_detail, name='get_completion_detail'),
    path('api/completions/<int:completion_id>/review/', review_completion, name='review_completion'),
    path('api/completions/<int:completion_id>/distribution/', get_completion_distribution, name='get_completion_distribution'),
    path('api/transactions/', get_financial_transactions, name='get_financial_transactions'),
    path('api/transactions/all/', get_all_financial_transactions, name='get_all_financial_transactions'),    # Маршруты для индивидуальных настроек распределения прибыли мастеров
    path('api/profit-settings/masters/', get_all_masters_with_settings, name='get_all_masters_with_settings'),
    path('api/profit-settings/master/<int:master_id>/', get_master_profit_settings, name='get_master_profit_settings'),
    path('api/profit-settings/master/<int:master_id>/set/', set_master_profit_settings, name='set_master_profit_settings'),    path('api/profit-settings/master/<int:master_id>/delete/', delete_master_profit_settings, name='delete_master_profit_settings'),
    path('api/orders/<int:order_id>/profit-preview/', get_order_profit_preview, name='get_order_profit_preview'),
    
    # Order Slots Management endpoints
    path('api/slots/master/<int:master_id>/schedule/', get_master_daily_schedule, name='get_master_daily_schedule'),
    path('api/slots/master/<int:master_id>/schedule/<str:schedule_date>/', get_master_daily_schedule, name='get_master_daily_schedule_date'),
    path('api/slots/assign/', assign_order_to_slot, name='assign_order_to_slot'),
    path('api/slots/master/<int:master_id>/available/', get_available_slots_for_master, name='get_available_slots_for_master'),
    path('api/slots/master/<int:master_id>/available/<str:schedule_date>/', get_available_slots_for_master, name='get_available_slots_for_master_date'),
    path('api/slots/release/', release_order_slot, name='release_order_slot'),
    path('api/slots/order/<int:order_id>/', get_order_slot_info, name='get_order_slot_info'),    path('api/slots/masters/summary/', get_all_masters_slots_summary, name='get_all_masters_slots_summary'),
    path('api/slots/masters/summary/<str:schedule_date>/', get_all_masters_slots_summary, name='get_all_masters_slots_summary_date'),    
    # Публичные API для лендинга
    path('public/settings/', get_public_settings, name='get_public_settings'),
    path('public/services/', get_public_services, name='get_public_services'),
    path('public/feedback/', create_feedback_request, name='create_public_feedback'),
      # Управление заявками обратной связи (для админ-панели)
    path('feedback-requests/', FeedbackRequestViewSet.as_view({'get': 'list', 'post': 'create'}), name='feedback_requests'),
    path('feedback-requests/<int:pk>/', FeedbackRequestViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='feedback_request_detail'),
    path('feedback-requests/not-called/', FeedbackRequestViewSet.as_view({'get': 'not_called'}), name='feedback_requests_not_called'),
    path('feedback-requests/called/', FeedbackRequestViewSet.as_view({'get': 'called'}), name='feedback_requests_called'),
    path('feedback-requests/<int:pk>/mark_called/', FeedbackRequestViewSet.as_view({'post': 'mark_called'}), name='feedback_request_mark_called'),
    path('feedback-requests/<int:pk>/assign/', FeedbackRequestViewSet.as_view({'post': 'assign_to_master'}), name='feedback_request_assign'),
    path('feedback-requests/debug-test/', FeedbackRequestViewSet.as_view({'get': 'debug_test'}), name='feedback_request_debug_test'),
]
