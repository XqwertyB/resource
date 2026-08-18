from django.test import SimpleTestCase
from django.urls import reverse


class OAuthRouteTests(SimpleTestCase):
    def test_student_oauth_authorization_route(self):
        self.assertEqual(reverse('student-oauth-authorize'), '/api/v1/oauth/student/authorize/')

