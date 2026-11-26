import re

from django.db import transaction
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver
from questions.models import (
    BaseQuestion,
    PulldataFile,
    RepeatSection,
    RootQuestion,
    RootQuestionTranslation,
    SubQuestion,
    SubQuestionProxy,
)


def _pulldata_file_is_referenced(file_id, using):
    return (
        RootQuestion.objects.using(using).filter(pulldata_files__pk=file_id).exists()
        or SubQuestion.objects.using(using).filter(pulldata_files__pk=file_id).exists()
    )


def _schedule_unreferenced_pulldata_files(file_ids, using):
    file_ids = {file_id for file_id in file_ids if file_id}
    if not file_ids:
        return

    def cleanup():
        for file_id in file_ids:
            # Serialize orphan cleanup against a concurrent M2M add.  On
            # PostgreSQL the row lock conflicts with the FK key-share lock
            # acquired by a through-table insert, so a committed attachment
            # is visible before this callback can delete the asset.
            with transaction.atomic(using=using):
                file_obj = (
                    PulldataFile.objects.using(using)
                    .select_for_update()
                    .filter(pk=file_id)
                    .first()
                )
                if file_obj is None or _pulldata_file_is_referenced(file_id, using):
                    continue
                file_obj.delete(using=using)

    transaction.on_commit(cleanup, using=using)


def _capture_question_pulldata_ids(instance, using):
    instance._pulldata_file_ids_before_delete = set(
        instance.pulldata_files.using(using).values_list("pk", flat=True)
    )


def _schedule_question_pulldata_cleanup(instance, using):
    _schedule_unreferenced_pulldata_files(
        getattr(instance, "_pulldata_file_ids_before_delete", ()), using
    )


@receiver(pre_delete, sender=RootQuestion)
def capture_root_question_pulldata_files(sender, instance, using, **kwargs):
    _capture_question_pulldata_ids(instance, using)


@receiver(post_delete, sender=RootQuestion)
def cleanup_root_question_pulldata_files(sender, instance, using, **kwargs):
    _schedule_question_pulldata_cleanup(instance, using)


@receiver(pre_delete, sender=SubQuestion)
def capture_sub_question_pulldata_files(sender, instance, using, **kwargs):
    _capture_question_pulldata_ids(instance, using)


@receiver(post_delete, sender=SubQuestion)
def cleanup_sub_question_pulldata_files(sender, instance, using, **kwargs):
    _schedule_question_pulldata_cleanup(instance, using)


@receiver(pre_delete, sender=SubQuestionProxy)
def capture_sub_question_proxy_pulldata_files(sender, instance, using, **kwargs):
    _capture_question_pulldata_ids(instance, using)


@receiver(post_delete, sender=SubQuestionProxy)
def cleanup_sub_question_proxy_pulldata_files(sender, instance, using, **kwargs):
    _schedule_question_pulldata_cleanup(instance, using)


@receiver(m2m_changed, sender=RootQuestion.pulldata_files.through)
@receiver(m2m_changed, sender=SubQuestion.pulldata_files.through)
def cleanup_detached_pulldata_files(
    sender, instance, action, reverse, model, pk_set, using, **kwargs
):
    if action == "pre_clear":
        if reverse:
            is_linked = (
                sender.objects.using(using)
                .filter(
                    pulldatafile_id=instance.pk,
                )
                .exists()
            )
            instance._pulldata_file_ids_before_clear = (
                {instance.pk} if is_linked else set()
            )
        else:
            instance._pulldata_file_ids_before_clear = set(
                instance.pulldata_files.using(using).values_list("pk", flat=True)
            )
        return
    if action == "pre_remove":
        requested_ids = set(pk_set or ())
        if reverse:
            owner_field = f"{model._meta.model_name}_id"
            is_linked = (
                sender.objects.using(using)
                .filter(
                    pulldatafile_id=instance.pk,
                    **{f"{owner_field}__in": requested_ids},
                )
                .exists()
            )
            instance._pulldata_file_ids_before_remove = (
                {instance.pk} if is_linked else set()
            )
        else:
            instance._pulldata_file_ids_before_remove = set(
                instance.pulldata_files.using(using)
                .filter(pk__in=requested_ids)
                .values_list("pk", flat=True)
            )
        return
    if action not in {"post_remove", "post_clear"}:
        return
    if action == "post_clear":
        file_ids = getattr(instance, "_pulldata_file_ids_before_clear", set())
    else:
        file_ids = getattr(instance, "_pulldata_file_ids_before_remove", set())
    _schedule_unreferenced_pulldata_files(file_ids, using)


@receiver(post_delete, sender=PulldataFile)
def cleanup_deleted_pulldata_file(sender, instance, using, **kwargs):
    storage_name = getattr(instance, "_pulldata_storage_name_before_delete", None)
    if not storage_name:
        storage_name = str(getattr(instance.file, "name", "") or "")
    PulldataFile.schedule_storage_delete(
        getattr(instance.file, "storage", None), storage_name, using
    )


@receiver(pre_delete, sender=PulldataFile)
def capture_deleted_pulldata_file(sender, instance, using, **kwargs):
    instance._pulldata_storage_name_before_delete = str(
        getattr(instance.file, "name", "") or ""
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


_OWN_EXPRESSION_FIELDS = (
    "relevant",
    "constraint",
    "required",
    "read_only",
    "default",
    "choice_filter",
    "calculation",
)


def _model_has_field(model, fname: str) -> bool:
    return any(getattr(f, "name", None) == fname for f in model._meta.get_fields())


def _update_references_after_rename(instance, created: bool):
    """
    When a question's `name` changes, update any `${name}` references in:
      - relevant / constraint / choice_filter / calculation / required /
        read_only / default dependency fields
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
        (base_question.module_relevant_dependencies.all(), "relevant"),
        (base_question.submodule_relevant_dependencies.all(), "relevant"),
        (base_question.root_question_constraint_dependencies.all(), "constraint"),
        (base_question.sub_question_constraint_dependencies.all(), "constraint"),
        (base_question.root_question_choice_filter_dependencies.all(), "choice_filter"),
        (base_question.sub_question_choice_filter_dependencies.all(), "choice_filter"),
        (base_question.root_question_calculation_dependencies.all(), "calculation"),
        (base_question.sub_question_calculation_dependencies.all(), "calculation"),
        (base_question.root_question_required_dependencies.all(), "required"),
        (base_question.sub_question_required_dependencies.all(), "required"),
        (base_question.root_question_read_only_dependencies.all(), "read_only"),
        (base_question.sub_question_read_only_dependencies.all(), "read_only"),
        (base_question.root_question_default_dependencies.all(), "default"),
        (base_question.sub_question_default_dependencies.all(), "default"),
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

        # The renamed question's own expressions refer to it by the old name
        # too. Update the instance as well, so callers that keep using it
        # (dependency sync, a later save) see the new name.
        own_changes = {}
        for field in _OWN_EXPRESSION_FIELDS:
            value = getattr(instance, field) or ""
            new_value = token_pat.sub(replacement, value)
            if new_value != value:
                own_changes[field] = new_value
                setattr(instance, field, new_value)
        if own_changes:
            type(instance).objects.filter(pk=instance.pk).update(**own_changes)
