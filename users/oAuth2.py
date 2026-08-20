"""OAuth 2.0 authorization endpoints for HEMIS students and teachers."""

from datetime import datetime
from uuid import uuid4

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.settings import (
    CLIENT_ID,
    CLIENT_SECRET,
    REDIRECT_URI,
    STUDENT_AUTHORIZE_URL,
    STUDENT_CLIENT_ID,
    STUDENT_CLIENT_SECRET,
    STUDENT_REDIRECT_URI,
    STUDENT_RESOURCE_OWNER_URL,
    STUDENT_TOKEN_URL,
)
from .client import OAuth2Client
from .models import User


TEACHER_OAUTH = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "authorize_url": "https://hemis.nspi.uz/oauth/authorize",
    "token_url": "https://hemis.nspi.uz/oauth/access-token",
    "resource_owner_url": "https://hemis.nspi.uz/oauth/api/user",
}
STUDENT_OAUTH = {
    "client_id": STUDENT_CLIENT_ID,
    "client_secret": STUDENT_CLIENT_SECRET,
    "redirect_uri": STUDENT_REDIRECT_URI,
    "authorize_url": STUDENT_AUTHORIZE_URL,
    "token_url": STUDENT_TOKEN_URL,
    "resource_owner_url": STUDENT_RESOURCE_OWNER_URL,
}


def parse_birth_date(value):
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None


class HemisOAuthMixin:
    oauth_settings = None
    account_role = None

    def get_client(self):
        return OAuth2Client(**self.oauth_settings)

    def get_profile(self, details):
        """Normalize both HEMIS response shapes into local User fields."""
        data = details.get("data", details)
        if self.account_role == "talaba":
            identifier_field = "student_id_number"
            identifier = data.get(identifier_field)
        else:
            identifier_field = "employee_id_number"
            identifier = data.get(identifier_field) or data.get("id")

        if not identifier:
            return None, None, None

        gender = data.get("gender")
        if isinstance(gender, dict):
            gender = gender.get("name")
        departments = data.get("departments") or []
        department = data.get("department")
        if departments and isinstance(departments[0], dict):
            department = departments[0].get("department", {}).get("name", department)

        defaults = {
            "first_name": data.get("first_name") or data.get("firstname"),
            "second_name": data.get("second_name") or data.get("surname"),
            "birth_date": parse_birth_date(data.get("birth_date")),
            "gender": gender,
            "department": department,
            "role": self.account_role,
        }
        phone = data.get("phone")
        if phone:
            phone = str(phone).replace("+", "")
            if not User.objects.filter(phone_number=phone).exclude(**{identifier_field: identifier}).exists():
                defaults["phone_number"] = phone
        return identifier_field, identifier, defaults


class HemisAuthorizationView(HemisOAuthMixin, APIView):
    """Create an authorization URL with a signed, session-independent CSRF state."""

    def get(self, request):
        signer = TimestampSigner(salt=f"oauth_state_{self.account_role}")
        state = signer.sign(uuid4().hex)
        return Response(
            {"data": {"authorization_url": self.get_client().get_authorization_url(state=state)}}
        )


class HemisCallbackView(HemisOAuthMixin, APIView):
    """Exchange a HEMIS code, synchronize the user, and issue local JWTs."""

    # Сколько времени даём пользователю на прохождение логина на стороне HEMIS.
    STATE_MAX_AGE = 600  # секунд

    def get(self, request):
        code = request.query_params.get("code")
        received_state = request.query_params.get("state")
        if not code:
            return Response({"message": "Authorization code is missing."}, status=status.HTTP_400_BAD_REQUEST)

        signer = TimestampSigner(salt=f"oauth_state_{self.account_role}")
        if not received_state:
            return Response({"message": "Invalid OAuth state."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            signer.unsign(received_state, max_age=self.STATE_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return Response({"message": "Invalid OAuth state."}, status=status.HTTP_400_BAD_REQUEST)

        token_response = self.get_client().get_access_token(code)
        provider_token = token_response.get("access_token")
        if not provider_token:
            return Response(
                {"message": "Could not obtain the HEMIS access token.", "error": token_response.get("error")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        details = self.get_client().get_user_details(provider_token)
        identifier_field, identifier, defaults = self.get_profile(details)
        if not identifier:
            return Response(
                {"message": "HEMIS did not return a user identifier.", "error": details.get("error")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user, _ = User.objects.update_or_create(
                **{identifier_field: identifier}, defaults=defaults
            )
        except IntegrityError:
            return Response(
                {"message": "A user with this phone number already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Authorization completed.",
                "data": {
                    "backend_token": {"access": str(refresh.access_token), "refresh": str(refresh)},
                    "provider_access_token": provider_token,
                    "role": user.role,
                },
            }
        )


class TeacherAuthorizationView(HemisAuthorizationView):
    oauth_settings = TEACHER_OAUTH
    account_role = "teacher"


class TeacherCallbackView(HemisCallbackView):
    oauth_settings = TEACHER_OAUTH
    account_role = "teacher"


class StudentAuthorizationView(HemisAuthorizationView):
    oauth_settings = STUDENT_OAUTH
    account_role = "talaba"


class StudentCallbackView(HemisCallbackView):
    oauth_settings = STUDENT_OAUTH
    account_role = "talaba"
