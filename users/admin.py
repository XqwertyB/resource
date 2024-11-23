import time
import requests  # Correct import

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from .models import APISettings, User



class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'first_name', 'role', 'is_staff', 'is_superuser')

    # Fields used for searching in the admin dashboard
    search_fields = ('phone_number', 'first_name', 'second_name', 'employee_id_number')

    # Ordering of the user entries
    ordering = ['phone_number']

    # Customize the fields and layout in the form for creating and editing users
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'second_name', 'birth_date', 'role', 'department', 'employee_id_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields displayed when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'first_name', 'role'),
        }),
    )

    def changelist_view(self, request, extra_context=None):
        if 'load-data' in request.GET:
            try:
                self.load_data_from_api(request)
            except Exception as e:
                self.message_user(request, f"Error: {str(e)}", level=messages.ERROR)
            return HttpResponseRedirect(request.path)

        extra_context = extra_context or {}
        extra_context['custom_button'] = True  # Pass context for button visibility
        return super().changelist_view(request, extra_context=extra_context)

    # Функция для загрузки данных из API
    def load_data_from_api(self, request):
        try:
            api_settings = APISettings.objects.first()
            if not api_settings:
                self.message_user(request, "API settings not configured", level=messages.ERROR)
                return
            base_url = api_settings.base_url
            token = api_settings.token
        except APISettings.DoesNotExist:
            self.message_user(request, "API settings not configured", level=messages.ERROR)
            return

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        page = 1
        saved_count = 0
        start_time = time.time()

        while True:
            response = requests.get(f"{base_url}?page={page}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data['data']['items']:
                    if not User.objects.filter(employee_id_number=item['employee_id_number']).exists():
                        # Создание записей в базе данных
                        User.objects.create(
                            employee_id_number=item['employee_id_number'],
                            first_name=item['first_name'],
                            second_name=item['second_name'],
                            gender=item['gender']['name'],
                            employeeType=item['employeeType']['name'],
                            birth_date=item['birth_date'],
                            role='teacher'
                        )
                        saved_count += 1

                # Проверка на наличие следующей страницы
                if page >= data['data']['pagination']['pageCount']:
                    break
                page += 1
                time.sleep(1)
            else:
                self.message_user(request, "Error retrieving data", level=messages.ERROR)
                return

        total_duration = time.time() - start_time
        self.message_user(request, f"Data saved. Total saved: {saved_count}. Duration: {total_duration:.2f} seconds.",
                          level=messages.SUCCESS)

    # Добавление кастомного URL для кнопки
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('load-data/', self.admin_site.admin_view(self.changelist_view), name='load-data'),
        ]
        return custom_urls + urls


admin.site.register(User, UserAdmin)

@admin.register(APISettings)
class APISettingsAdmin(admin.ModelAdmin):
    list_display = ('base_url', 'token')
    search_fields = ('base_url',)


