from django.urls import path

from . import views

app_name = "surveys"

urlpatterns = [
    path("surveys/", views.SurveysAPIView.as_view(), name="surveys"),
]
