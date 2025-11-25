import time
from datetime import date, datetime
import logging
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView


from config.settings import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from content.serializers import LoginSerializer
from users.client import oAuth2Client
from users.models import User, APISettings
from users.serializers import GetUserSerializer

logger = logging.getLogger(__name__)

def get_and_save_all_pages():
    # Base URL and token for the API
    base_url = 'https://talaba.tsue.uz/rest/v1/data/employee-list?type=all'
    token = 'GcQKn9GP6mJcPCHwsArNFWEIObe2CfZF'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    page = 1
    saved_count = 0
    start_time = time.time()

    while True:
        response = requests.get(f"{base_url}?page={page}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data['data']['items']:
                if not User.objects.filter(employee_id_number=item['employee_id_number']).exists():
                    birth_date_value = item.get('birth_date')
                    if isinstance(birth_date_value, str):
                        try:
                            # Try to parse the string as an ISO date
                            birth_date = date.fromisoformat(birth_date_value)
                        except ValueError:
                            # If the string is not a valid date, set birth_date to None
                            birth_date = None
                    else:
                        # If birth_date_value is not a string, set birth_date to None
                        birth_date = None
                    User.objects.create(
                        employee_id_number=item['employee_id_number'],
                        first_name=item['first_name'],
                        second_name=item['second_name'],
                        gender=item['gender']['name'],
                        employeeType=item['employeeType']['name'],
                        birth_date=birth_date,
                        role='teacher'
                    )
                    saved_count += 1

            # Check for the next page
            if page >= data['data']['pagination']['pageCount']:
                break
            page += 1
            time.sleep(1)
        else:
            return {'error': 'Error fetching data', 'status_code': response.status_code}

    total_duration = time.time() - start_time

    return {'status': 'data saved', 'saved_items': saved_count, 'total_time': f'{total_duration:.2f} seconds'}


class DataImportView(View):
    def get(self, request):
        import_users_from_tsue.delay()
        return JsonResponse({"status": "Import started"})


# Ensure to import your OAuth2Client correctly

###########################################################################
from uuid import uuid4


class oAuthAuthorizationView(APIView):
    def get(self, request, *args, **kwargs):
        # 1. Генерируем state
        state = uuid4().hex
        request.session['oauth_state'] = state

        # 2. Инициализируем клиент (БЕЗ state)
        client = oAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            authorize_url='https://hemis.tsue.uz/oauth/authorize',
            token_url='https://hemis.tsue.uz/oauth/access-token',
            resource_owner_url='https://hemis.tsue.uz/oauth/api/user'
        )

        # 3. Получаем базовую ссылку
        base_url = client.get_authorization_url()

        # 4. Вручную добавляем state в конец ссылки
        # Обычно get_authorization_url возвращает что-то вроде "...?client_id=...&response_type=code"
        # Поэтому мы безопасно добавляем &state=...
        authorization_url = f"{base_url}&state={state}"

        return Response({
            'authorization_url': authorization_url
        })


class OAuthCallbackView(APIView):
    def get(self, request, *args, **kwargs):
        # 1. Получаем code и state из query parameters
        auth_code = request.query_params.get('code')
        received_state = request.query_params.get('state')

        # 2. Проверяем наличие code
        if not auth_code:
            return Response({'error': 'Authorization code is missing'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверка state для защиты от CSRF
        expected_state = request.session.pop('oauth_state', None)

        if not received_state or received_state != expected_state:
            logger.error("State mismatch or missing. CSRF potential.")
            return Response({'error': 'Invalid state parameter or missing session state'},
                            status=status.HTTP_400_BAD_REQUEST)

        # OAuth client initialization (Убрали ?fields=)
        client = oAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            authorize_url='https://hemis.tsue.uz/oauth/authorize',
            token_url='https://hemis.tsue.uz/oauth/access-token',
            resource_owner_url='https://hemis.tsue.uz/oauth/api/user'  # Улучшено
        )

        try:
            # Обмен code на токен
            access_token_response = client.get_access_token(auth_code)
            access_token = access_token_response.get('access_token')

            if not access_token:
                logger.error("Failed to obtain access token: %s", access_token_response)
                return Response({'error': 'Failed to obtain access token', 'details': access_token_response},
                                status=status.HTTP_400_BAD_REQUEST)

            # Получение данных пользователя
            user_details = client.get_user_details(access_token)
            logger.debug("User details: %s", user_details)

        except Exception as e:
            logger.error("Error during token or user fetch: %s", e)
            return Response({'error': f"OAuth process failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Улучшенная обработка данных и уникального ID
        hemis_unique_id = str(user_details.get('id'))
        if not hemis_unique_id:
            return Response({'error': 'Unique user ID (id/uuid) missing from HEMIS data'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        departments = user_details.get('departments', [])
        department_name = departments[0].get('department', {}).get('name') if departments else None

        user_type = user_details.get('type')  # e.g., 'teacher'

        # Transform data
        transformed_data = {
            'hemis_id': hemis_unique_id,  # Уникальный ID для поиска
            'first_name': user_details.get('firstname'),
            'second_name': user_details.get('surname'),
            'birth_date': self.convert_birth_date(user_details.get('birth_date')),
            'phone_number': user_details.get('phone', '').replace('+', ''),  # Safe access
            'role': user_type.lower() if user_type else 'default',  # Используем role из HEMIS
            'employee_id_number': user_details.get('employee_id_number'),
            'department': department_name,
        }

        logger.debug("Transformed data: %s", transformed_data)

        # 5. Handle user creation or update
        try:
            # Ищем по hemis_id
            user, created = User.objects.update_or_create(
                hemis_id=transformed_data['hemis_id'],
                defaults=transformed_data
            )

            if created:
                logger.info("Created new user: %s", user)
                # Установка пароля для соответствия модели (если требуется)
                # user.set_unusable_password()
                # user.save()

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            return Response({
                'jwt_token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Error processing user or generating token: %s", e)
            # Возвращаем 500, так как ошибка на стороне сервера/БД
            return Response({'error': f"User processing failed: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def convert_birth_date(self, birth_date_str):
        # ... (метод остается прежним)
        try:
            return datetime.strptime(birth_date_str, '%d-%m-%Y').date()  # Добавил .date()
        except Exception as e:
            logger.error(f"Invalid birth date: {birth_date_str}. Error: {e}")
            return None

class UserDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = GetUserSerializer
    #@swagger_auto_schema(request_body=GetUserSerializer)


    def get(self, request, *args, **kwargs):
        user = request.user

        # Сериализуем данные пользователя
        serializer = self.serializer_class(user)

        return Response(
            {
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


