from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import time

from rest_framework_simplejwt.tokens import RefreshToken


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page_number'
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page_count': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


student, teacher, employee, admin = 'student', 'teacher', 'employee', 'admin'
ROLES = (
    (student, student),
    (teacher, teacher),
    (employee, employee),
    (admin, admin)
)
