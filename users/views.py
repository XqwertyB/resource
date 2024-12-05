import time
from datetime import date, datetime
import logging
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
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
        result = get_and_save_all_pages()
        if 'error' in result:
            return JsonResponse(result, status=result.get('status_code', 500))
        return JsonResponse(result)


# Ensure to import your OAuth2Client correctly

###########################################################################
class oAuthAuthorizationView(APIView):
    def get(self, request, *args, **kwargs):
        print(REDIRECT_URI)
        client = oAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            authorize_url='https://hemis.tsue.uz/oauth/authorize',
            token_url='https://hemis.tsue.uz/oauth/access-token',
            resource_owner_url='https://hemis.tsue.uz/oauth/api/user?fields='
        )
        authorization_url = client.get_authorization_url()

        return Response(
            {
                'authorization_url': authorization_url
            },
            status=status.HTTP_200_OK)


    def post(self, request, *args, **kwargs):
        # Метод для получения токенов (access и refresh)
        return Response(self.token(), status=status.HTTP_200_OK)

    def token(self):
        # Пример генерации токена через RefreshToken
        refresh = RefreshToken.for_user(self.request.user)

        return {
            "access": str(refresh.access_token),
            "refresh_token": str(refresh)
        }


# class OAuthCallbackView(APIView):
#     def get(self, request, *args, **kwargs):
#         full_info = {}
#         auth_code = self.kwargs.get('code')
#         if not auth_code:
#             return Response(
#                 {
#                     'status': False,
#                     'error': 'Authorization code is missing'
#                 },
#                 status=status.HTTP_400_BAD_REQUEST)
#
#         client = oAuth2Client(
#             client_id=CLIENT_ID,
#             client_secret=CLIENT_SECRET,
#             redirect_uri=REDIRECT_URI,
#             authorize_url='https://hemis.tsue.uz/oauth/authorize',
#             token_url='https://hemis.tsue.uz/oauth/access-token',
#             resource_owner_url='https://hemis.tsue.uz/oauth/api/user?fields='
#         )
#         access_token_response = client.get_access_token(auth_code)
#
#         if 'access_token' in access_token_response:
#             access_token = access_token_response['access_token']
#             user_details = client.get_user_details(access_token)
#             full_info['details'] = user_details
#             full_info['token'] = access_token
#             return Response(full_info, status=status.HTTP_200_OK)
#         else:
#             return Response(
#                 {
#                     'status': False,
#                     'error': 'Failed to obtain access token'
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )


class OAuthCallbackView(APIView):
    def get(self, request, *args, **kwargs):
        auth_code = self.kwargs.get('code')
        if not auth_code:
            return Response({'error': 'Authorization code is missing'}, status=status.HTTP_400_BAD_REQUEST)

        # OAuth client initialization
        client = oAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            authorize_url='https://hemis.tsue.uz/oauth/authorize',
            token_url='https://hemis.tsue.uz/oauth/access-token',
            resource_owner_url='https://hemis.tsue.uz/oauth/api/user?fields='
        )

        try:
            access_token_response = client.get_access_token(auth_code)
        except Exception as e:
            logger.error("Error obtaining access token: %s", e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        access_token = access_token_response.get('access_token')
        if not access_token:
            return Response({'error': 'Failed to obtain access token'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_details = client.get_user_details(access_token)
            logger.debug("User details: %s", user_details)
        except Exception as e:
            logger.error("Error fetching user details: %s", e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Department handling
        departments = user_details.get('departments', [])
        department_name = departments[0].get('department', {}).get('name') if departments else None

        # Transform data
        transformed_data = {
            'first_name': user_details.get('firstname'),
            'second_name': user_details.get('surname'),
            'birth_date': self.convert_birth_date(user_details.get('birth_date')),
            'phone_number': user_details.get('phone').replace('+', ''),
            'role': 'teacher',
            'employee_id_number': user_details.get('employee_id_number'),
            'department': department_name,
        }

        logger.debug("Transformed data: %s", transformed_data)

        # Handle user creation or update
        phone_number = transformed_data['phone_number']
        user = User.objects.filter(phone_number=phone_number).first()

        try:
            if user:
                logger.info("Updating user: %s", user)
                for key, value in transformed_data.items():
                    setattr(user, key, value)
                user.save()
            else:
                logger.info("Creating new user with data: %s", transformed_data)
                user = User.objects.create(**transformed_data)


            refresh = RefreshToken.for_user(user)
            return Response({
                'jwt_token': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Error processing user: %s", e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def convert_birth_date(self, birth_date_str):
        try:
            return datetime.strptime(birth_date_str, '%d-%m-%Y')
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


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


