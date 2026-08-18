from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role in {'student', 'talaba'})


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == 'teacher')


class IsTeacherOrStudent(BasePermission):
    allowed_roles = {'teacher', 'student', 'talaba'}

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role in self.allowed_roles)
