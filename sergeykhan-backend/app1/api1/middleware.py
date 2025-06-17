from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from .models import CustomUser

class RoleValidationMiddleware:
    """
    Middleware для проверки ролей пользователей на определенных эндпоинтах
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Роутинги для каждой роли
        ROLE_ENDPOINTS = {
            'master': ['/api/master/', '/master/'],
            'curator': ['/api/curator/', '/curator/'],
            'operator': ['/api/operator/', '/operator/'],
            'warrant-master': ['/api/warrant-master/', '/warrant-master/', '/garant-master/'],
            'super-admin': ['/api/super-admin/', '/super-admin/', '/admin/'],
        }

        # Проверяем только для определенных путей
        path = request.path_info
        
        # Исключаем общие API эндпоинты
        excluded_paths = ['/api/login/', '/api/logout/', '/api/register/', '/api/user/', '/admin/', '/static/', '/media/']
        
        if any(path.startswith(excluded) for excluded in excluded_paths):
            return self.get_response(request)

        # Проверяем роль только для API запросов к панелям
        for role, endpoints in ROLE_ENDPOINTS.items():
            if any(path.startswith(endpoint) for endpoint in endpoints):
                # Получаем токен из заголовка
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Token '):
                    token = auth_header[6:]
                    try:
                        token_obj = Token.objects.get(key=token)
                        user = token_obj.user
                        
                        # Проверяем роль пользователя
                        if user.role != role:
                            return JsonResponse({
                                'error': f'Доступ запрещен. Требуется роль: {role}',
                                'user_role': user.role,
                                'required_role': role
                            }, status=403)
                            
                    except Token.DoesNotExist:
                        return JsonResponse({'error': 'Недействительный токен'}, status=401)
                break

        return self.get_response(request)


def role_required(allowed_roles):
    """
    Декоратор для проверки ролей пользователей
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Требуется аутентификация'}, status=401)
            
            if request.user.role not in allowed_roles:
                return JsonResponse({
                    'error': f'Недостаточно прав. Требуется одна из ролей: {", ".join(allowed_roles)}',
                    'user_role': request.user.role
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RolePermission:
    """
    Класс для проверки разрешений на основе ролей
    """
    ROLES = {
        'MASTER': 'master',
        'OPERATOR': 'operator',
        'WARRANT_MASTER': 'warrant-master',
        'SUPER_ADMIN': 'super-admin',
        'CURATOR': 'curator'
    }

    @staticmethod
    def check_role(user, required_role):
        """Проверяет роль пользователя"""
        if not user.is_authenticated:
            return False
        return user.role == required_role

    @staticmethod
    def check_roles(user, required_roles):
        """Проверяет роль пользователя из списка ролей"""
        if not user.is_authenticated:
            return False
        return user.role in required_roles
