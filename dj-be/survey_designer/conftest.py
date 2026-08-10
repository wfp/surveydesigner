import pytest
from accounts.const import PermissionGroups
from change_requests.models import ChangeRequest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files import File
from django.test import Client, RequestFactory
from modules.models import (
    Indicator,
    IndicatorArea,
    IndicatorMapping,
    IndicatorMappingSurveyMode,
    IndicatorMappingSurveyType,
    Module,
    Submodule,
    SubmoduleMapping,
    SubmoduleMappingSurveyAttribute,
    SubmoduleMappingSurveyMode,
    SubmoduleMappingSurveyType,
    SubmoduleTranslation,
)
from organization.models import Organization
from questions.const import QuestionType
from questions.models import (
    Calculation,
    Choice,
    ChoiceGroup,
    ChoiceTranslation,
    RecallPeriod,
    RepeatSection,
    RootQuestion,
    RootQuestionTranslation,
    SubQuestion,
    SubQuestionTranslation,
    Suffix,
)
from rest_framework.test import APIClient
from saved_surveys.models import SavedSurvey, SubModuleOrder, SubQuestionSubmodule
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType


def _create_choices(group_name, choice_names, choice_labels, choice_translations):
    c_group = ChoiceGroup.objects.create(
        name=group_name,
    )

    choices = []
    for name, label in zip(choice_names, choice_labels):
        choice = Choice.objects.create(
            choice_group=c_group,
            name=name,
            label=label,
        )
        choices.append(choice)

    for choice, translations in zip(choices, choice_translations):
        for lang, label in translations:
            ChoiceTranslation.objects.create(
                choice=choice,
                language=lang,
                label=label,
            )

    return c_group


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture()
def user(db):
    return get_user_model().objects.create_user(
        email="test@example.com", password="test_user"
    )


@pytest.fixture()
def admin(db):
    admin = get_user_model().objects.create_user(
        email="admin@example.com",
        password="admin_user",
        is_superuser=True,
        is_staff=True,
    )
    admin.organization = Organization.objects.create(name="Admin Organization")
    admin.save()
    return admin


@pytest.fixture()
def global_admin(db):
    user = get_user_model().objects.create_user(
        email="global_admin@example.com",
        password="admin_user",
        is_superuser=True,
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=PermissionGroups.GLOBAL_ADMINS)
    user.groups.add(group)
    group, _ = Group.objects.get_or_create(name=PermissionGroups.ADMINS)
    user.groups.add(group)
    return user


@pytest.fixture()
def api_client():
    client = APIClient()
    return client


@pytest.fixture()
def django_client():
    client = Client()
    return client


@pytest.fixture()
def logged_client(django_client, user):
    django_client.login(email="test@example.com", password="test_user")
    return django_client


@pytest.fixture()
def logged_admin_client(django_client, admin):
    django_client.login(email="admin@example.com", password="admin_user")
    return django_client


@pytest.fixture()
def logged_global_admin_client(django_client, global_admin):
    django_client.login(email="global_admin@example.com", password="admin_user")
    return django_client


@pytest.fixture()
def api_client_authenticated(api_client, user):
    api_client.force_authenticate(user)
    return api_client


@pytest.fixture()
def api_client_authenticated_admin(api_client, admin):
    api_client.force_authenticate(admin)
    return api_client


@pytest.fixture()
def organization_1():
    return Organization.objects.create(name="Organization 1")


@pytest.fixture()
def organization_2():
    return Organization.objects.create(name="Organization 2")


@pytest.fixture()
def module_1(organization_1):
    module = Module.objects.create(
        name="TestModule",
        label="Test Module",
    )
    module.organizations.add(organization_1)
    return module


@pytest.fixture()
def module_2(organization_1, organization_2):
    module = Module.objects.create(
        name="TestModule 2",
        label="Test Module 2",
    )
    module.organizations.add(organization_1)
    module.organizations.add(organization_2)
    return module


@pytest.fixture()
def survey_category_1():
    return SurveyCategory.objects.create(
        name="SurveyCategory1",
        label="Survey Category 1",
    )


@pytest.fixture()
def survey_category_2():
    return SurveyCategory.objects.create(
        name="SurveyCategory2",
        label="Survey Category 2",
    )


@pytest.fixture()
def survey_category_3():
    return SurveyCategory.objects.create(
        name="SurveyCategory3",
        label="Survey Category 3",
    )


@pytest.fixture()
def survey_type_1(survey_category_1):
    return SurveyType.objects.create(
        category=survey_category_1,
        name="SurveyType1",
        label="Survey Type 1",
    )


@pytest.fixture()
def survey_type_2(survey_category_1):
    return SurveyType.objects.create(
        category=survey_category_1,
        name="SurveyType2",
        label="Survey Type 2",
    )


@pytest.fixture()
def survey_mode_1(organization_1):
    survey_mode = SurveyMode.objects.create(
        name="SurveyMode1",
        label="Survey Mode 1",
    )
    survey_mode.organizations.add(organization_1)
    return survey_mode


@pytest.fixture()
def survey_mode_2(organization_1, organization_2):
    survey_mode = SurveyMode.objects.create(
        name="SurveyMode2",
        label="Survey Mode 2",
    )
    survey_mode.organizations.add(organization_1)
    survey_mode.organizations.add(organization_2)
    return survey_mode


@pytest.fixture()
def survey_attribute_1():
    return SurveyAttribute.objects.create(
        name="SurveyAttribute1",
        label="Survey Attribute 1",
    )


@pytest.fixture()
def survey_attribute_2():
    return SurveyAttribute.objects.create(
        name="SurveyAttribute2",
        label="Survey Attribute 2",
    )


@pytest.fixture()
def survey_attribute_3():
    return SurveyAttribute.objects.create(
        name="SurveyAttribute3",
        label="Survey Attribute 3",
    )


@pytest.fixture()
def submodule_mapping_1(survey_type_1, survey_mode_1, survey_attribute_1):
    mapping = SubmoduleMapping.objects.create()
    SubmoduleMappingSurveyType.objects.create(
        submodule_mapping=mapping, survey_type=survey_type_1, is_mandatory=True
    )
    SubmoduleMappingSurveyMode.objects.create(
        survey_mode=survey_mode_1, survey_type=None, is_mandatory=True
    )
    SubmoduleMappingSurveyAttribute.objects.create(
        submodule_mapping=mapping,
        survey_attribute=survey_attribute_1,
        is_mandatory=True,
    )
    return mapping


@pytest.fixture()
def submodule_mapping_2(survey_type_2, survey_mode_2, survey_attribute_2):
    mapping = SubmoduleMapping.objects.create()
    SubmoduleMappingSurveyType.objects.create(
        submodule_mapping=mapping, survey_type=survey_type_2, is_mandatory=False
    )
    SubmoduleMappingSurveyMode.objects.create(
        survey_mode=survey_mode_2, survey_type=None, is_mandatory=True
    )
    SubmoduleMappingSurveyAttribute.objects.create(
        submodule_mapping=mapping,
        survey_attribute=survey_attribute_2,
        is_mandatory=False,
    )
    return mapping


@pytest.fixture()
def submodule_mapping_3(survey_attribute_3):
    mapping = SubmoduleMapping.objects.create()
    SubmoduleMappingSurveyAttribute.objects.create(
        submodule_mapping=mapping,
        survey_attribute=survey_attribute_3,
        is_mandatory=False,
    )
    return mapping


@pytest.fixture()
def submodule_1(module_1, submodule_mapping_1):
    submodule = Submodule.objects.create(
        name="TestSubmodule",
        label="Test Submodule",
        module=module_1,
        appearance="test",
        mapping=submodule_mapping_1,
    )
    SubmoduleTranslation.objects.create(
        submodule=submodule,
        language="fr",
        label="Test PL label",
    )
    # Add root question
    question = RootQuestion.objects.create(
        name="TestQuestionSub1",
        label="Test Question 1",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule)
    return submodule


@pytest.fixture()
def submodule_2(module_2, submodule_mapping_2):
    submodule = Submodule.objects.create(
        name="TestSubmodule 2",
        label="Test Submodule 2",
        module=module_2,
        appearance="test",
        mapping=submodule_mapping_2,
    )
    SubmoduleTranslation.objects.create(
        submodule=submodule,
        language="fr",
        label="Test PL label",
    )
    # Add root question
    question = RootQuestion.objects.create(
        name="TestQuestionSub2",
        label="Test Question 2",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule)
    return submodule


@pytest.fixture()
def submodule_3(module_2, submodule_mapping_3):
    submodule = Submodule.objects.create(
        name="TestSubmodule 3",
        label="Test Submodule 3",
        module=module_2,
        appearance="test",
        mapping=submodule_mapping_3,
    )
    SubmoduleTranslation.objects.create(
        submodule=submodule,
        language="fr",
        label="Test PL label",
    )
    # Add root question
    question = RootQuestion.objects.create(
        name="TestQuestionSub3",
        label="Test Question 3",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule)
    return submodule


@pytest.fixture()
def root_question_1(submodule_1):
    question = RootQuestion.objects.create(
        name="TestQuestion1",
        label="Test Question 1",
        description="Test Question 1 - Description",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule_1)

    RootQuestionTranslation.objects.create(
        root_question=question, language="fr", label="Test Question 1 PL"
    )

    return question


@pytest.fixture()
def root_question_3(submodule_2, submodule_3):
    question = RootQuestion.objects.create(
        name="TestQuestion3",
        label="Test Question 3",
        description="Test Question 3 - Description",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule_2)
    question.submodule.add(submodule_3)

    RootQuestionTranslation.objects.create(
        root_question=question, language="fr", label="Test Question 3 PL"
    )
    return question


@pytest.fixture()
def root_question_4(submodule_2):
    question = RootQuestion.objects.create(
        name="TestQuestion4",
        label="Test Question 4",
        description="Test Question 4 - Description",
        type=QuestionType.INTEGER,
        appearance="test",
    )
    question.submodule.add(submodule_2)

    RootQuestionTranslation.objects.create(
        root_question=question, language="fr", label="Test Question 4 PL"
    )
    return question


@pytest.fixture()
def root_question_5(submodule_2):
    question = RootQuestion.objects.create(
        name="TestQuestion5",
        label="Test Question 5",
        description="Test Question 5 - Description",
        type=QuestionType.SELECT_ONE,
        appearance="test",
    )
    question.submodule.add(submodule_2)
    RootQuestionTranslation.objects.create(
        root_question=question, language="fr", label="Test Question 5 PL"
    )
    return question


@pytest.fixture()
def indicator_1(
    root_question_1,
    sub_question_1,
    root_question_2,
    sub_question_2,
    sub_question_3,
):
    indicator = Indicator.objects.create(name="TestIndicator", label="Test Indicator")

    indicator.questions.add(root_question_1.base_question)
    indicator.questions.add(root_question_2.base_question)
    indicator.questions.add(sub_question_1.base_question)
    indicator.questions.add(sub_question_2.base_question)
    indicator.questions.add(sub_question_3.base_question)

    return indicator


@pytest.fixture()
def indicator_mapping_survey_type(survey_type_1):
    mapping = IndicatorMapping.objects.create()
    mapping.survey_types.through.objects.create(
        indicator_mapping=mapping,
        survey_type=survey_type_1,
        is_mandatory=True,
    )
    return mapping


@pytest.fixture()
def indicator_mapping_survey_mode(survey_mode_1, survey_type_1):
    mapping = IndicatorMapping.objects.create()
    st_mapping = IndicatorMappingSurveyType.objects.create(
        indicator_mapping=mapping,
        survey_type=survey_type_1,
        is_mandatory=True,
    )
    IndicatorMappingSurveyMode.objects.create(
        survey_mode=survey_mode_1,
        survey_type=st_mapping,
        is_mandatory=True,
    )
    return mapping


@pytest.fixture()
def indicator_2(root_question_3, repeat_section_2):
    indicator = Indicator.objects.create(
        name="TestIndicator2", label="Test Indicator 2"
    )

    indicator.questions.add(root_question_3.base_question)
    indicator.questions.add(repeat_section_2.base_question)

    return indicator


@pytest.fixture()
def calculation_1(submodule_1, root_question_1):
    return Calculation.objects.create(
        name="Calculation1",
        label="Calculation 1",
        calculation=". + 10",
    )


@pytest.fixture()
def choices_1():
    choice_names = ["1", "2"]
    choice_labels = ["Choice 1", "Choice 2"]
    choice_translations = [
        [("fr", "Choice 1 PL")],
        [("fr", "Choice 2 PL"), ("es", "Choice 2 ES")],
    ]
    return _create_choices(
        "ChoiceGroup1", choice_names, choice_labels, choice_translations
    )


@pytest.fixture()
def choices_2():
    choice_names = ["3", "4"]
    choice_labels = ["Choice 3", "Choice 4"]
    choice_translations = [
        [("fr", "Choice 3 PL")],
        [("fr", "Choice 4 PL"), ("es", "Choice 4 ES")],
    ]
    return _create_choices(
        "ChoiceGroup2", choice_names, choice_labels, choice_translations
    )


@pytest.fixture()
def root_question_2(submodule_1, choices_1):
    question = RootQuestion.objects.create(
        name="TestQuestion2",
        label="Test Question 2",
        type=QuestionType.SELECT_MULTIPLE,
        choices=choices_1,
    )
    question.submodule.add(submodule_1)
    return question


@pytest.fixture()
def repeat_section_1(submodule_1, root_question_2):
    rs = RepeatSection.objects.create(
        name="RepeatSection1",
        label="Repeat Section 1",
        repeat_count="5",
    )
    rs.submodule.add(submodule_1)

    rs.questions.add(root_question_2.base_question)
    return rs


@pytest.fixture()
def repeat_section_2(submodule_2, root_question_4, root_question_3):
    rs = RepeatSection.objects.create(
        name="RepeatSection2",
        label="Repeat Section 2",
        repeat_count="5",
    )
    rs.submodule.add(submodule_2)

    rs.questions.add(root_question_4.base_question)
    rs.questions.add(root_question_3.base_question)
    return rs


@pytest.fixture()
def recall_period_1():
    return RecallPeriod.objects.create(
        name="RecallPeriod1", description="Recall Period 1 - Description"
    )


@pytest.fixture()
def suffix_1(choices_1):
    return Suffix.objects.create(
        name="Suffix1",
        description="Suffix 1 - Description",
        type=QuestionType.SELECT_ONE,
        choices=choices_1,
    )


@pytest.fixture()
def suffix_2():
    return Suffix.objects.create(
        name="Suffix2",
        description="Suffix 2 - Description",
        type=QuestionType.TEXT,
    )


@pytest.fixture()
def sub_question_1(root_question_1, suffix_1):
    q = SubQuestion.objects.create(
        root_question=root_question_1,
        name="SubQuestion1",
        suffix=suffix_1,
        label="SubQuestion 1",
    )

    SubQuestionTranslation.objects.create(
        sub_question=q,
        language="fr",
        label="SubQuestion 1 PL",
    )

    return q


@pytest.fixture()
def sub_question_2(root_question_1, recall_period_1):
    q = SubQuestion.objects.create(
        root_question=root_question_1,
        name="SubQuestion2",
        recall_period=recall_period_1,
        label="SubQuestion 2",
    )

    SubQuestionTranslation.objects.create(
        sub_question=q,
        language="fr",
        label="SubQuestion 2 PL",
    )

    return q


@pytest.fixture()
def sub_question_3(root_question_2, suffix_2):
    q = SubQuestion.objects.create(
        root_question=root_question_2,
        name="SubQuestion3",
        suffix=suffix_2,
        label="SubQuestion 3",
        disabled="Test",
    )

    SubQuestionTranslation.objects.create(
        sub_question=q,
        language="fr",
        label="SubQuestion 3 PL",
    )

    return q


@pytest.fixture()
def sub_question_4(root_question_1, suffix_1, suffix_2):
    q = SubQuestion.objects.create(
        root_question=root_question_1,
        name="SubQuestion4",
        suffix=suffix_1,
        suffix_2=suffix_2,
        label="SubQuestion 4",
        disabled="Test",
    )

    SubQuestionTranslation.objects.create(
        sub_question=q,
        language="fr",
        label="SubQuestion 4 PL",
    )

    return q


@pytest.fixture()
def xls_form_data(root_question_1, root_question_2, calculation_1, repeat_section_1):
    return [
        root_question_1,
        root_question_2,
        calculation_1,
        repeat_section_1,
        sub_question_1,
        sub_question_2,
        sub_question_3,
        sub_question_4,
    ]


@pytest.fixture()
def saved_survey_1(
    organization_1, admin, indicator_1, submodule_1, submodule_2, survey_type_1
):
    survey_type_1.category.organizations.add(organization_1)
    survey_type_1.organizations.add(organization_1)
    indicator_area = IndicatorArea.objects.create(
        name="SavedSurveyArea1",
        label="Saved Survey Area 1",
    )
    indicator_1.indicator_area = indicator_area
    indicator_1.save()

    saved_survey = SavedSurvey.objects.create(
        owner=admin,
        name="SavedSurvey1",
        survey_type=None,
        survey_mode=None,
        survey_category=None,
        modules_order=[submodule_2.module_id, submodule_1.module_id],
        indicator_areas_order=[indicator_area.id],
        indicators_order={str(indicator_area.id): [indicator_1.id]},
    )
    saved_survey.organizations.set([organization_1])
    saved_survey.indicators.set([indicator_1])
    saved_survey.submodules.set([submodule_1])
    saved_survey.survey_type = survey_type_1
    saved_survey.survey_category = survey_type_1.category
    saved_survey.save()

    SubModuleOrder.objects.create(
        saved_survey=saved_survey,
        submodule=submodule_2,
        order=0,
    )
    SubModuleOrder.objects.create(
        saved_survey=saved_survey,
        submodule=submodule_1,
        order=1,
    )
    return saved_survey


@pytest.fixture()
def subquestion_submodule(saved_survey_1, sub_question_1, submodule_1):
    return SubQuestionSubmodule.objects.create(
        saved_survey=saved_survey_1,
        subquestion=sub_question_1,
        submodule=submodule_1,
    )


@pytest.fixture()
def change_request_1(admin):
    cr = ChangeRequest(
        created_by=admin,
        description="Test",
    )
    cr.file.save(
        "test.xlsx",
        File(open("./survey_designer/apps/questions/tests/files/questions.xlsx", "rb")),
    )
    cr.organizations.add(admin.organization)
    return cr


@pytest.fixture
def request_factory():
    factory = RequestFactory()
    return factory


# Helper function to create submodules with mapping
def create_submodule_with_mapping(
    module,
    name,
    label,
    survey_types=None,
    survey_modes=None,
    survey_attributes=None,
    is_mandatory=True,
):
    mapping = SubmoduleMapping.objects.create()

    survey_type_mappings = []
    if survey_types:
        for survey_type in survey_types:
            st_mapping = SubmoduleMappingSurveyType.objects.create(
                submodule_mapping=mapping,
                survey_type=survey_type,
                is_mandatory=is_mandatory,
            )
            survey_type_mappings.append(st_mapping)
    else:
        st_mapping = None

    if survey_modes:
        for mode in survey_modes:
            if survey_type_mappings:
                for st_mapping in survey_type_mappings:
                    SubmoduleMappingSurveyMode.objects.create(
                        survey_mode=mode,
                        survey_type=st_mapping,
                        is_mandatory=is_mandatory,
                    )
            else:
                # If no survey_type, we can't link modes via survey_type
                SubmoduleMappingSurveyMode.objects.create(
                    survey_mode=mode,
                    survey_type=None,
                    is_mandatory=is_mandatory,
                )

    if survey_attributes:
        for attribute in survey_attributes:
            SubmoduleMappingSurveyAttribute.objects.create(
                submodule_mapping=mapping,
                survey_attribute=attribute,
                is_mandatory=is_mandatory,
            )

    submodule = Submodule.objects.create(
        name=name,
        label=label,
        module=module,
        mapping=mapping,
    )
    # Add root question
    question = RootQuestion.objects.create(
        name=f"RootQuestion_{name}",
        label=f"Root Question for {name}",
        type=QuestionType.INTEGER,
    )
    question.submodule.add(submodule)
    return submodule


# Submodule 4
@pytest.fixture()
def submodule_4(module_1, survey_mode_2, survey_attribute_2):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule4",
        label="Test Submodule 4",
        survey_types=None,
        survey_modes=[survey_mode_2],
        survey_attributes=[survey_attribute_2],
    )


# Submodule 5
@pytest.fixture()
def submodule_5(module_1, survey_attribute_2):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule5",
        label="Test Submodule 5",
        survey_types=None,
        survey_modes=None,
        survey_attributes=[survey_attribute_2],
    )


# Submodule 6
@pytest.fixture()
def submodule_6(module_1, survey_type_1):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule6",
        label="Test Submodule 6",
        survey_types=[survey_type_1],
        survey_modes=None,
        survey_attributes=None,
    )


# Submodule 7
@pytest.fixture()
def submodule_7(module_1, survey_type_2, survey_mode_1, survey_attribute_1):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule7",
        label="Test Submodule 7",
        survey_types=[survey_type_2],
        survey_modes=[survey_mode_1],
        survey_attributes=[survey_attribute_1],
    )


# Submodule 8
@pytest.fixture()
def submodule_8(module_1, survey_type_2, survey_mode_2, survey_attribute_1):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule8",
        label="Test Submodule 8",
        survey_types=[survey_type_2],
        survey_modes=[survey_mode_2],
        survey_attributes=[survey_attribute_1],
    )


# Submodule 9
@pytest.fixture()
def submodule_9(module_1, survey_type_2):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule9",
        label="Test Submodule 9",
        survey_types=[survey_type_2],
        survey_modes=None,
        survey_attributes=None,
    )


# Submodule 10
@pytest.fixture()
def submodule_10(module_1, survey_type_1, survey_mode_1):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule10",
        label="Test Submodule 10",
        survey_types=[survey_type_1],
        survey_modes=[survey_mode_1],
        survey_attributes=None,
    )


# Submodule 11
@pytest.fixture()
def submodule_11(module_1, survey_type_1, survey_mode_1, survey_mode_2):
    return create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule11",
        label="Test Submodule 11",
        survey_types=[survey_type_1],
        survey_modes=[survey_mode_1, survey_mode_2],
        survey_attributes=None,
    )


# Submodule 12
@pytest.fixture()
def submodule_12(
    module_1,
    survey_type_1,
    survey_type_2,
    survey_mode_1,
    survey_mode_2,
    survey_attribute_2,
):
    # Since Submodule has a one-to-one relationship with SubmoduleMapping, we'll simulate multiple mappings by creating separate submodules
    submodule12a = create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule12a",
        label="Test Submodule 12a",
        survey_types=[survey_type_1],
        survey_modes=[survey_mode_1, survey_mode_2],
        survey_attributes=[survey_attribute_2],
    )

    submodule12b = create_submodule_with_mapping(
        module=module_1,
        name="TestSubmodule12b",
        label="Test Submodule 12b",
        survey_types=[survey_type_2],
        survey_modes=None,
        survey_attributes=[survey_attribute_2],
    )

    return [submodule12a, submodule12b]


@pytest.fixture
def question_with_choices(db, root_question_5, submodule_2, module_2):
    # Minimal module/submodule so exporter will include the question
    cg = ChoiceGroup.objects.create(name="Yesnodkref")

    # We deliberately create names where lexicographic order != business order
    # and set 'order' to enforce the desired sequence.
    # Expected order: 1 Yes, 0 No, 777 PNA, 888 DK
    c1 = Choice.objects.create(
        choice_group=cg, name="1", label="Yes", order=1, is_active=True
    )
    c0 = Choice.objects.create(
        choice_group=cg, name="0", label="No", order=2, is_active=True
    )
    c777 = Choice.objects.create(
        choice_group=cg,
        name="777",
        label="Prefer not to answer",
        order=3,
        is_active=True,
    )
    c888 = Choice.objects.create(
        choice_group=cg, name="888", label="Don't Know", order=4, is_active=True
    )
    root_question_5.choices = cg
    root_question_5.save()

    return {
        "module": module_2,
        "submodule": submodule_2,
        "choice_group": cg,
        "choices": [c1, c0, c777, c888],
        "root_question": root_question_5,
        "base_question": root_question_5.base_question,
    }
