from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponseRedirect
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


class LogoutView(View):
    http_method_names = ["get"]

    def get(self, request):
        auth.logout(request)
        return_url = settings.FRONTEND_BASE_DOMAIN
        response = HttpResponseRedirect(return_url)
        response.delete_cookie("idtoken")
        return response
