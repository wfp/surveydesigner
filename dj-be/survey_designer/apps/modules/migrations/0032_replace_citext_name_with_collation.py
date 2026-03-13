# Generated for Django 5.2: replace CICharField name with collation-based field

import core.validators
from django.db import migrations, models

MODULES_TABLES = [
    ("modules_module", "module"),
    ("modules_submodule", "submodule"),
    ("modules_indicator", "indicator"),
    ("modules_indicatorarea", "indicatorarea"),
]

LIKE_INDEX_FILTER = " OR ".join(
    f"(tbl.relname = '{table_name}' AND attr.attname = 'name')"
    for table_name, _ in MODULES_TABLES
)


DROP_LIKE_INDEXES_SQL = f"""
DO $$
DECLARE index_record record;
BEGIN
    FOR index_record IN
        SELECT DISTINCT ns.nspname AS schema_name, idx.relname AS index_name
        FROM pg_class idx
        JOIN pg_index i ON idx.oid = i.indexrelid
        JOIN pg_class tbl ON tbl.oid = i.indrelid
        JOIN pg_namespace ns ON ns.oid = idx.relnamespace
        JOIN pg_attribute attr ON attr.attrelid = tbl.oid AND attr.attnum = ANY(i.indkey)
        WHERE idx.relkind = 'i'
          AND idx.relname LIKE '%\\_like' ESCAPE '\\'
          AND pg_get_indexdef(idx.oid) ~ '(varchar|text)_pattern_ops'
          AND ({LIKE_INDEX_FILTER})
    LOOP
        EXECUTE format('DROP INDEX IF EXISTS %I.%I', index_record.schema_name, index_record.index_name);
    END LOOP;
END $$;
"""

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

    operations = [
        migrations.RunSQL(
            sql=DROP_LIKE_INDEXES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ] + run_sql_operations + [
        migrations.SeparateDatabaseAndState(state_operations=state_operations),
    ]
