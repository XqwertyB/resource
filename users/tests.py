from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from content.models import Rating  # Импортируйте модель Rating
from content.forms import RatingForms


class AddRatingTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('addrating/')  # Замените 'add_rating' на реальный путь к вашему API

    def test_valid_rating_creation(self):
        data = {
            "recourse_id": 1,
            "start": 5
        }
        response = self.client.post(self.url, data, format='json')

        # Проверяем, что запрос успешен
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем, что запись создана с корректными данными
        rating = Rating.objects.get(recourse_id=1, ip='127.0.0.1')  # Замените на правильный способ извлечения IP
        self.assertEqual(rating.star_id, 5)

    def test_invalid_rating_missing_field(self):
        data = {
            "recourse_id": 1
            # Поле "start" отсутствует
        }
        response = self.client.post(self.url, data, format='json')

        # Проверяем, что запрос отклонен
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_invalid_rating_form_validation(self):
        data = {
            "recourse_id": "invalid",  # Неверный тип данных
            "start": "invalid"  # Неверный тип данных
        }
        response = self.client.post(self.url, data, format='json')

        # Проверяем, что форма отклоняет неверные данные
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recourse_id', response.data)
        self.assertIn('start', response.data)

