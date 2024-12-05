import requests
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from .models import ReviewRecourse, Files, Videos, Recourse, Category, ReviewVideos


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
        read_only_fields = ['id', ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'second_name']


class ResourceSerializers(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    class Meta:
        model = Recourse
        fields = ["category", "typ", "info", ]


class FileSerializers(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    recourse = ResourceSerializers(read_only=True)
    class Meta:
        model = Files
        fields = ['id', 'name', 'file', 'recourse', 'user' ]


class VideoSerializers(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    recourse = ResourceSerializers(read_only=True)
    class Meta:
        model = Videos
        fields = ['id', 'name', 'video_file', 'recourse', 'user' ]
        read_only_fields = ['id', ]

class CreateFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Files
        fields = ['id', 'name', 'file']
        read_only_fields = ['id']

class CreateVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Videos
        fields = ['id', 'name', 'video_file']
        read_only_fields = ['id']


class RecSerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    file_data = serializers.FileField(required=False)
    video_data = serializers.FileField(required=False)

    class Meta:
        model = Recourse
        fields = ['category', 'typ', 'info', 'file_data', 'video_data',]

    def create(self, validated_data):
        user = self.context.get('req_user')
        if not user:
            raise serializers.ValidationError("User is required in the context.")

        # Extract file and video data
        file_data = validated_data.pop('file_data', None)
        video_data = validated_data.pop('video_data', None)

        # Create the Recourse object
        recourse = Recourse.objects.create(user=user, **validated_data)

        # Handle file upload
        if file_data:
            Files.objects.create(
                user=user,
                recourse=recourse,
                name=file_data.name,
                file=file_data
            )

        # Handle video upload
        if video_data:
            Videos.objects.create(
                user=user,
                recourse=recourse,
                name=video_data.name,
                video_file=video_data
            )

        return recourse




class ReviewRecourseSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ReviewRecourse
        fields = ['id',  'text', 'user']


class ResViewSerializers(serializers.ModelSerializer):
    reviews = ReviewRecourseSerializer(many=True, read_only=True,)
    files = CreateFileSerializer(many=True, read_only=True)
    videos = CreateVideoSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    class Meta:
        model = Recourse
        fields = ['id', 'category', 'files', 'videos', 'typ', 'info', 'reviews']


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

        authentication_kwargs = {'username': login, 'password': password}
        user = authenticate(**authentication_kwargs)

        if user:

            self.user = user
            return {
                "message": "Login successful.",
                "jwt_tokens": self.user.token(),
                "role": self.user.role.lower()
            }
        else:

            token = self.verify_student_password(login, password)
            if token:
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
        fields = ['id', 'recourse', 'user', 'text',  'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ReviewVideosSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    text = serializers.CharField()
    class Meta:
        model = ReviewVideos
        fields = ['user', 'text' ]