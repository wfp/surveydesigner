import re

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from questions.models import (
    BaseQuestion,
    RepeatSection,
    RootQuestion,
    RootQuestionTranslation,
    SubQuestion,
)


# Create BaseQuestion on create
@receiver(post_save, sender=RootQuestion)
def create_or_update_root_question(sender, instance, created, **kwargs):
    if created:
        bq = BaseQuestion.objects.create(root_question=instance)
        bq.order = bq.id
        bq.save()
    else:
        # Touch sub-questions so their signals run
        for sub_question in instance.sub_questions.all():
            sub_question.save()


@receiver(post_save, sender=SubQuestion)
def create_or_update_sub_question(sender, instance, created, **kwargs):
    if created:
        bq = BaseQuestion.objects.create(sub_question=instance)
        bq.order = bq.id
        bq.save()


@receiver(post_save, sender=RepeatSection)
def create_or_update_repeat_section(sender, instance, created, **kwargs):
    if created:
        bq = BaseQuestion.objects.create(repeat_section=instance)
        bq.order = bq.id
        bq.save()


# Capture *string* old names in pre_save
@receiver(pre_save, sender=RootQuestion)
def store_root_question_old_name(sender, instance, **kwargs):
    if instance.pk:
        old = RootQuestion.objects.filter(pk=instance.pk).only("name").first()
        instance._pre_save_name = old.name if old else None
    else:
        instance._pre_save_name = None


@receiver(pre_save, sender=SubQuestion)
def store_sub_question_old_name(sender, instance, **kwargs):
    if instance.pk:
        old = SubQuestion.objects.filter(pk=instance.pk).only("name").first()
        instance._pre_save_name = old.name if old else None
    else:
        instance._pre_save_name = None


# Rename references after save
@receiver(post_save, sender=RootQuestion)
def update_root_question_references(sender, instance, created, **kwargs):
    _update_references_after_rename(instance, created)


@receiver(post_save, sender=SubQuestion)
def update_sub_question_references(sender, instance, created, **kwargs):
    _update_references_after_rename(instance, created)


def _compile_token_pattern(old_name: str) -> re.Pattern:
    """Match exactly the ${OldName} token (XLSForm style)."""
    return re.compile(r"\$\{" + re.escape(old_name) + r"\}")


def _bulk_replace_field(
    qs, field_name: str, pattern: re.Pattern, replacement: str
) -> int:
    """
    Replace token occurrences in a given text field across a queryset.
    Returns the number of rows updated.
    """
    to_update = []
    for obj in qs.iterator():
        value = getattr(obj, field_name) or ""
        new_value = pattern.sub(replacement, value)
        if new_value != value:
            setattr(obj, field_name, new_value)
            to_update.append(obj)

    if to_update:
        qs.model.objects.bulk_update(to_update, [field_name])
    return len(to_update)


def _model_has_field(model, fname: str) -> bool:
    return any(getattr(f, "name", None) == fname for f in model._meta.get_fields())


def _update_references_after_rename(instance, created: bool):
    """
    When a question's `name` changes, update any `${name}` references in:
      - relevant / constraint / choice_filter / calculation dependency fields
      - RootQuestion/SubQuestion `label`
      - RootQuestionTranslation `label`
    """
    if created:
        return

    old_name = getattr(instance, "_pre_save_name", None)
    new_name = instance.name
    if not old_name or old_name == new_name:
        return

    token_pat = _compile_token_pattern(old_name)
    replacement = "${" + new_name + "}"
    token = f"${{{old_name}}}"

    base_question = instance.base_question  # One-to-one via BaseQuestion

    # (qs, field) pairs for dependency updates on this BaseQuestion
    dep_fields = [
        (base_question.root_question_relevant_dependencies.all(), "relevant"),
        (base_question.sub_question_relevant_dependencies.all(), "relevant"),
        (base_question.repeat_section_relevant_dependencies.all(), "relevant"),
        (base_question.submodule_relevant_dependencies.all(), "relevant"),
        (base_question.root_question_constraint_dependencies.all(), "constraint"),
        (base_question.sub_question_constraint_dependencies.all(), "constraint"),
        (base_question.root_question_choice_filter_dependencies.all(), "choice_filter"),
        (base_question.sub_question_choice_filter_dependencies.all(), "choice_filter"),
        (base_question.root_question_calculation_dependencies.all(), "calculation"),
        (base_question.sub_question_calculation_dependencies.all(), "calculation"),
    ]

    # Label-like fields that may contain ${OldName}
    label_fields = []

    # RootQuestion.label search globally for any label referencing this token
    if _model_has_field(RootQuestion, "label"):
        label_fields.append(
            (RootQuestion.objects.filter(label__contains=token), "label")
        )

    # SubQuestion.label (if present in your model)
    if _model_has_field(SubQuestion, "label"):
        label_fields.append(
            (SubQuestion.objects.filter(label__contains=token), "label")
        )

    # RootQuestionTranslation: label (global search for token)
    if _model_has_field(RootQuestionTranslation, "label"):
        label_fields.append(
            (RootQuestionTranslation.objects.filter(label__contains=token), "label")
        )

    with transaction.atomic():
        for qs, field in dep_fields:
            _bulk_replace_field(qs.only(field), field, token_pat, replacement)

        for qs, field in label_fields:
            _bulk_replace_field(qs.only(field), field, token_pat, replacement)
