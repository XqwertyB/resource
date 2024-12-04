from uuid import UUID

from django.shortcuts import get_object_or_404, redirect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


from users.permission import IsTeacher, IsStudent
from . import models
from .models import Recourse, RecViews, ReviewRecourse, Likes, Category, Videos, Files, ReviewVideos
from .serializers import RecSerializer, ReviewRecourseSerializer, ResViewSerializers, CategorySerializer, \
    VideoSerializers, FileSerializers, ReviewVideosSerializer


class RecCreateView(APIView):
    permission_classes = [IsTeacher]

    @swagger_auto_schema(request_body=RecSerializer)
    def post(self, request):
        user = request.user
        data = request.data.copy()

        # Обработка файла
        if 'file' in request.FILES:
            data['file'] = {
                'name': data.get('name', 'Unnamed File'),
                'file': request.FILES['file']
            }

        # Обработка видео
        if 'video_file' in request.FILES:
            data['video'] = {
                'name': data.get('name', 'Unnamed Video'),
                'video_file': request.FILES['video_file']
            }

        serializer = RecSerializer(data=data, context={'req_user': user})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






class RecView(APIView):
    permission_classes = [IsTeacher, IsStudent,]

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
    def get(self, request, *args, **kwargs):
        sub_category_name = request.query_params.get('sub_category')
        typ = request.query_params.get('typ')
        queryset = Recourse.objects.all()
        if sub_category_name:
            queryset = queryset.filter(sub_category__name__iexact=sub_category_name)
        if typ:
            queryset=queryset.filter(typ=typ)
        serializer = ResViewSerializers(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecUpDe(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Recourse.objects.all()
    serializer_class = RecSerializer
    permission_classes = [IsTeacher,]


class RecDetail(APIView):
    permission_classes = [IsAuthenticated,]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'param_name',
                openapi.IN_QUERY,
                description="Description of the query parameter",
                type=openapi.TYPE_STRING,
            ),
        ]
    )
    def get(self, request, pk, ):

        rec = get_object_or_404(Recourse, pk=pk)
        user = request.user
        rec_viewed = RecViews.objects.filter(user=user, rec=rec).exists()
        if not rec_viewed:
            rec.view_count += 1
            rec.save()

            RecViews.objects.create(user=user, rec=rec)
        serializer = ResViewSerializers(rec)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
    def get(self, request, pk):
        ip_client = get_client_ip(request)
        if not ip_client:
            return Response({"error": "Unable to fetch client IP"}, status=400)

        try:
            Likes.objects.get(ip=ip_client, resource_id=pk)
            return redirect(f'/{pk}')
        except Likes.DoesNotExist:
            new_like = Likes()
            new_like.ip = ip_client
            new_like.resource_id = pk
            new_like.save()
            return redirect(f'/{pk}')

class DelLike(APIView):
    def get(self, request, pk):
        ip_client = get_client_ip(request)
        try:
            lik = Likes.objects.get(ip=ip_client)
            lik.delete()
            return redirect(f'/{pk}')
        except:
            return redirect(f'/{pk}')


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
        if not obj.exists():
            return Response({"detail": "No video found for the user."}, status=404)

        # Serialize the queryset without converting to a list
        serialized = FileSerializers(obj, many=True)

        return Response(serialized.data, status=status.HTTP_200_OK)



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

class RecFile(APIView):
    permission_classes = [IsAuthenticated,]

    def get(self, request, *args, **kwargs):
        obj = Files.objects.all()
        if not obj.exists():
            return Response({"detail": "No files found."}, status=404)


        serialized = FileSerializers(obj, many=True)

        return Response(serialized.data, status=status.HTTP_200_OK)


class RecVideoDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:

            video = Videos.objects.get(pk=pk)
            video_serializer = VideoSerializers(video)
            reviews = ReviewVideos.objects.filter(video=video)
            reviews_serializer = ReviewVideosSerializer(reviews, many=True)
            user = request.user
            rec_viewed = RecViews.objects.filter(user=user, video=video).exists()
            if not rec_viewed:
                video.view_count += 1
                video.save()

                RecViews.objects.create(user=user, video=video)
            response_data = {
                "video": video_serializer.data,
                "reviews": reviews_serializer.data,
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


        data = request.data
        data["video"] = video.id
        data["user"] = request.user.id

        serializer = ReviewVideosSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)