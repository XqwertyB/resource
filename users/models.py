import uuid
from django.utils import timezone

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken

from users.constants import ROLES


class BaseModel(models.Model):
    """
    - Bu model har doim id, created_at va updated_at fieldlarni qayta yozmasdan har qanday modelda inherit qilib ishlash imkonini beruvchi class.

    - Bu class modelda yaratilmaydi sababi abstract=True deyilgani uchun.

    - Demak, qayta qayta yuqoridagi filedlarni yozmaslik uchun ishlab chiqilgan model

    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True




class UserManager(BaseUserManager):

    def _create_user(self, phone_number, password, is_staff=False, is_superuser=False, **extra_fields):
        if not phone_number:
            raise ValueError('Foydalanuvchilar telefon raqami saqlanishi shart')
        user, created = self.model.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'is_staff': is_staff,
                'is_active': True,
                'is_superuser': is_superuser,
                'last_login': timezone.now(),
                'date_joined': timezone.now(),
                **extra_fields
            }
        )
        if created:
            user.set_password(password)
            user.save(using=self._db)
        return user

    def create_user(self, phone_number, password, **extra_fields):
        return self._create_user(phone_number, password, False, False, **extra_fields)

    def create_superuser(self, phone_number, password, **extra_fields):
        user = self._create_user(phone_number, password, True, True, **extra_fields)
        user.role = 'admin'
        user.save(using=self._db)
        return user


class User(AbstractUser, BaseModel):
    _validate_phone = RegexValidator(
        regex=r"^998([3578]{2}|(9[013-57-9]))\d{7}$",
        message="Your phone number must start with 9 and not exceed 12 characters. For example: 998901234567",
    )

    # Remove 'last_name' and 'username' fields from the model since they are not needed
    last_name = None
    username = None

    # Custom fields for your user model
    employee_id_number = models.CharField(max_length=200, null=True)
    student_id_number = models.CharField(max_length=200, null=True)
    first_name = models.CharField(max_length=100, null=True)
    second_name = models.CharField(max_length=100, null=True)
    birth_date = models.DateTimeField(null=True)
    gender = models.CharField(max_length=20, null=True)
    phone_number = models.CharField(max_length=12, null=True, blank=True, unique=True, validators=[_validate_phone])
    employeeType = models.CharField("O'qtuvchi turi", max_length=200, null=True)
    department = models.CharField("O'qitish fani", max_length=100, null=True, blank=True)
    bio_info = models.TextField("BIO_Info", max_length=1000, null=True, blank=True)
    role = models.CharField(choices=ROLES, max_length=60)

    # Define phone_number as the unique username field
    USERNAME_FIELD = 'phone_number'

    # UserManager ensures custom handling for creating users
    objects = UserManager()

    def __str__(self):
        return str(self.first_name)

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to include any custom logic
        before saving a user.
        """
        if self.pk:
            # Optionally, you could clean the model fields if needed.
            # self.clean()  # Only call clean() if you have extra validation in clean()
            pass
        super(User, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Remove any '+' from the phone number before saving
        if self.phone_number:
            self.phone_number = self.phone_number.replace('+', '')

        super(User, self).save(*args, **kwargs)


class APISettings(models.Model):
    base_url = models.URLField(verbose_name='Base URL', help_text='URL для получения списка студентов')
    token = models.CharField(max_length=255, verbose_name='API Token', help_text='Токен для доступа к API')

    class Meta:
        verbose_name = "API Settings"
        verbose_name_plural = "API Settings"

    def __str__(self):
        return "API Configuration"