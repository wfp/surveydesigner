import json
from hmac import compare_digest
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View

from .utils import generate_codes


class OIDCAuthenticationRequestView(View):
    http_method_names = ["get"]

    def get(self, request):
        client_id = settings.OIDC_CLIENT_ID
        redirect_url = settings.OIDC_CALLBACK_URL
        authorization_url = settings.OIDC_AUTHORIZATION_ENDPOINT

        code_challenge, code_verifier = generate_codes()
        request.session["code_verifier"] = code_verifier

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_url,
            "scope": "openid",
            "response_type": "code",
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }

        query = urlencode(params)
        return HttpResponseRedirect(f"{authorization_url}?{query}")


class OIDCAuthenticationCallbackView(View):
    http_method_names = ["get"]

    def login_failure(self):
        return HttpResponseRedirect("/")

    def get(self, request):
        if request.GET.get("error"):
            if request.user.is_authenticated:
                auth.logout(request)
            assert not request.user.is_authenticated

        elif "code" in request.GET:
            if "code_verifier" not in request.session:
                return self.login_failure()

            code_verifier = request.session["code_verifier"]
            del request.session["code_verifier"]
            request.session.save()

            kwargs = {
                "request": request,
                "code_verifier": code_verifier,
            }

            print(f"ENV: {settings.ENV}")
            print(f"FRONTEND_BASE_DOMAIN: {settings.FRONTEND_BASE_DOMAIN}")
            self.user = auth.authenticate(**kwargs)

            if self.user and self.user.is_active:
                auth.login(self.request, self.user)
                return_url = settings.FRONTEND_BASE_DOMAIN
                response = HttpResponseRedirect(return_url)
                response.set_cookie(
                    "idtoken",
                    request.session.get("oidc_id_token"),
                    secure=True,
                    httponly=True,
                    samesite="strict",
                )
                return response

        return self.login_failure()


@method_decorator(csrf_exempt, name="dispatch")
class E2ELoginView(View):
    http_method_names = ["post"]

    def post(self, request):
        if not settings.ENABLE_E2E_AUTH:
            return JsonResponse({"detail": "E2E auth is disabled."}, status=404)

        token = request.headers.get("X-E2E-Auth-Token", "")
        if not compare_digest(token, settings.E2E_AUTH_TOKEN):
            return JsonResponse({"detail": "Invalid E2E auth token."}, status=403)

        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)

        email = (payload.get("email") or "").lower()
        allowed_emails = [value.lower() for value in settings.E2E_AUTH_EMAILS]
        if email not in allowed_emails:
            return JsonResponse(
                {"detail": "Email is not enabled for E2E auth."}, status=403
            )

        User = get_user_model()
        user, _created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "is_staff": email in ("admin@wfp.org", "me@me"),
                "is_superuser": email in ("admin@wfp.org", "me@me"),
            },
        )
        if not user.is_active:
            return JsonResponse({"detail": "User is inactive."}, status=403)

        auth.login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        get_token(request)
        return JsonResponse({"email": user.email})


class LogoutView(View):
    http_method_names = ["get"]

    def get(self, request):
        auth.logout(request)
        return_url = settings.FRONTEND_BASE_DOMAIN
        response = HttpResponseRedirect(return_url)
        response.delete_cookie("idtoken")
        return response
