import pytest
from core.utils import get_model_admin_base_url
from django.contrib.admin import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from modules.admin import ModuleAdmin, SubmoduleAdmin
from modules.factories import ModuleFactory, SubmoduleFactory
from modules.models import Module, Submodule


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def module_admin(admin_site):
    return ModuleAdmin(Module, admin_site)


@pytest.fixture
def submodule_admin(admin_site):
    return SubmoduleAdmin(Submodule, admin_site)


class TestModuleAdmin:
    def test_module_admin_list_view(self, logged_admin_client):
        modules = ModuleFactory.create_batch(5)
        url = get_model_admin_base_url(Module, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        assert response.context["cl"].result_count == len(modules)

    def test_export_action(self, logged_admin_client, module_admin):
        ModuleFactory.create_batch(5)
        request = logged_admin_client.get(reverse("admin:modules_module_changelist"))
        response = module_admin.export_action(request, Module.objects.all())
        assert response.status_code == 200

    def test_add_submodule_mapping(self, request_factory, module_admin, global_admin):
        ModuleFactory.create_batch(5)
        request = request_factory.get(reverse("admin:modules_module_changelist"))
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        request.user = global_admin
        response = module_admin.add_submodule_mapping(request, Module.objects.all())
        assert response.status_code == 302
        assert (
            response.url
            == f"/admin/modules/submodulemapping/add/?module_ids={','.join(str(module.id) for module in Module.objects.all())}"
        )


class TestSubmoduleAdmin:
    def test_submodule_admin_list_view(self, logged_admin_client):
        submodules = SubmoduleFactory.create_batch(5)
        url = get_model_admin_base_url(Submodule, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        assert response.context["cl"].result_count == len(submodules)

    def test_export_action(self, logged_admin_client, submodule_admin):
        SubmoduleFactory.create_batch(5)
        request = logged_admin_client.get(reverse("admin:modules_submodule_changelist"))
        response = submodule_admin.export_action(request, Submodule.objects.all())
        assert response.status_code == 200

    def test_add_question_button(self, logged_admin_client, submodule_admin):
        submodule = SubmoduleFactory()
        logged_admin_client.get(reverse("admin:modules_submodule_changelist"))
        submodule.question_count = 12345
        response = submodule_admin.question_list_button(submodule)
        assert "12345" in response
