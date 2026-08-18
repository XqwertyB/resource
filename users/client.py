from urllib.parse import urlencode

import requests


class OAuth2Client:
    def __init__(self, client_id, client_secret, redirect_uri, authorize_url, token_url, resource_owner_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.resource_owner_url = resource_owner_url

    def get_authorization_url(self, state=None):
        """Build a correctly encoded OAuth 2.0 authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        if state:
            params["state"] = state
        separator = "&" if "?" in self.authorize_url else "?"
        return f"{self.authorize_url}{separator}{urlencode(params)}"

    def get_access_token(self, auth_code):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        try:
            response = requests.post(self.token_url, data=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "So‘rov muddati tugadi (timeout)"}
        except (requests.RequestException, ValueError) as exc:
            return {"error": str(exc)}

    def get_user_details(self, access_token):
        try:
            response = requests.get(
                self.resource_owner_url,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            return {"error": "Foydalanuvchi ma’lumotlarini Hemisdan olishda timeout yuz berdi"}
        except (requests.RequestException, ValueError) as exc:
            return {"error": str(exc)}
