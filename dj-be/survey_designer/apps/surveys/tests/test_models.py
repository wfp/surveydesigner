import pytest
from surveys.models import SurveyMode


@pytest.mark.django_db
def test_visible_for_user_survey_mode(
    user, survey_mode_1, survey_mode_2, organization_1
):
    # Query the visible survey modes for the not global admin user
    user.organization = organization_1
    visible_modes = SurveyMode.objects.visible_for_user(user)
    # Check that both survey_mode_1 and survey_mode_2 are visible
    assert survey_mode_1 in visible_modes
    assert survey_mode_2 in visible_modes
    assert visible_modes.count() == 2
