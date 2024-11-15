from tkinter.font import names

import requests
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from . import models
from .models import  ReviewRecourse


class Category(serializers.ModelSerializer):
    class Meta:
        model = models.Category
        fields = ['id', 'name']

class Sub_CatSerializers(serializers.ModelSerializer):
    sub_category = Category()
    class Meta:
        model = models.Sub_Category
        fields = [ 'id', 'name', 'sub_category']


class FileSerializers(serializers.ModelSerializer):
    class Meta:
        model = models.Files
        fields = ['id', 'name', 'file']

class VideoSerializers(serializers.ModelSerializer):
    class Meta:
        model = models.Videos
        fields = ['id', 'name', 'video_file']

class UserRecSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ['first_name']

class RecSerializers(serializers.ModelSerializer):
    sub_category = Sub_CatSerializers()
    file = FileSerializers()
    video = VideoSerializers()

    class Meta:
        model = models.Recourse
        fields = ['id', 'sub_category', 'file', 'video', 'typ', 'info', 'user', ]


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        login = data.get('login')
        password = data.get('password')

        if not login:
            raise ValidationError("Login is required.")
        if not password:
            raise ValidationError("Password is required.")

        # Attempt authentication with Django’s built-in authenticate method
        authentication_kwargs = {'username': login, 'password': password}
        user = authenticate(**authentication_kwargs)

        if user:
            # If user is found, attach to serializer and return success with role
            self.user = user
            return {
                "message": "Login successful.",
                "jwt_tokens": self.user.token(),
                "role": self.user.role.lower()
            }
        else:
            # Handle student ID-based authentication through external service
            token = self.verify_student_password(login, password)
            if token:
                # Create JWT tokens for the student and return them
                jwt_tokens = self.create_jwt_token(login)
                return {
                    "message": "Login successful.",
                    "jwt_tokens": jwt_tokens,
                    "role": jwt_tokens.get("role")
                }

        raise ValidationError("Authentication failed.")

    def get_user(self, **kwargs):
        users = User.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError("No active account found.")
        return users.first()

    def verify_student_password(self, login, password):
        url = "https://talaba.tsue.uz/rest/v1/auth/login"
        payload = {
            "login": login,
            "password": password
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success'):
                    res_user_data = requests.get(
                        'https://talaba.tsue.uz/rest/v1/account/me',
                        headers={"Authorization": f"Bearer {response_data['data']['token']}"}
                    )
                    res_user_data_new = res_user_data.json()

                    # Create or update local user with the fetched student data
                    user, created = User.objects.get_or_create(
                        student_id_number=login,
                        defaults={
                            'password': make_password(password),
                            'first_name': res_user_data_new['data']['first_name'],
                            'second_name': res_user_data_new['data']['second_name'],
                            'gender': res_user_data_new['data']['gender']['name'],
                            'role': 'talaba'
                        }
                    )

                    # If existing user, just return the token
                    return response_data['data'].get('token')

                raise ValidationError("Invalid student ID number or password.")
            else:
                raise ValidationError(f"Error: Received status code {response.status_code}")
        except requests.RequestException as e:
            raise ValidationError(f"Error during request: {e}")

    def create_jwt_token(self, student_id_number):
        try:
            user = User.objects.get(student_id_number=student_id_number)
            refresh = RefreshToken.for_user(user)
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                "role": user.role.lower()
            }
        except User.DoesNotExist:
            raise ValidationError("User not found.")

class ReviewRecourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewRecourse
        fields = ['id', 'recourse', 'user', 'text', 'rating', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']