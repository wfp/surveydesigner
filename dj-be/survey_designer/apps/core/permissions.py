from django.contrib.auth.models import Permission
from rest_framework import permissions
from rest_framework.permissions import DjangoModelPermissions


class AdminPermissions:
    default_actions = ("add", "change", "delete", "view")
    permission_map = {
        "modules": {
            "Indicator": default_actions,
            "IndicatorArea": default_actions,
            "Module": default_actions,
            "ModuleTranslation": default_actions,
            "Submodule": default_actions,
            "SubmoduleTranslation": default_actions,
            "SubmoduleMapping": default_actions,
            "SubmoduleMappingSurveyCategory": default_actions,
            "SubmoduleMappingSurveyType": default_actions,
            "SubmoduleMappingSurveyMode": default_actions,
            "SubmoduleMappingSurveyAttribute": default_actions,
        },
        "questions": {
            "BaseQuestion": default_actions,
            "Calculation": default_actions,
            "RootQuestion": default_actions,
            "RootQuestionTranslation": default_actions,
            "RecallPeriod": default_actions,
            "Suffix": default_actions,
            "SubQuestion": default_actions,
            "SubQuestionTranslation": default_actions,
            "ChoiceGroup": default_actions,
            "Choice": default_actions,
            "ChoiceTranslation": default_actions,
            "SubQuestionProxy": default_actions,
            "NestedSuffix": default_actions,
            "RootQuestionConstraintMessageTranslation": default_actions,
            "SubQuestionConstraintMessageTranslation": default_actions,
            "RepeatSection": default_actions,
        },
        "change_requests": {
            "ChangeRequest": default_actions,
        },
        "surveys": {
            "SurveyCategory": default_actions,
            "SurveyCategoryTranslation": default_actions,
            "SurveyType": default_actions,
            "SurveyTypeTranslation": default_actions,
            "SurveyMode": default_actions,
            "SurveyModeTranslation": default_actions,
            "SurveyAttribute": default_actions,
            "SurveyAttributeTranslation": default_actions,
        },
        "accounts": {
            "User": ("view",),
        },
    }

    def get_model_permissions(self, app_label, model_name, actions):
        permissions = []
        model_name = model_name.lower()

        for action in actions:
            code_name = f"{action}_{model_name}"

            permissions.append(
                Permission.objects.get_by_natural_key(
                    codename=code_name, app_label=app_label, model=model_name
                )
            )

        return permissions

    def get_permissions(self):
        permissions = []

        for app_label, model_action_list in self.permission_map.items():
            for model_name, actions in model_action_list.items():
                model_permissions = self.get_model_permissions(
                    app_label, model_name, actions
                )
                permissions.extend(model_permissions)

        return permissions

    def set_permissions(self, group):
        group.permissions.set([permission.id for permission in self.get_permissions()])


class ReadOnlyPermissions:
    default_actions = ("view",)
    permission_map = {
        "modules": {
            "Indicator": default_actions,
            "IndicatorArea": default_actions,
            "Module": default_actions,
            "ModuleTranslation": default_actions,
            "Submodule": default_actions,
            "SubmoduleTranslation": default_actions,
            "SubmoduleMapping": default_actions,
            "SubmoduleMappingSurveyCategory": default_actions,
            "SubmoduleMappingSurveyType": default_actions,
            "SubmoduleMappingSurveyMode": default_actions,
            "SubmoduleMappingSurveyAttribute": default_actions,
        },
        "questions": {
            "BaseQuestion": default_actions,
            "Calculation": default_actions,
            "RootQuestion": default_actions,
            "RootQuestionTranslation": default_actions,
            "RecallPeriod": default_actions,
            "Suffix": default_actions,
            "SubQuestion": default_actions,
            "SubQuestionTranslation": default_actions,
            "ChoiceGroup": default_actions,
            "Choice": default_actions,
            "ChoiceTranslation": default_actions,
            "SubQuestionProxy": default_actions,
            "NestedSuffix": default_actions,
            "RootQuestionConstraintMessageTranslation": default_actions,
            "SubQuestionConstraintMessageTranslation": default_actions,
            "RepeatSection": default_actions,
        },
        "change_requests": {
            "ChangeRequest": default_actions,
        },
        "surveys": {
            "SurveyCategory": default_actions,
            "SurveyCategoryTranslation": default_actions,
            "SurveyType": default_actions,
            "SurveyTypeTranslation": default_actions,
            "SurveyMode": default_actions,
            "SurveyModeTranslation": default_actions,
            "SurveyAttribute": default_actions,
            "SurveyAttributeTranslation": default_actions,
        },
    }

    def get_model_permissions(self, app_label, model_name, actions):
        permissions = []
        model_name = model_name.lower()

        for action in actions:
            code_name = f"{action}_{model_name}"

            permissions.append(
                Permission.objects.get_by_natural_key(
                    codename=code_name, app_label=app_label, model=model_name
                )
            )

        return permissions

    def get_permissions(self):
        permissions = []

        for app_label, model_action_list in self.permission_map.items():
            for model_name, actions in model_action_list.items():
                model_permissions = self.get_model_permissions(
                    app_label, model_name, actions
                )
                permissions.extend(model_permissions)

        return permissions

    def set_permissions(self, group):
        group.permissions.set([permission.id for permission in self.get_permissions()])


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_staff and request.user.groups.filter(name="Admins").exists()
        )


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners of an object to edit it."""

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the snippet.
        return obj.author == request.user


class SDModelPermissions(DjangoModelPermissions):
    """
    Extend the DjangoModelPermissions with the GET check
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }
