import pytest
from core.utils import get_model_admin_base_url
from django.contrib.admin import AdminSite
from django.contrib.admin.widgets import (
    AutocompleteSelectMultiple,
    RelatedFieldWidgetWrapper,
)
from django.contrib.messages.storage.fallback import FallbackStorage
from django.templatetags.static import static
from django.urls import reverse
from modules.admin import IndicatorAdmin, ModuleAdmin, SubmoduleAdmin
from modules.factories import ModuleFactory, SubmoduleFactory
from modules.models import Indicator, IndicatorArea, Module, Submodule


def _assert_admin_search_works(logged_admin_client, model, expected_text):
    response = logged_admin_client.get(
        get_model_admin_base_url(model, "_changelist"),
        {"q": expected_text[:5].lower()},
    )
    assert response.status_code == 200
    assert expected_text in response.content.decode()


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def module_admin(admin_site):
    return ModuleAdmin(Module, admin_site)


@pytest.fixture
def submodule_admin(admin_site):
    return SubmoduleAdmin(Submodule, admin_site)


@pytest.fixture
def indicator_admin(admin_site):
    return IndicatorAdmin(Indicator, admin_site)


class TestModuleAdmin:
    def test_module_admin_list_view(self, logged_admin_client):
        modules = ModuleFactory.create_batch(5)
        url = get_model_admin_base_url(Module, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        assert response.context["cl"].result_count == len(modules)

    def test_module_admin_search_view(self, logged_admin_client, module_1):
        _assert_admin_search_works(logged_admin_client, Module, module_1.name)

    def test_module_change_page_includes_tribute_assets(
        self, logged_admin_client, module_1
    ):
        response = logged_admin_client.get(
            get_model_admin_base_url(Module, "_change", [module_1.id])
        )

        assert response.status_code == 200
        html = response.content.decode()
        assert static("js/tribute/tribute.js") in html
        assert static("admin/relevant_autocomplete.js") in html

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
            == "/admin/modules/submodulemapping/add/?module_ids="
            + ",".join(str(module.id) for module in Module.objects.all())
        )

    def test_save_model_sets_and_clears_relevant_dependencies(
        self,
        request_factory,
        module_admin,
        admin,
        module_1,
        root_question_1,
    ):
        request = request_factory.post(
            reverse("admin:modules_module_change", args=[module_1.id])
        )
        request.user = admin

        module_1.relevant = f"${{{root_question_1.name}}} > 0"
        module_admin.save_model(request, module_1, form=None, change=True)

        assert module_1.relevant_dependencies.filter(
            pk=root_question_1.base_question.id
        ).exists()

        module_1.relevant = ""
        module_admin.save_model(request, module_1, form=None, change=True)

        assert not module_1.relevant_dependencies.exists()


class TestSubmoduleAdmin:
    def test_submodule_admin_list_view(self, logged_admin_client):
        submodules = SubmoduleFactory.create_batch(5)
        url = get_model_admin_base_url(Submodule, "_changelist")
        response = logged_admin_client.get(url)
        assert response.status_code == 200
        assert response.context["cl"].result_count == len(submodules)

    def test_submodule_admin_search_view(self, logged_admin_client, submodule_1):
        _assert_admin_search_works(logged_admin_client, Submodule, submodule_1.name)

    def test_submodule_change_page_includes_tribute_assets(
        self, logged_admin_client, submodule_1
    ):
        response = logged_admin_client.get(
            get_model_admin_base_url(Submodule, "_change", [submodule_1.id])
        )

        assert response.status_code == 200
        html = response.content.decode()
        assert static("js/tribute/tribute.js") in html
        assert static("admin/relevant_autocomplete.js") in html

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


class TestIndicatorAreaAdmin:
    def test_indicator_area_admin_search_view(self, logged_admin_client):
        indicator_area = IndicatorArea.objects.create(
            name="IndicatorAreaSearch",
            label="Indicator Area Search",
        )
        _assert_admin_search_works(
            logged_admin_client, IndicatorArea, indicator_area.name
        )


class TestIndicatorAdmin:
    def test_indicator_admin_search_view(self, logged_admin_client, indicator_1):
        _assert_admin_search_works(logged_admin_client, Indicator, indicator_1.name)

    def test_indicator_questions_field_uses_autocomplete_widget(
        self, request_factory, indicator_admin, admin
    ):
        request = request_factory.get(reverse("admin:modules_indicator_add"))
        request.user = admin
        form = indicator_admin.get_form(request)()

        assert indicator_admin.autocomplete_fields == ("questions",)
        widget = form.fields["questions"].widget
        if isinstance(widget, RelatedFieldWidgetWrapper):
            widget = widget.widget
        assert isinstance(widget, AutocompleteSelectMultiple)
