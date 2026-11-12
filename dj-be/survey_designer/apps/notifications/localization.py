from django.conf import settings
from django.utils.translation import get_language

from .models import Notification, Release


def resolve_content_language(language=None):
    language = str(language or get_language() or "en").strip().lower().replace("_", "-")
    supported = {code for code, _ in settings.LANGUAGES}
    if language in supported:
        return language
    primary = language.split("-", 1)[0]
    return primary if primary in supported else "en"


def localized_content(instance, language=None):
    """Return one language after authorization; body strings are not trusted HTML."""
    if not isinstance(instance, (Notification, Release)):
        raise TypeError(
            "Localized notification content requires a Notification or Release."
        )
    language = resolve_content_language(language)
    translation = None
    if language != "en":
        translation = next(
            (row for row in instance.translations.all() if row.language == language),
            None,
        )
        if translation and (
            not translation.title.strip() or not translation.label.strip()
        ):
            translation = None

    content = {
        "language": language if translation is not None else "en",
        "title": translation.title if translation is not None else instance.title,
        "body": translation.label if translation is not None else instance.body,
    }
    if isinstance(instance, Notification):
        content["abstract"] = (
            translation.abstract if translation is not None else instance.abstract
        )
    return content
