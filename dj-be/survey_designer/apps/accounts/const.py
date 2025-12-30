from django.db import models


class UserAPISiteAPITypes(models.TextChoices):
    ONA = "ONA", "Ona"
    KOBO = "KOBO", "Kobo"

    @classmethod
    def get_base_url(cls, site):
        return site.url

    @classmethod
    def get_projects_url(cls, site):
        if not site.is_ona:
            return ""
        base_url = cls.get_base_url(site)
        return f"{base_url}api/v1/projects"

    @classmethod
    def get_profiles_url(cls, site):
        if not site.is_ona:
            return ""
        base_url = cls.get_base_url(site)
        return f"{base_url}api/v1/profiles"

    @classmethod
    def get_orgs_url(cls, site, org=None):
        if not site.is_ona:
            return ""
        base_url = cls.get_base_url(site)
        if org:
            return f"{base_url}api/v1/orgs/{org}"
        return f"{base_url}api/v1/orgs"

    @classmethod
    def get_upload_url(cls, site, project_id):
        base_url = cls.get_base_url(site)
        mapping = {
            cls.ONA: f"api/v1/projects/{project_id}/forms",
            cls.KOBO: "api/v2/assets/",
        }
        return f"{base_url}{mapping.get(site.api_type)}"

    @classmethod
    def get_metadata_url(cls, site):
        if not getattr(site, "is_moda", False):
            return ""
        base_url = cls.get_base_url(site)
        return f"{base_url}api/v1/metadata"


class PermissionGroups(models.TextChoices):
    ADMINS = "Admins"
    GLOBAL_ADMINS = "Global Admins"
    BULK_UPLOAD = "Bulk Upload"
    CHANGE_REQUESTS = "Change Requests"
    NOTIFICATIONS = "Notifications"
    READ_ONLY = "Read Only"
