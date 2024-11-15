from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.sites import requests
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


