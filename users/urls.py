from django.urls import path

from content.views import RecCreateView, RecView, RecUpDe, ReviewRecourseAPIView, RecUserContent, AddLike, DelLike
from users.views import ( DataImportView, oAuthAuthorizationView, OAuthCallbackView, LoginView, \
                         )

urlpatterns = [
    path('save_teacher/', DataImportView.as_view(), name="O'qtuvchilarni yuklab olish"),
    path('login/', oAuthAuthorizationView.as_view(), name="Login o'qtuvchilar uchun"),
    path('login/student/', LoginView.as_view(), name='login talabalar uchun'),
    path('callback/<str:code>', OAuthCallbackView.as_view()),
    path('resourceuser/', RecUserContent.as_view(), name="Userga tegishli resurslar" ),
    path('recourse-create/', RecCreateView.as_view(), name="resurs yaratish"),
    path('recourse/', RecView.as_view(), name="barcha resurslar"),
    path('recourse_up_del/<str:pk>/', RecUpDe.as_view(), name="resursni update qilish yoki uchirish"),
    path('recourse/<int:recourse_id>/reviews/', ReviewRecourseAPIView.as_view(), name='recourse-reviews'),
    path('reviews/<int:pk>/', ReviewRecourseAPIView.as_view(), name='review-detail'),
    path('<str:pk>/add_likes', AddLike.as_view(), name='Like quyish'),
    path('<str:pk>/del_likes', DelLike.as_view(), name= 'Likeni uchirish'),


]
