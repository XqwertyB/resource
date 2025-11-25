import requests
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response






class GetIpAddressAPIView(APIView):
    def get(self, request, format=None):
        client_ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '')

        return Response({'client_ip_address': client_ip_address})




class VideoStream(APIView):
    def get(self, request):
        video_path = 'media/video_content/Oqtuvchi profili2024-08-20 17-54-11-483.mp4'

        def stream_video():
            with open(video_path, 'rb') as video_file:
                while True:
                    chunk = video_file.read(10240)
                    if not chunk:
                        break
                    yield chunk

        response = StreamingHttpResponse(stream_video(), content_type='video/mp4')
        response['Content-Disposition'] = 'inline; filename="video.mp4"'
        return response



