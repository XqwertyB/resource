import os
import logging
from uuid import UUID

from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


from users.permission import IsTeacher, IsStudent
from . import models
from .models import Recourse, RecViews, ReviewRecourse, Likes, Category, Videos, Files, ReviewVideos
from .serializers import RecSerializer, ReviewRecourseSerializer, ResViewSerializers, CategorySerializer, \
    VideoSerializers, FileSerializers, ReviewVideosSerializer

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# class RecCreateView(APIView):
#     permission_classes = [IsTeacher]
#
#     @swagger_auto_schema(request_body=RecSerializer)
#     def post(self, request):
#         user = request.user
#         data = request.data.copy()
#
#         # Обработка файла
#         if 'file' in request.FILES:
#             data['file'] = {
#                 'name': data.get('name', 'Unnamed File'),
#                 'file': request.FILES['file']
#             }
#
#         # Обработка видео
#         if 'video_file' in request.FILES:
#             data['video'] = {
#                 'name': data.get('name', 'Unnamed Video'),
#                 'video_file': request.FILES['video_file']
#             }
#
#         serializer = RecSerializer(data=data, context={'req_user': user})
#
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecCreateView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser, FormParser]

    # Разрешенные MIME-типы и расширения файлов
    ALLOWED_FILE_TYPES = {
        'file': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ],
        'video': [
            'video/mp4',
            'video/avi',
            'video/mpeg',
            'video/quicktime'
        ]
    }

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB

    def validate_file(self, file, file_type):
        """Валидация загружаемых файлов"""

        # Проверка размера файла
        if file_type == 'file' and file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"Размер файла не должен превышать {self.MAX_FILE_SIZE // (1024 * 1024)}MB")

        if file_type == 'video' and file.size > self.MAX_VIDEO_SIZE:
            raise ValidationError(f"Размер видео не должен превышать {self.MAX_VIDEO_SIZE // (1024 * 1024)}MB")

        # Проверка MIME-типа
        if file.content_type not in self.ALLOWED_FILE_TYPES[file_type]:
            raise ValidationError(f"Недопустимый тип файла. Разрешены: {', '.join(self.ALLOWED_FILE_TYPES[file_type])}")

        # Проверка расширения файла
        ext = os.path.splitext(file.name)[1].lower()
        allowed_extensions = {
            'file': ['.pdf', '.doc', '.docx'],
            'video': ['.mp4', '.avi', '.mov', '.mpeg']
        }

        if ext not in allowed_extensions[file_type]:
            raise ValidationError(
                f"Недопустимое расширение файла. Разрешены: {', '.join(allowed_extensions[file_type])}")

    def check_contextual_permission(self, user, data):
        """The current Recourse schema has no course/group relation."""
        return True

    @swagger_auto_schema(request_body=RecSerializer)
    def post(self, request):
        user = request.user

        # Логирование попытки создания записи
        logger.info(f"User {user.id} attempting to create Rec record")

        # Валидация загружаемых файлов
        files = request.FILES
        validation_errors = {}

        if 'file' in files:
            try:
                self.validate_file(files['file'], 'file')
            except ValidationError as e:
                validation_errors['file'] = str(e)

        if 'video' in files:
            try:
                self.validate_file(files['video'], 'video')
            except ValidationError as e:
                validation_errors['video'] = str(e)

        if validation_errors:
            return Response(
                {"errors": validation_errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Подготовка данных
        data = request.data.copy()

        # Проверка контекстных прав доступа
        try:
            self.check_contextual_permission(user, data)
        except (PermissionDenied, ValidationError) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDenied)
                else status.HTTP_400_BAD_REQUEST
            )

        # Создание сериализатора с контекстом пользователя
        serializer = RecSerializer(data=data, context={'req_user': user})

        if serializer.is_valid():
            try:
                instance = serializer.save()

                # Логирование успешного создания
                logger.info(f"User {user.id} successfully created Rec record {instance.id}")

                # Возвращаем только необходимые данные, исключая чувствительную информацию
                response_data = {
                    'id': instance.id,
                    'status': 'created',
                    'message': 'Запись успешно создана'
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Логирование ошибок базы данных
                logger.error(f"Error creating Rec record for user {user.id}: {str(e)}")
                return Response(
                    {"error": "Ошибка при создании записи"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecView(APIView):
    permission_classes = [IsAuthenticated]  # Только аутентифицированные пользователи
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        """
        Динамическое назначение разрешений в зависимости от метода
        """
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsTeacher()]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'category',
                openapi.IN_QUERY,
                description="Filter by subcategory name",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'typ',
                openapi.IN_QUERY,
                description="Filter by type",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'page_size',
                openapi.IN_QUERY,
                description="Number of results per page",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            200: ResViewSerializers(many=True),
            403: 'Forbidden - insufficient permissions'
        }
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        category_name = request.query_params.get('category')
        typ = request.query_params.get('typ')

        if user.role not in {'teacher', 'talaba', 'student', 'admin', 'moderator'}:
            return Response(
                {"error": "Недостаточно прав для просмотра записей"},
                status=status.HTTP_403_FORBIDDEN
            )
        queryset = Recourse.objects.all()

        # Применение фильтров
        if category_name:
            queryset = queryset.filter(category__name__iexact=category_name)
        if typ:
            queryset = queryset.filter(typ=typ)

        # Пагинация
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        if page is not None:
            serializer = ResViewSerializers(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ResViewSerializers(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecUpDe(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RecSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        """
        Ограничиваем queryset только записями, к которым пользователь имеет права
        """
        if getattr(self, 'swagger_fake_view', False):
            # Вызывается drf-yasg при генерации схемы, где request.user = AnonymousUser
            return Recourse.objects.none()

        user = self.request.user
        return Recourse.objects.filter(user=user)

    def perform_update(self, serializer):
        """Дополнительная валидация при обновлении"""
        instance = self.get_object()
        user = self.request.user

        # Проверка, что пользователь является владельцем
        if instance.user != user:
            raise PermissionDenied("Вы можете изменять только свои записи")

        serializer.save()

    def perform_destroy(self, instance):
        """Дополнительная валидация при удалении"""
        user = self.request.user

        if instance.user != user:
            raise PermissionDenied("Вы можете удалять только свои записи")

        # Логирование удаления
        logger.warning(f"User {user.id} deleting Recourse {instance.id}")
        instance.delete()


class RecDetail(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: ResViewSerializers,
            403: 'Forbidden - no access to this resource',
            404: 'Resource not found'
        }
    )
    def get(self, request, pk):
        user = request.user

        try:
            # Получаем запись с проверкой прав доступа
            rec = self.get_authorized_recourse(pk, user)
        except Recourse.DoesNotExist:
            return Response(
                {"error": "Ресурс не найден или у вас нет прав доступа"},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied:
            return Response(
                {"error": "У вас нет прав для просмотра этого ресурса"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Обновление счетчика просмотров
        self.handle_view_tracking(user, rec)

        serializer = ResViewSerializers(rec)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_authorized_recourse(self, pk, user):
        """
        Получение записи с проверкой прав доступа
        """
        rec = get_object_or_404(Recourse, pk=pk)

        if user.role not in {'teacher', 'talaba', 'student', 'admin', 'moderator'}:
            raise PermissionDenied()

        return rec

    def handle_view_tracking(self, user, rec):
        # The current schema tracks views only for Videos, not for Recourse.
        return None


class ReviewRecourseAPIView(APIView):
    permission_classes = [IsAuthenticated,]

    @swagger_auto_schema(
        # For GET requests, use query parameters
        manual_parameters=[
            openapi.Parameter(
                'param_name',
                openapi.IN_QUERY,
                description="Description of the query parameter",
                type=openapi.TYPE_STRING,
            ),
        ]
    )

    def get(self, request, recourse_id):
        reviews = ReviewRecourse.objects.filter(recourse_id=recourse_id)
        serializer = ReviewRecourseSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=ReviewRecourseSerializer)
    def post(self, request, recourse_id):
        data = request.data.copy()
        data['recourse'] = recourse_id
        serializer = ReviewRecourseSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, pk):
        try:
            review = ReviewRecourse.objects.get(pk=pk, user=request.user)
        except ReviewRecourse.DoesNotExist:
            return Response({"error": "Review not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

        review.delete()
        return Response({"message": "Review deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class RecUserContent(APIView):
    permission_classes = [IsTeacher,]
    #@swagger_auto_schema(request_body=ReviewRecourseSerializer)
    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            UUID(str(user.id))  # Validate UUID
        except (ValueError, AttributeError):
            return Response({"detail": "Invalid user ID format."}, status=400)

        obj = Recourse.objects.filter(user=user)
        serializes = ResViewSerializers(obj, many=True)
        recourse_ids = obj.values_list('id', flat=True)
        reviews = ReviewRecourse.objects.filter(recourse_id__in=recourse_ids)
        review_serializer = ReviewRecourseSerializer(reviews, many=True)


        response_data = {
            "recourses": serializes.data,
            "reviews": review_serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

def get_client_ip(request):
    x_forwarded_for =request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or "0.0.0.0"


class AddLike(APIView):
    def post(self, request, pk):
        ip_client = get_client_ip(request)
        if not ip_client:
            return Response({"error": "Unable to fetch client IP"}, status=400)

        try:
            # Check if the like already exists
            like = Likes.objects.get(ip=ip_client, resource_id=pk)
            # If it exists, delete it (unlike)
            like.delete()
            return Response({"message": "Like removed"}, status=200)
        except Likes.DoesNotExist:
            # If it does not exist, create a new like
            Likes.objects.create(ip=ip_client, resource_id=pk)
            return Response({"message": "Like added"}, status=201)


class CategoryCreateView(APIView):
    permission_classes = [IsTeacher,]
    @swagger_auto_schema(request_body=CategorySerializer)
    def post(self, request):
        user = request.user

        data = request.data.copy()
        data['user'] = user.id


        serializer = CategorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryView(APIView):
    def get(self, request):
        queryset = Category.objects.all()
        serializer = CategorySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class RecUserVideo(APIView):
    permission_classes = [IsTeacher,]
    #@swagger_auto_schema(request_body=ReviewRecourseSerializer)
    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            UUID(str(user.id))  # Validate UUID
        except (ValueError, AttributeError):
            return Response({"detail": "Invalid user ID format."}, status=400)

        obj = Videos.objects.filter(user=user)
        serializes = VideoSerializers(obj, many=True)
        response_data = {
            "video": serializes.data,
        }
        return Response(response_data, status=status.HTTP_200_OK)
@method_decorator(csrf_exempt, name='dispatch')
class RecUserFile(APIView):
    permission_classes = [IsTeacher]

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            UUID(str(user.id))
        except (ValueError, AttributeError):
            return Response({"detail": "Invalid user ID format."}, status=400)

        # Query the files for the user
        obj = Files.objects.filter(user=user)


        # Serialize the queryset without converting to a list
        serialized = FileSerializers(obj, many=True)

        return Response(serialized.data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class RecVideo(APIView):
    permission_classes = [IsAuthenticated,]
    #@swagger_auto_schema(request_body=ReviewRecourseSerializer)
    def get(self, request, *args, **kwargs):
        obj = Videos.objects.all()
        serializes = VideoSerializers(obj, many=True)
        response_data = {
            "video": serializes.data,
        }
        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class RecFile(APIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request, *args, **kwargs):
        obj = Files.objects.all()


        serialized = FileSerializers(obj, many=True)

        return Response(serialized.data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class RecVideoDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            # Fetch the video
            video = Videos.objects.get(pk=pk)

            # Serialize the video
            video_serializer = VideoSerializers(video)

            # Fetch and serialize reviews
            reviews = ReviewVideos.objects.filter(video=video)
            reviews_serializer = ReviewVideosSerializer(reviews, many=True)

            # Count likes for the video
            like_count = Likes.objects.filter(resource_id=pk).count()

            # Check if the video has been viewed by the user
            user = request.user
            rec_viewed = RecViews.objects.filter(user=user, video=video).exists()

            if not rec_viewed:
                # Increment view count and save
                video.view_count += 1
                video.save()

                # Record the view
                RecViews.objects.create(user=user, video=video)

            # Prepare the response data
            response_data = {
                "video": video_serializer.data,
                "reviews": reviews_serializer.data,
                "like_count": like_count,  # Add the like count here
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Videos.DoesNotExist:
            return Response(
                {"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND
            )



class CommentVideo(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            video = Videos.objects.get(pk=pk)
        except Videos.DoesNotExist:
            return Response(
                {"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Collect data for the serializer
        data = {
            "text": request.data.get("text"),  # Extract 'text' from request
            "user": request.user.id,  # Include user ID
        }

        # Pass the data to the serializer
        serializer = ReviewVideosSerializer(data=data)

        if serializer.is_valid():
            # Save the comment (if your model requires a video, handle it here)
            ReviewVideos.objects.create(
                text=serializer.validated_data['text'],
                user=request.user,
                video=video
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentVideoDel(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            # Find the review to delete by primary key
            review = ReviewVideos.objects.get(pk=pk, user=request.user)
        except ReviewVideos.DoesNotExist:
            return Response(
                {"error": "Review not found or you don't have permission to delete this comment"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete the review
        review.delete()
        return Response({"message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
