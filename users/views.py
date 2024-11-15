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
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from config.settings import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTHORIZE_URL, TOKEN_URL, RESOURCE_OWNER_URL, \
    REDIRECT_URIS, AUTHORIZE_URLS, TOKEN_URLS, RESOURCE_OWNER_URLS
from content.serializers import LoginSerializer
from users.client import oAuth2Client
from users.models import User, APISettings
from config import settings


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




class oAuthCallbackView(APIView):
    def get(self, request, *args, **kwargs):
        auth_code = request.GET.get('code')
        if not auth_code:
            return Response({'error': 'Authorization code is missing'}, status=status.HTTP_400_BAD_REQUEST)

        # Initialize OAuth client with parameters from settings
        client = oAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            authorize_url='https://hemis.tsue.uz/oauth/authorize',
            token_url='https://hemis.tsue.uz/oauth/access-token',
            resource_owner_url='https://hemis.tsue.uz/oauth/api/user?fields='
        )

        # Attempt to get access_token
        try:
            access_token_response = client.get_access_token(auth_code)
        except Exception as e:
            logger.error("Error obtaining access token: %s", e)
            return Response({'error': 'An error occurred while obtaining the access token'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'access_token' not in access_token_response:
            return Response(
                {'status': False, 'error': 'Failed to obtain access token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token = access_token_response['access_token']

        # Attempt to get user details
        try:
            user_details = client.get_user_details(access_token)
            logger.info("User details: %s", user_details)
        except Exception as e:
            logger.error("Error fetching user details: %s", e)
            return Response({'error': 'Failed to fetch user details'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        departments = user_details.get('departments', [])
        if departments:
           # print(departments)  # Debugging to ensure the structure
            department_data = departments[0].get('department', {})
            department_name = department_data.get('name', None)
        else:
            department_name = None
            print("Departments field is empty or missing.")

        transformed_data = {
            'first_name': user_details.get('firstname'),
            'second_name': user_details.get('surname'),
            'birth_date': self.convert_birth_date(user_details.get('birth_date')),
            'phone_number': user_details.get('phone').replace('+', ''),
            'role': 'teacher',  # Default role
            'employee_id_number': user_details.get('employee_id_number'),
            'department': department_name
        }

        # Check if a user with the given phone_number already exists
        phone_number = transformed_data['phone_number']
        user = User.objects.filter(phone_number=phone_number).first()

        if user:
            # User exists, update the user
            user.first_name = transformed_data.get('first_name', user.first_name)
            user.second_name = transformed_data.get('second_name', user.second_name)
            user.birth_date = transformed_data.get('birth_date', user.birth_date)
            user.phone_number = transformed_data.get('phone_number', user.phone_number)
            user.employee_id_number = transformed_data.get('employee_id_number', user.employee_id_number)
            user.department = transformed_data.get('department', user.department)
            user.role = transformed_data.get('role', user.role)
            user.save()
            logger.info("User updated: %s", user)
        else:
            # User does not exist, create a new one
            try:
                user = User.objects.create(**transformed_data)
                logger.info("User created: %s", user)
            except IntegrityError as e:
                logger.error("Error creating user: %s", e)
                return Response({'error': 'User creation failed due to integrity error.'}, status=status.HTTP_400_BAD_REQUEST)

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        return Response({
            'details': user_details,
            'jwt_token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


