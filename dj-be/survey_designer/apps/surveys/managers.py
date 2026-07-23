from django.db import models


class SurveyQuerySet(models.QuerySet):
    pass


class SurveyCategoryQuerySet(SurveyQuerySet):
    pass


class SurveyModeQuerySet(SurveyQuerySet):
    pass


class SurveyAttributeQuerySet(SurveyQuerySet):
    pass


class SurveyTypeQuerySet(SurveyQuerySet):
    pass
