from django.db import models


class SurveyOrganizationVisibilityQuerySetMixin(models.QuerySet):
    def visible_for_user(self, user):
        if user.is_global_admins_member or user.is_superuser:
            return self
        return self.filter(organizations=user.organization)

    def invisible_for_user(self, user):
        return self.exclude(id__in=self.visible_for_user(user))


class SurveyCategoryQuerySet(SurveyOrganizationVisibilityQuerySetMixin):
    pass


class SurveyModeQuerySet(SurveyOrganizationVisibilityQuerySetMixin):
    pass


class SurveyAttributeQuerySet(SurveyOrganizationVisibilityQuerySetMixin):
    pass


class SurveyTypeQuerySet(SurveyOrganizationVisibilityQuerySetMixin):
    pass
