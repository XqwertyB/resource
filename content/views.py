from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView
from users.permission import IsTeacher, IsStudent
from . import models
from .models import Recourse, RecViews, ReviewRecourse
from .serializers import RecSerializers, ReviewRecourseSerializer


class RecCreateView(APIView):
    permission_classes = [IsTeacher,]
    def post(self, request):
        user = request.user

        data = request.data.copy()  # Делаем копию данных запроса
        data['user'] = user.id


        serializer = RecSerializers(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecView(APIView):
    #permission_classes = [IsTeacher, IsStudent,]
    def get(self, request, *args, **kwargs):
        sub_category_name = request.query_params.get('sub_category')
        typ = request.query_params.get('typ')
        queryset = Recourse.objects.all()
        if sub_category_name:
            queryset = queryset.filter(sub_category__name__iexact=sub_category_name)
        if typ:
            queryset=queryset.filter(typ=typ)
        serializer = RecSerializers(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecUpDe(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.Recourse.objects.all()
    serializer_class = RecSerializers
    permission_classes = [IsTeacher,]


class RecDetail(APIView):
    def get(self, request, pk, ):
        # Получаем объект вакансии по его ID
        rec = get_object_or_404(Recourse, pk=pk)

        # Получаем текущего пользователя
        user = request.user

        # Проверяем, просматривал ли пользователь эту вакансию ранее
        rec_viewed = RecViews.objects.filter(user=user, rec=rec).exists()

        if not rec_viewed:
            # Увеличиваем количество просмотров на 1
            rec.view_count += 1
            rec.save()

            # Записываем, что пользователь просмотрел вакансию
            RecViews.objects.create(user=user, rec=rec)

        # Сериализуем объект для отображения
        serializer = RecSerializers(rec)

        # Возвращаем ответ с данными вакансии
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReviewRecourseAPIView(APIView):
    permission_classes = [IsAuthenticated,]


    def get(self, request, recourse_id):
        reviews = ReviewRecourse.objects.filter(recourse_id=recourse_id)
        serializer = ReviewRecourseSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

