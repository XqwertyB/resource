from uuid import UUID

from django.shortcuts import get_object_or_404, redirect
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from users.permission import IsTeacher, IsStudent
from . import models
from .models import Recourse, RecViews, ReviewRecourse, Likes, Category
from .serializers import RecSerializer, ReviewRecourseSerializer, ResViewSerializers, CategorySerializer


class RecCreateView(APIView):
    permission_classes = [IsTeacher]

    @swagger_auto_schema(request_body=RecSerializer)
    def post(self, request):
        user = request.user
        data = request.data.copy()
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
    def get(self, request, pk, ):

        rec = get_object_or_404(Recourse, pk=pk)


        user = request.user


        rec_viewed = RecViews.objects.filter(user=user, rec=rec).exists()

        if not rec_viewed:

            rec.view_count += 1
            rec.save()

            # Записываем, что пользователь просмотрел вакансию
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