from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission

from users.models import User


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            student = Student.objects.select_related('user').get(user=request.user)
            return student.user.role == 'student'
        except ObjectDoesNotExist:
            return False


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            employee = Employee.objects.select_related('user').get(user=request.user)
            return employee.user.role == 'teacher'
        except ObjectDoesNotExist:
            return False


class IsTeacherOrStudent(BasePermission):
    allowed_roles = {'teacher', 'student'}

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        is_student = Student.objects.filter(user=request.user).exists()
        is_teacher = Employee.objects.filter(user=request.user).exists()

        return (is_student or is_teacher) and request.user.role in self.allowed_roles
