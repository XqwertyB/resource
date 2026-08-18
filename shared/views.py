import requests
from pathlib import Path
from django.conf import settings
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
        video_path = Path(settings.MEDIA_ROOT) / 'video_content' / 'Oqtuvchi profili2024-08-20 17-54-11-483.mp4'
        if not video_path.is_file():
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)

        def stream_video():
            with video_path.open('rb') as video_file:
                while True:
                    chunk = video_file.read(10240)
                    if not chunk:
                        break
                    yield chunk

        response = StreamingHttpResponse(stream_video(), content_type='video/mp4')
        response['Content-Disposition'] = 'inline; filename="video.mp4"'
        return response



