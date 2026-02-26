# Generated for Django 5.2: replace CICharField name with collation-based field

import core.validators
from django.db import migrations, models

SURVEYS_TABLES = [
    ("surveys_surveycategory", "surveycategory"),
    ("surveys_surveytype", "surveytype"),
    ("surveys_surveymode", "surveymode"),
    ("surveys_surveyattribute", "surveyattribute"),
]

run_sql_operations = []
for table_name, _ in SURVEYS_TABLES:
    run_sql_operations.append(
        migrations.RunSQL(
            sql=f'ALTER TABLE "{table_name}" ALTER COLUMN "name" TYPE varchar(255) COLLATE "case_insensitive" USING name::text;',
            reverse_sql=migrations.RunSQL.noop,
        )
    )

state_operations = [
    migrations.AlterField(
        model_name="surveycategory",
        name="name",
        field=models.CharField(
            db_collation="case_insensitive",
            max_length=255,
            unique=True,
            validators=[core.validators.validate_name],
            verbose_name="Name",
        ),
    ),
    migrations.AlterField(
        model_name="surveytype",
        name="name",
        field=models.CharField(
            db_collation="case_insensitive",
            max_length=255,
            unique=True,
            validators=[core.validators.validate_name],
            verbose_name="Name",
        ),
    ),
    migrations.AlterField(
        model_name="surveymode",
        name="name",
        field=models.CharField(
            db_collation="case_insensitive",
            max_length=255,
            unique=True,
            validators=[core.validators.validate_name],
            verbose_name="Name",
        ),
    ),
    migrations.AlterField(
        model_name="surveyattribute",
        name="name",
        field=models.CharField(
            db_collation="case_insensitive",
            max_length=255,
            unique=True,
            validators=[core.validators.validate_name],
            verbose_name="Name",
        ),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_replace_citext_with_collation"),
        ("surveys", "0020_surveymode_attributes"),
    ]

    operations = run_sql_operations + [
        migrations.SeparateDatabaseAndState(state_operations=state_operations),
    ]
