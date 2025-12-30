import sys
from os import environ
from pathlib import Path

import sentry_sdk
from corsheaders.defaults import default_headers
from django.contrib import admin
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

load_dotenv()  # take environment variables from .env.

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "survey_designer" / "apps"
sys.path.insert(0, str(APPS_DIR))

# Environment name
ENV = environ.get("ENV", "local")

# Base domain
BASE_DOMAIN = environ.get("BASE_DOMAIN", "localhost")

FRONTEND_BASE_DOMAIN = environ.get("FRONTEND_BASE_DOMAIN", "http://localhost:3000")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = environ["ALLOWED_HOSTS"].split(";")

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "drf_spectacular",
    "rest_framework",
    "rest_framework.authtoken",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "corsheaders",
    "nested_admin",
    "admin_auto_filters",
    "dynamic_raw_id",
    "adminsortable2",
    "django_rq",
    "django_filters",
    "pwa",
    "martor",
    "dal",
    "dal_select2",
    "django_minify_html",
    # "silk",
]
if DEBUG:
    THIRD_PARTY_APPS += [
        "django_extensions",
    ]

LOCAL_APPS = [
    "survey_designer.apps.accounts",
    "survey_designer.apps.change_requests",
    "survey_designer.apps.core",
    "survey_designer.apps.documents",
    "survey_designer.apps.modules",
    "survey_designer.apps.questions",
    "survey_designer.apps.saved_surveys",
    "survey_designer.apps.surveys",
    "survey_designer.apps.organization",
    "survey_designer.apps.frontend_content",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django_minify_html.middleware.MinifyHtmlMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "silk.middleware.SilkyMiddleware",
    "core.middleware.OrganizationMiddleware",
]

CSRF_TRUSTED_ORIGINS = [
    FRONTEND_BASE_DOMAIN,
]


ROOT_URLCONF = "survey_designer.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "survey_designer" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.debug",
            ],
        },
    },
]

WSGI_APPLICATION = "survey_designer.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": environ["POSTGRES_DB"],
        "USER": environ["POSTGRES_USER"],
        "PASSWORD": environ["POSTGRES_PASSWORD"],
        "HOST": environ["POSTGRES_HOST"],
        "PORT": environ["POSTGRES_PORT"],
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=15000ms",
        },
    },
}

# CACHE
REDIS_URL = environ.get("REDIS_URL", None)
if REDIS_URL:  # pragma: no cover
    # Set Cache to redis
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "SOCKET_TIMEOUT": 500,
                "SOCKET_CONNECT_TIMEOUT": 500,
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "COMPRESSOR_CLASS": "django_redis.compressors.lzma.LzmaCompressor",
            },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("fr", _("French")),
    ("es", _("Spanish")),
    ("ar", _("Arabic")),
    ("zh-cn", _("Chinese")),
    ("ru", _("Russian")),
    ("pt", _("Portuguese")),
]


LOCALE_PATHS = (BASE_DIR.joinpath("locale"),)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR.joinpath("static")

# Whitenoise
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR.joinpath("uploads")

# Allow larger POSTs from Django Admin forms (default is 1000).
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# Upload to S3
UPLOAD_TO_S3 = environ.get("UPLOAD_TO_S3", "False").lower() == "true"
if UPLOAD_TO_S3:  # pragma: no cover
    AWS_ACCESS_KEY_ID = environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_ACL = None
    AWS_S3_REGION_NAME = environ.get("AWS_S3_REGION_NAME", "eu-west-1")
    AWS_STORAGE_BUCKET_NAME = environ.get("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = environ.get("AWS_S3_ENDPOINT_URL", None)
    AWS_S3_CUSTOM_DOMAIN = environ.get("AWS_S3_CUSTOM_DOMAIN", None)
    AWS_S3_URL_PROTOCOL = environ.get("AWS_S3_URL_PROTOCOL", "https:")
    # Enable url signature v4
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

    # proxy to minio
    if AWS_S3_ENDPOINT_URL and "localhost" in AWS_S3_ENDPOINT_URL:
        AWS_S3_PROXIES = {
            "http": "http://minio:9000",
        }

    # Static files
    # STATIC_LOCATION = "static"
    # STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{STATIC_LOCATION}/"
    # STATICFILES_STORAGE = "core.storage_backends.StaticStorage"
    # Media files
    PUBLIC_MEDIA_LOCATION = "media"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{PUBLIC_MEDIA_LOCATION}/"
    DEFAULT_FILE_STORAGE = "core.storage_backends.PublicMediaStorage"


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

# Check the Identity provider, if CIAM then use CIAM authentication backend
# Default: Use Keycloak backend
authentication_backend = (
    "core.auth.backends.OIDCAuthenticationBackendCIAM"
    if (environ.get("IDENTITY_PROVIDER", "") == "CIAM")
    else "core.auth.backends.OIDCAuthenticationBackend"
)

AUTHENTICATION_BACKENDS = [
    authentication_backend,
    "django.contrib.auth.backends.ModelBackend",
]


# DRF
REST_FRAMEWORK = {
    "NON_FIELD_ERRORS_KEY": "error",
    # "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PERMISSION_CLASSES": ("core.permissions.SDModelPermissions",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        # "oidc_auth.authentication.BearerTokenAuthentication",
    ),
    # "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    # "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# DRF-Spectacular
from survey_designer import ___version___ as build_id  # noqa

SPECTACULAR_SETTINGS = {
    "TITLE": "WFP Survey Designer API SPEC",
    "DESCRIPTION": """ This tool is targeted for users that are
    using XLSForm or ODK-based tools (such as: MoDa or Kobo).
    """,
    "TOS": "https://cdn.wfp.org/legal/terms/",
    "CONTACT": {"name": "Davis NDEGWAH", "email": "davis.ndegwah@wfp.org"},
    "LICENSE": {},
    "VERSION": f"{build_id}",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "DISABLE_ERRORS_AND_WARNINGS": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "AUTHENTICATION_WHITELIST": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
}


# CIAM OIDC auth settings for api
OIDC_AUTH = {
    "OIDC_ENDPOINT": environ.get("OIDC_ENDPOINT", ""),
    "OIDC_RESOLVE_USER_FUNCTION": "survey_designer.apps.accounts.authentication.get_user_by_id",
    "BEARER_AUTH_HEADER_PREFIX": "Bearer",
    "OIDC_BEARER_TOKEN_EXPIRATION_TIME": 60,
    "OIDC_JWKS_EXPIRATION_TIME": 24 * 60 * 60,
    # The Django cache to use
    "OIDC_CACHE_NAME": "default",
    "OIDC_CACHE_PREFIX": "oidc_auth.",
}

OIDC_CLIENT_ID = environ.get("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = environ.get("OIDC_CLIENT_SECRET")
OIDC_CALLBACK_URL = environ.get("OIDC_CALLBACK_URL", "")
OIDC_AUTHORIZATION_ENDPOINT = environ.get("OIDC_AUTHORIZATION_ENDPOINT", "")
OIDC_TOKEN_ENDPOINT = environ.get("OIDC_TOKEN_ENDPOINT", "")
OIDC_JWKS_ENDPOINT = environ.get("OIDC_JWKS_ENDPOINT", "")
OIDC_CONFIGURATION_ENDPOINT = environ.get("OIDC_CONFIGURATION_ENDPOINT", "")
OIDC_USERINFO_ENDPOINT = environ.get("OIDC_USERINFO_ENDPOINT", "")

IDENTITY_PROVIDER = environ.get("IDENTITY_PROVIDER", False)

# RQ queues definition
RQ_QUEUES = {
    "send-email": {"URL": REDIS_URL, "DEFAULT_TIMEOUT": 500},
    "generate-doc": {"URL": REDIS_URL, "DEFAULT_TIMEOUT": 500},
    "generic": {"URL": REDIS_URL, "DEFAULT_TIMEOUT": 500},
}

# CORS headers
CORS_ALLOWED_ORIGINS = environ.get("CORS_ALLOWED_ORIGINS", "").split(";")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-csrftoken",
    "content-type",
    "survey-designer-organizations",
]

# Sentry
SEND_TO_SENTRY = environ.get("SEND_TO_SENTRY", "False").lower() == "true"
try:
    SENTRY_SAMPLE_RATE = float(environ.get("SENTRY_SAMPLE_RATE", "0.001"))
except ValueError:  # pragma: no cover
    SENTRY_SAMPLE_RATE = 0.001
if SEND_TO_SENTRY:  # pragma: no cover
    sentry_sdk.init(
        dsn=environ["SENTRY_DSN"],
        integrations=[DjangoIntegration(), RedisIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production,
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        environment=ENV,
    )

# Read forwarded proto when present to build correct redirect
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Max size of an uploaded image (NOTE: not bytes, but width or height)
UPLOADED_PHOTO_MAX_SIZE = int(environ.get("UPLOADED_PHOTO_MAX_SIZE", "1024"))

# Silk profiler
# SILKY_PYTHON_PROFILER = True
# SILKY_PYTHON_PROFILER_BINARY = True
# SILKY_STORAGE_CLASS = DEFAULT_FILE_STORAGE
# SILKY_PYTHON_PROFILER_RESULT_PATH = "/profiling/"  # TODO: does not work
# SILKY_AUTHENTICATION = True  # User must login
# SILKY_AUTHORISATION = True  # User must have permissions


# def silky_permissions(user):
#     return user.is_superuser


# SILKY_PERMISSIONS = silky_permissions  # User must be a superuser
# SILKY_META = True
# SILKY_ANALYZE_QUERIES = True

# SILKY_DYNAMIC_PROFILING = [
#     {
#         "module": "modules.views",
#         "function": "ModuleViewSet.list",
#         "name": "Modules List",
#     },
#     {
#         "module": "modules.views",
#         "function": "ModuleViewSet.retrieve",
#         "name": "Modules Retrieve",
#     },
#     {
#         "module": "modules.views",
#         "function": "SubmoduleViewSet.list",
#         "name": "Submodules List",
#     },
#     {
#         "module": "modules.views",
#         "function": "SubmoduleViewSet.retrieve",
#         "name": "Submodules Retrieve",
#     },
#     {
#         "module": "modules.views",
#         "function": "IndicatorViewSet.list",
#         "name": "Indicators List",
#     },
#     {
#         "module": "modules.views",
#         "function": "IndicatorViewSet.retrieve",
#         "name": "Indicators Retrieve",
#     },
# ]


# Email settings
DEFAULT_FROM_EMAIL = "Survey Designer <global.surveydesigner@wfp.org>"
SERVER_EMAIL = "SysAdmin Survey Designer <global.surveydesigner@wfp.org>"

if ENV == "prod":
    EMAIL_SUBJECT_PREFIX = "Survey Designer |"
else:
    EMAIL_SUBJECT_PREFIX = f"[{ENV.upper()}] Survey Designer |"

EMAIL_BACKEND = environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)

if environ.get("EMAIL_HOST_USER", None):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = environ["EMAIL_HOST"]
    EMAIL_HOST_USER = environ["EMAIL_HOST_USER"]  # noqa F405
    EMAIL_HOST_PASSWORD = environ["EMAIL_HOST_PASSWORD"]  # noqa F405
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True


# API Gateway settings
API_GATEWAY_URL = environ.get("API_GATEWAY_URL", "https://api.wfp.org")

# Enketo settings
ENKETO_PREVIEW_URL = "https://enketo.moda.wfp.org/preview/?form="

# INITIAL_WFP_ORGANIZATION
INITIAL_ORGANIZATION = "WFP"

# Admin settings
ADMIN_ORDERING = {
    "change_requests": {
        "ChangeRequest": 1,
    },
    "surveys": {
        "SurveyCategory": 1,
        "SurveyType": 2,
        "SurveyMode": 3,
        "SurveyAttribute": 4,
    },
    "modules": {
        "Module": 1,
        "Submodule": 2,
        "Indicator": 3,
    },
    "questions": {
        "BaseQuestion": 2,
        "RootQuestion": 3,
        "ChoiceGroup": 4,
        "Suffix": 5,
        "RecallPeriod": 6,
        "Calculation": 7,
        "RepeatSection": 8,
    },
}

ADMIN_APPS_ORDERING = {
    "survey_designer.apps.accounts": 1,
    "admin": 2,
    "auth": 3,
    "survey_designer.apps.change_requests": 4,
    "survey_designer.apps.surveys": 5,
    "survey_designer.apps.modules": 6,
    "survey_designer.apps.questions": 7,
}


def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)

    # Sort the apps using the custom ordering or default alphabetical order.
    app_list = sorted(
        app_dict.values(), key=lambda x: ADMIN_APPS_ORDERING.get(x["app_label"], 999)
    )

    # Sort the models within each app based on custom ordering or alphabetically.
    for app in app_list:
        custom_ordering = ADMIN_ORDERING.get(app["app_label"])

        if custom_ordering:
            app["models"].sort(key=lambda x: custom_ordering.get(x["object_name"], 999))
        else:
            app["models"].sort(key=lambda x: x["name"])

    return app_list


def app_index(self, request, app_label, extra_context=None):
    app_list = self.get_app_list(request, app_label)

    if not app_list:
        raise Http404("The requested admin page does not exist.")

    context = {
        **self.each_context(request),
        "title": _("%(app)s administration") % {"app": app_list[0]["name"]},
        "subtitle": None,
        "app_list": app_list,
        "app_label": app_label,
        **(extra_context or {}),
    }

    request.current_app = self.name

    return TemplateResponse(
        request,
        self.app_index_template
        or ["admin/%s/app_index.html" % app_label, "admin/app_index.html"],
        context,
    )


admin.AdminSite.get_app_list = get_app_list
admin.AdminSite.app_index = app_index
