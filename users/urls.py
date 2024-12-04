from django.urls import path

from content.views import RecCreateView, RecView, RecUpDe, ReviewRecourseAPIView, RecUserContent, AddLike, \
    RecDetail, CategoryCreateView, CategoryView, RecUserVideo, RecUserFile, RecVideo, RecFile, RecVideoDetail, \
    CommentVideo, CommentVideoDel
from users.views import (DataImportView, oAuthAuthorizationView, OAuthCallbackView, LoginView, UserDetailView, \
                         )

urlpatterns = [
    path('save_teacher/', DataImportView.as_view(), name="O'qtuvchilarni yuklab olish"),
    path('login/', oAuthAuthorizationView.as_view(), name="Login o'qtuvchilar uchun"),
    path('login/student/', LoginView.as_view(), name='login talabalar uchun'),
    path('callback/<str:code>', OAuthCallbackView.as_view()),
    path('resourceuser/', RecUserContent.as_view(), name="Userga tegishli resurslar" ),
    path('recourse-create/', RecCreateView.as_view(), name="resurs yaratish"),
    path('recourse/', RecView.as_view(), name="barcha resurslar"),
    path('recourse/detail/<str:pk>/', RecDetail.as_view()),
    path('recourse_up_del/<str:pk>/', RecUpDe.as_view(), name="resursni update qilish yoki uchirish"),
    path('recourse/<str:recourse_id>/reviews/', ReviewRecourseAPIView.as_view(), name='recourse-reviews'),
    path('reviews/<str:pk>/', ReviewRecourseAPIView.as_view(), name='review-detail'),
    path('<str:pk>/add_likes', AddLike.as_view(), name='Like quyish'),
    path('category/create/', CategoryCreateView.as_view()),
    path('category/', CategoryView.as_view()),
    path('getme/', UserDetailView.as_view()),
    path('videos/user/', RecUserVideo.as_view()),
    path('files/user/', RecUserFile.as_view()),
    path('videos/', RecVideo.as_view()),
    path('video/detail/<str:pk>/', RecVideoDetail.as_view()),
    path('videos/<str:pk>/reviews/', CommentVideo.as_view()),
    path('videos/<str:pk>/reviews/delet/', CommentVideoDel.as_view()),
    path('files/', RecFile.as_view())


]
