from change_requests.models import ChangeRequest
from django.db.models import Q, QuerySet
from modules.models import Indicator, Module, Submodule
from organization.models import Organization
from questions.models import (
    Calculation,
    ChoiceGroup,
    RepeatSection,
    RootQuestion,
    SubQuestion,
    Suffix,
)
from surveys.models import SurveyAttribute, SurveyCategory, SurveyMode, SurveyType


def get_organizations(obj) -> QuerySet:
    """
    In order to display organizations in cms change_form for given model,
    define proper condition for this model below,
    and add ChangeFormOrganizationsDisplayMixin to given model's admin.
    """
    if isinstance(
        obj,
        (
            Module,
            SurveyType,
            SurveyCategory,
            SurveyMode,
            SurveyAttribute,
            ChangeRequest,
        ),
    ):
        return obj.organizations.all()

    if isinstance(obj, Submodule):
        return obj.module.organizations.all()

    if isinstance(obj, Suffix):
        q1 = Q(module__submodules__root_questions__sub_questions__suffix=obj)
        q2 = Q(module__submodules__root_questions__sub_questions__suffix_2=obj)
        return Organization.objects.filter(q1 | q2).distinct()

    if isinstance(obj, ChoiceGroup):
        q1 = Q(module__submodules__root_questions__choices=obj)
        q2 = Q(module__submodules__root_questions__sub_questions__suffix__choices=obj)
        q3 = Q(module__submodules__root_questions__sub_questions__suffix_2__choices=obj)
        return Organization.objects.filter(q1 | q2 | q3).distinct()

    if isinstance(obj, Calculation):
        q = Q(module__submodules__root_questions__calculation=obj)
        return Organization.objects.filter(q).distinct()

    if isinstance(obj, RootQuestion):
        q = Q(module__submodules__root_questions=obj)
        return Organization.objects.filter(q).distinct()

    if isinstance(obj, RepeatSection):
        q = Q(module__submodules__repeat_sections=obj)
        return Organization.objects.filter(q).distinct()

    if isinstance(obj, Indicator):
        q1 = Q(module__submodules__root_questions__base_question__indicators=obj)
        q2 = Q(
            module__submodules__root_questions__sub_questions__base_question__indicators=obj
        )
        q3 = Q(surveytype__indicator_mappings__indicator=obj)
        return Organization.objects.filter(q1 | q2 | q3).distinct()

    if isinstance(obj, SubQuestion):
        if hasattr(obj, "root_question"):
            return get_organizations(obj.root_question)
        else:
            # If there is no root_question it means, object is being created
            return SubQuestion.objects.none()

    raise NotImplementedError(
        f"Missing get_organizations implementation for "
        f"`{obj.__class__.__name__}` in ModelOrganizationsMixin"
    )
