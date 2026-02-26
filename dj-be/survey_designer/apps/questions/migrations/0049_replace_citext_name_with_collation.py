# Generated for Django 5.2: replace CICharField name with collation-based field

import core.validators
from django.db import migrations, models

QUESTIONS_TABLES = [
    "questions_rootquestion",
    "questions_subquestion",
    "questions_choicegroup",
    "questions_choicegroupfile",
    "questions_recallperiod",
    "questions_suffix",
    "questions_calculation",
    "questions_repeatsection",
]

run_sql_operations = [
    migrations.RunSQL(
        sql=f'ALTER TABLE "{table}" ALTER COLUMN "name" TYPE varchar(255) COLLATE "case_insensitive" USING name::text;',
        reverse_sql=migrations.RunSQL.noop,
    )
    for table in QUESTIONS_TABLES
]

def _name_field():
    return models.CharField(
        db_collation="case_insensitive",
        max_length=255,
        unique=True,
        validators=[core.validators.validate_name],
        verbose_name="Name",
    )

state_operations = [
    migrations.AlterField(
        model_name="rootquestion",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="subquestion",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="choicegroup",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="choicegroupfile",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="recallperiod",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="suffix",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="calculation",
        name="name",
        field=_name_field(),
    ),
    migrations.AlterField(
        model_name="repeatsection",
        name="name",
        field=_name_field(),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_replace_citext_with_collation"),
        ("questions", "0048_add_choice_group_file"),
    ]

    operations = run_sql_operations + [
        migrations.SeparateDatabaseAndState(state_operations=state_operations),
    ]
