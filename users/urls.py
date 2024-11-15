from django.urls import path

from content.views import RecCreateView, RecView, RecUpDe,  ReviewRecourseAPIView
from users.views import (get_and_save_all_pages, DataImportView,
                         oAuthAuthorizationView, oAuthCallbackView, LoginView, \
                         )

urlpatterns = [
    #path('save_teacher/', get_and_save_all_pages, ),
    path('save_teacher/', DataImportView.as_view()),
    path('login/', oAuthAuthorizationView.as_view()),
    path('login/student/', LoginView.as_view()),
    path('callback/', oAuthCallbackView.as_view()),
    path('recourse-create/', RecCreateView.as_view()),
    path('recourse/', RecView.as_view()),
    path('recourse_up_del/<str:pk>/', RecUpDe.as_view()),
    path('recourse/<int:recourse_id>/reviews/', ReviewRecourseAPIView.as_view(), name='recourse-reviews'),
    path('reviews/<int:pk>/', ReviewRecourseAPIView.as_view(), name='review-detail'),


]
