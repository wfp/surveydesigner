# Generated for Django 5.2: replace CICharField name with collation-based field

import core.validators
from django.db import migrations, models

MODULES_TABLES = [
    ("modules_module", "module"),
    ("modules_submodule", "submodule"),
    ("modules_indicator", "indicator"),
    ("modules_indicatorarea", "indicatorarea"),
]

run_sql_operations = []
for table_name, _ in MODULES_TABLES:
    run_sql_operations.append(
        migrations.RunSQL(
            sql=f'ALTER TABLE "{table_name}" ALTER COLUMN "name" TYPE varchar(255) COLLATE "case_insensitive" USING name::text;',
            reverse_sql=migrations.RunSQL.noop,
        )
    )

state_operations = [
    migrations.AlterField(
        model_name="module",
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
        model_name="submodule",
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
        model_name="indicator",
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
        model_name="indicatorarea",
        name="name",
        field=models.CharField(
            db_collation="case_insensitive",
            max_length=255,
            unique=True,
            validators=[core.validators.validate_wfp_name],
            verbose_name="WFP Name",
        ),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_replace_citext_with_collation"),
        ("modules", "0031_indicatormappingsurveyattribute_and_more"),
    ]

    operations = run_sql_operations + [
        migrations.SeparateDatabaseAndState(state_operations=state_operations),
    ]
