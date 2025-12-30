import base64

import django_rq
import requests
from accounts.models import User
from authlib.jose import JsonWebKey, jwt
from core.send_email import EmailHelper
from core.tasks import send_email
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group


class OIDCAuthenticationBackend(ModelBackend):
    @property
    def claims_options(self):
        return {
            "iss": {
                "values": [settings.OIDC_TOKEN_ENDPOINT],
                "essential": True,
            },
            "aud": {
                "values": [settings.OIDC_CLIENT_ID],
                "essential": True,
            },
        }

    def get_token(self, payload):
        # Encode the client ID and secret as base64
        auth_str = f"{settings.OIDC_CLIENT_ID}:{settings.OIDC_CLIENT_SECRET}"
        encoded_auth_str = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        response = requests.post(
            url=settings.OIDC_TOKEN_ENDPOINT,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_auth_str}",
            },
        )
        response.raise_for_status()
        return response.json()

    def get_jwks_data(self):
        response = requests.get(url=settings.OIDC_JWKS_ENDPOINT)
        response.raise_for_status()
        return JsonWebKey.import_key_set(response.json())

    def decode_jwt(self, id_token):
        return jwt.decode(
            id_token, key=self.get_jwks_data(), claims_options=self.claims_options
        )

    def verify_token(self, id_token):
        return self.decode_jwt(id_token)

    def get_userinfo(self, access_token, id_token, payload):
        try:
            response = requests.get(
                settings.OIDC_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # If userinfo fails, extract user info from ID token
                # The ID token contains basic user information
                return {
                    "sub": payload.get("sub"),
                    "email": payload.get("email"),
                    "given_name": payload.get("given_name"),
                    "family_name": payload.get("family_name"),
                    "preferred_username": payload.get("preferred_username"),
                }
            else:
                raise

    def get_display_name(self, user_info):
        given_name = user_info.get("given_name")
        family_name = user_info.get("family_name")
        return f"{given_name} {family_name}"

    @staticmethod
    def create_user(email):
        user = User.objects.create_user(email=email)

        group = Group.objects.filter(name="Read Only").first()
        if group:
            user.groups.add(group)
        user.save()

        to_list = User.objects.filter(groups__name="Notifications").values_list(
            "email", flat=True
        )
        if to_list:
            # get the queue to send emails
            email_queue = django_rq.get_queue("send-email")
            mail = EmailHelper(
                "email/new_user_notification.html",
                {"user": user},
                subject="New user registered.",
                to_list=to_list,
            )
            email_queue.enqueue(send_email, email_helper=mail)

        return user

    def get_or_create_user(self, user_info):
        email = user_info.get("email")

        if email:
            user = User.objects.filter(email__iexact=email).first()
            if user:
                return user

            return self.create_user(email)
        return

    def authenticate(self, request, **kwargs):
        self.request = request
        if not self.request:
            return

        state = self.request.GET.get("session_state")
        code = self.request.GET.get("code")
        code_verifier = kwargs.pop("code_verifier", None)

        if not code or not state:
            return

        reverse_url = settings.OIDC_CALLBACK_URL

        token_payload = {
            "client_id": settings.OIDC_CLIENT_ID,
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": reverse_url,
        }

        token_info = self.get_token(token_payload)
        id_token = token_info.get("id_token")
        access_token = token_info.get("access_token")

        payload = self.verify_token(id_token)
        if payload:
            user_info = self.get_userinfo(access_token, id_token, payload)

            request.session["oidc_access_token"] = access_token
            request.session["oidc_id_token"] = id_token
            request.session["user_info"] = user_info
            request.session["display_name"] = self.get_display_name(user_info)

            user = self.get_or_create_user(user_info)
            return user
        return


class OIDCAuthenticationBackendCIAM(OIDCAuthenticationBackend):
    def get_token(self, payload):
        response = requests.post(
            url=settings.OIDC_TOKEN_ENDPOINT,
            data=payload,
        )
        response.raise_for_status()
        return response.json()
