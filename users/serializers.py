from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.sites import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


class GetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id",
                  "date_joined",
                  "created_at",
                  "updated_at",
                  "employee_id_number",
                  "first_name",
		          "second_name",
		          "birth_date",
                  "phone_number",
		          "department",
                  "role")