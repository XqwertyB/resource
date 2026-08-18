from django.urls import path

from content.views import RecCreateView, RecView, RecUpDe, ReviewRecourseAPIView, RecUserContent, AddLike, \
    RecDetail, CategoryCreateView, CategoryView, RecUserVideo, RecUserFile, RecVideo, RecFile, RecVideoDetail, \
    CommentVideo, CommentVideoDel
from users.oAuth2 import (
    StudentAuthorizationView,
    StudentCallbackView,
    TeacherAuthorizationView,
    TeacherCallbackView,
)
from users.views import LoginView, UserDetailView

urlpatterns = [
    path('login/', TeacherAuthorizationView.as_view(), name='teacher-oauth-authorize'),
    path('login/student/', StudentAuthorizationView.as_view(), name='student-oauth-login'),
    path('callback/', TeacherCallbackView.as_view(), name='teacher-oauth-callback'),
    path('login/student/password/', LoginView.as_view(), name='student-password-login'),
    path('oauth/teacher/authorize/', TeacherAuthorizationView.as_view(), name='teacher-oauth-authorize-v2'),
    path('oauth/teacher/callback/', TeacherCallbackView.as_view(), name='teacher-oauth-callback-v2'),
    path('oauth/student/authorize/', StudentAuthorizationView.as_view(), name='student-oauth-authorize'),
    path('oauth/student/callback/', StudentCallbackView.as_view(), name='student-oauth-callback'),
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
