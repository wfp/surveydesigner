"""Record required/read_only/default dependencies for existing questions.

0050 added these dependency tables empty, and only questions saved afterwards
fill them. Backfilling with the same parser lets renames propagate into
existing expressions. The other dependency tables are left untouched.
"""

from collections import defaultdict

from django.db import migrations
from questions.services.expression_validation import expression_dependency_names

FIELDS = ("required", "read_only", "default")


def backfill_expression_dependencies(apps, schema_editor):
    BaseQuestion = apps.get_model("questions", "BaseQuestion")
    RootQuestion = apps.get_model("questions", "RootQuestion")
    SubQuestion = apps.get_model("questions", "SubQuestion")

    # Names use a case-insensitive collation, so match them exactly here.
    ids_by_name = defaultdict(list)
    for id_, *names in BaseQuestion.objects.values_list(
        "id", "root_question__name", "sub_question__name", "repeat_section__name"
    ):
        name = next((name for name in names if name), None)
        if name:
            ids_by_name[name].append(id_)

    def backfill(question, question_type):
        for field_name in FIELDS:
            names = expression_dependency_names(
                getattr(question, field_name), field_name, question_type
            )
            if names:
                getattr(question, f"{field_name}_dependencies").set(
                    [id_ for name in names for id_ in ids_by_name.get(name, ())]
                )

    without_expressions = {field_name: "" for field_name in FIELDS}
    for root_question in RootQuestion.objects.exclude(**without_expressions):
        backfill(root_question, root_question.type)
    for sub_question in SubQuestion.objects.exclude(
        **without_expressions
    ).select_related("root_question", "suffix", "suffix_2"):
        # Historical models lack SubQuestion.type, so derive it the same way.
        suffix = sub_question.suffix_2 or sub_question.suffix
        backfill(
            sub_question, suffix.type if suffix else sub_question.root_question.type
        )


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0050_question_expression_dependencies"),
    ]

    operations = [
        migrations.RunPython(
            backfill_expression_dependencies, migrations.RunPython.noop
        ),
    ]
