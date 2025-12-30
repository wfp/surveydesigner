from django.urls import path

from survey_designer.apps.organization.views import ListOrganizationsView

urlpatterns = [
    path("organizations/", ListOrganizationsView.as_view(), name="organizations_list"),
]
