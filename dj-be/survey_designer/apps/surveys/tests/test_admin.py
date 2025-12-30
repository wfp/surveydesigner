import pytest
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType

from survey_designer.apps.core.utils import get_model_admin_base_url


@pytest.mark.django_db
class TestSurveyCategoryAdmin:
    def test_survey_category_queryset(self, logged_admin_client, survey_category_1):
        url = get_model_admin_base_url(SurveyCategory, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_category in queryset:
            assert hasattr(survey_category, "organization_names")
            assert isinstance(survey_category.organization_names, list)
            assert len(survey_category.organization_names) > 0


@pytest.mark.django_db
class TestSurveyModeAdmin:
    def test_survey_mode_queryset(self, logged_admin_client, survey_mode_1):
        url = get_model_admin_base_url(SurveyMode, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_mode in queryset:
            assert hasattr(survey_mode, "organization_names")
            assert isinstance(survey_mode.organization_names, list)
            assert len(survey_mode.organization_names) > 0


@pytest.mark.django_db
class TestSurveyTypeAdmin:
    def test_survey_type_queryset(self, logged_admin_client, survey_type_1):
        url = get_model_admin_base_url(SurveyType, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_type in queryset:
            assert hasattr(survey_type, "organization_names")
            assert isinstance(survey_type.organization_names, list)
            assert len(survey_type.organization_names) > 0


@pytest.mark.django_db
class TestSurveyAttributeAdmin:
    def test_survey_attribute_queryset(self, logged_admin_client, survey_attribute_1):
        url = get_model_admin_base_url(SurveyAttribute, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        queryset = response.context_data["cl"].queryset
        # Assert that 'organization_names' is being annotated in the queryset
        for survey_attribute in queryset:
            assert hasattr(survey_attribute, "organization_names")
            assert isinstance(survey_attribute.organization_names, list)
            assert len(survey_attribute.organization_names) > 0
