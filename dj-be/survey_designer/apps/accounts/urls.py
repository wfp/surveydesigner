from django.urls import path
from rest_framework import routers

from . import views

app_name = "users"

urlpatterns = [
    path("api-token-auth/", views.AuthToken.as_view(), name="user_auth_token"),
    path("user/", views.UserDetailAPIView.as_view(), name="user_detail"),
    path("projects/", views.UserProjectListAPIView.as_view(), name="user_projects"),
    path("api-sites/", views.UserAPISiteView.as_view(), name="user_api_sites"),
]

router = routers.SimpleRouter()
router.register(r"api-keys", views.UserAPIKeyViewSet)

urlpatterns.extend(router.urls)
