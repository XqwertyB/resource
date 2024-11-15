from django.urls import path

from .views import (
    VideoStream, GetIpAddressAPIView,
)

urlpatterns = [
    path('stream-video/', VideoStream.as_view(), name='stream-video'),
    path('ip/', GetIpAddressAPIView.as_view()),


]
