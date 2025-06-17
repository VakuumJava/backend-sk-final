"""
API представления для аутентификации и пользователей
"""
from .utils import *


# ----------------------------------------
#  Публичные (регистрация/логин/тестовые)
# ----------------------------------------

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(email=email, password=password)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            }
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    serializer = CustomUserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ----------------------------------------
#  Защищённые пользовательские API
# ----------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_token(request):
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_by_id(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CustomUserSerializer(user)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_masters(request):
    masters = CustomUser.objects.filter(role='master')
    serializer = CustomUserSerializer(masters, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_curators(request):
    curators = CustomUser.objects.filter(role='curator')
    serializer = CustomUserSerializer(curators, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_operators(request):
    operators = CustomUser.objects.filter(role='operator')
    serializer = CustomUserSerializer(operators, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@role_required([ROLES['SUPER_ADMIN']])
def super_admin_panel(request):
    """
    Панель супер-администратора. Доступна только пользователям с ролью super-admin.
    """
    if request.user.role != ROLES['SUPER_ADMIN']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для супер-администраторов.',
            'user_role': request.user.role,
            'required_role': ROLES['SUPER_ADMIN']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель супер-администратора',
        'user_role': request.user.role
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validate_user_role(request):
    """Возвращает информацию о роли пользователя"""
    return Response({
        'user_id': request.user.id,
        'email': request.user.email,
        'role': request.user.role,
        'is_valid': True
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def master_panel_access(request):
    """Доступ к панели мастера - только для мастеров"""
    if request.user.role != ROLES['MASTER']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для мастеров.',
            'user_role': request.user.role,
            'required_role': ROLES['MASTER']
        }, status=403)
    
    return Response({
        'message': 'Добро пожаловать в панель мастера',
        'user_role': request.user.role
    })


@api_view(['GET']) 
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def curator_panel_access(request):
    """Доступ к панели куратора - только для кураторов"""
    if request.user.role != ROLES['CURATOR']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для кураторов.',
            'user_role': request.user.role,
            'required_role': ROLES['CURATOR']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель куратора',
        'user_role': request.user.role
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated]) 
def operator_panel_access(request):
    """Доступ к панели оператора - только для операторов"""
    if request.user.role != ROLES['OPERATOR']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для операторов.',
            'user_role': request.user.role,
            'required_role': ROLES['OPERATOR']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель оператора',
        'user_role': request.user.role
    })


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def warrant_master_panel_access(request):
    """Доступ к панели гарантийного мастера - только для гарантийных мастеров"""
    if request.user.role != ROLES['WARRANT_MASTER']:
        return Response({
            'error': 'Доступ запрещен. Панель доступна только для гарантийных мастеров.',
            'user_role': request.user.role,
            'required_role': ROLES['WARRANT_MASTER']
        }, status=403)
        
    return Response({
        'message': 'Добро пожаловать в панель гарантийного мастера',
        'user_role': request.user.role
    })
