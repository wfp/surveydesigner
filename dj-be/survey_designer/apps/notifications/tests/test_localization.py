from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.translation import override
from notifications.const import NotificationStatus, ReleaseStatus
from notifications.localization import localized_content, resolve_content_language
from notifications.models import (
    Notification,
    NotificationTranslation,
    Release,
    ReleaseTranslation,
)
from notifications.selectors import notifications_for_user, releases_for_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def notice():
    return Notification.objects.create(
        title="English title",
        abstract="English summary",
        body="<p>English body</p>",
        status=NotificationStatus.PUBLISHED,
        publish_at=timezone.now() - timedelta(minutes=1),
    )


@pytest.fixture
def french(notice):
    return NotificationTranslation.objects.create(
        notification=notice,
        language="fr",
        title="Titre francais",
        abstract="Resume francais",
        label="<p>Texte francais</p>",
    )


@pytest.mark.parametrize(
    "language", [code for code, _ in settings.LANGUAGES if code != "en"]
)
def test_supported_languages_return_one_translation(notice, language):
    NotificationTranslation.objects.create(
        notification=notice, language=language, title="Translated", label="<p>Body</p>"
    )
    content = localized_content(notice, language)
    assert content == {
        "language": language,
        "title": "Translated",
        "body": "<p>Body</p>",
        "abstract": "",
    }


def test_requested_language_only_is_returned_without_mutating_storage(notice, french):
    content = localized_content(notice, "fr")
    assert content == {
        "language": "fr",
        "title": french.title,
        "body": french.label,
        "abstract": french.abstract,
    }
    notice.refresh_from_db()
    assert notice.title == "English title"
    assert "translations" not in content


@pytest.mark.parametrize(
    "language", ("en", "en-gb", "en_US", "de", "unsupported", "ar")
)
def test_missing_or_unsupported_translation_falls_back_to_english(
    notice, french, language
):
    content = localized_content(notice, language)
    assert content["language"] == "en"
    assert content["title"] == notice.title
    assert content["abstract"] == notice.abstract
    assert content["body"] == notice.body


@pytest.mark.parametrize("language", ("FR", " fr ", "fr-CA", "fr_CA"))
def test_locale_variants_resolve_to_configured_language(notice, french, language):
    assert localized_content(notice, language)["language"] == "fr"


def test_active_request_language_is_used_when_no_explicit_language_is_supplied(
    notice, french
):
    with override("fr"):
        assert localized_content(notice)["language"] == "fr"
    with override("en"):
        assert localized_content(notice)["language"] == "en"


@pytest.mark.parametrize("field", ("title", "label"))
def test_incomplete_translation_falls_back_as_a_whole_message(notice, french, field):
    NotificationTranslation.objects.filter(pk=french.pk).update(**{field: "   "})
    content = localized_content(notice, "fr")
    assert content["language"] == "en"
    assert content["title"] == notice.title
    assert content["body"] == notice.body
    assert content["abstract"] == notice.abstract


def test_optional_blank_translated_abstract_is_not_replaced_with_english(
    notice, french
):
    french.abstract = ""
    french.save()
    assert localized_content(notice, "fr")["abstract"] == ""


def test_release_translation_uses_its_inherited_label_as_body():
    release = Release.objects.create(
        business_version="2.0.1", title="English", body="English notes"
    )
    ReleaseTranslation.objects.create(
        release=release, language="fr", title="Francais", label="Notes francaises"
    )
    assert localized_content(release, "fr") == {
        "language": "fr",
        "title": "Francais",
        "body": "Notes francaises",
    }
    assert "abstract" not in localized_content(release, "en")


def test_notification_list_localization_uses_constant_queries(
    user, django_assert_num_queries
):
    group = Group.objects.create(name="Readers")
    user.groups.add(group)
    for i in range(5):
        notice = Notification.objects.create(
            title=f"Notice {i}",
            body="English body",
            status=NotificationStatus.PUBLISHED,
        )
        notice.audience.add(group)
        NotificationTranslation.objects.create(
            notification=notice, language="fr", title="French", label="French body"
        )
    with django_assert_num_queries(2):
        content = [localized_content(row, "fr") for row in notifications_for_user(user)]
    assert len(content) == 5
    assert all(row["language"] == "fr" for row in content)


def test_release_list_localization_uses_constant_queries(
    user, django_assert_num_queries
):
    group = Group.objects.create(name="Readers")
    user.groups.add(group)
    for i in range(4):
        release = Release.objects.create(
            business_version=f"2.0.{i}",
            title="English",
            body="Notes",
            status=ReleaseStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        notice = Notification.objects.create(title="Announcement", release=release)
        notice.audience.add(group)
        ReleaseTranslation.objects.create(
            release=release, language="fr", title="French", label="French notes"
        )
    with django_assert_num_queries(2):
        content = [localized_content(row, "fr") for row in releases_for_user(user)]
    assert len(content) == 4


def test_language_resolution_does_not_read_the_database(django_assert_num_queries):
    with django_assert_num_queries(0):
        assert resolve_content_language("ZH_CN") == "zh-cn"
        assert resolve_content_language("fr-CA") == "fr"
        assert resolve_content_language("de") == "en"
