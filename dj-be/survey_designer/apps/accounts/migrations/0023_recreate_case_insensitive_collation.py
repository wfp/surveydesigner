# Generated for Django 5.2: recreate the case_insensitive collation as non-deterministic

from django.db import migrations


CASE_INSENSITIVE_COLUMNS = [
    ("accounts_user", "email"),
    ("accounts_userapikey", "name"),
    ("modules_module", "name"),
    ("modules_submodule", "name"),
    ("modules_indicator", "name"),
    ("modules_indicatorarea", "name"),
    ("questions_rootquestion", "name"),
    ("questions_subquestion", "name"),
    ("questions_choicegroup", "name"),
    ("questions_choicegroupfile", "name"),
    ("questions_recallperiod", "name"),
    ("questions_suffix", "name"),
    ("questions_calculation", "name"),
    ("questions_repeatsection", "name"),
    ("surveys_surveycategory", "name"),
    ("surveys_surveytype", "name"),
    ("surveys_surveymode", "name"),
    ("surveys_surveyattribute", "name"),
]


LIKE_INDEX_COLUMNS = [
    ("accounts_user", "email"),
    ("modules_module", "name"),
    ("modules_submodule", "name"),
    ("modules_indicator", "name"),
    ("modules_indicatorarea", "name"),
    ("questions_rootquestion", "name"),
    ("questions_subquestion", "name"),
    ("questions_choicegroup", "name"),
    ("questions_choicegroupfile", "name"),
    ("questions_recallperiod", "name"),
    ("questions_suffix", "name"),
    ("questions_calculation", "name"),
    ("questions_repeatsection", "name"),
    ("surveys_surveycategory", "name"),
    ("surveys_surveytype", "name"),
    ("surveys_surveymode", "name"),
    ("surveys_surveyattribute", "name"),
]


def _alter_columns_sql(collation_name):
    return "\n".join(
        f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE varchar(255) COLLATE "{collation_name}" USING {column}::text;'
        for table, column in CASE_INSENSITIVE_COLUMNS
    )


LIKE_INDEX_FILTER = " OR ".join(
    f"(tbl.relname = '{table}' AND attr.attname = '{column}')"
    for table, column in LIKE_INDEX_COLUMNS
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


RECREATE_COLLATION_SQL = "\n".join(
    [
        'ALTER COLLATION "case_insensitive" RENAME TO "case_insensitive_deterministic_old";',
        "CREATE COLLATION case_insensitive (provider = icu, locale = 'und-u-ks-level2', deterministic = false);",
        _alter_columns_sql("case_insensitive"),
        'DROP COLLATION "case_insensitive_deterministic_old";',
    ]
)


REVERSE_SQL = "\n".join(
    [
        'ALTER COLLATION "case_insensitive" RENAME TO "case_insensitive_nondeterministic_old";',
        "CREATE COLLATION case_insensitive (provider = icu, locale = 'und-u-ks-level2', deterministic = true);",
        _alter_columns_sql("case_insensitive"),
        'DROP COLLATION "case_insensitive_nondeterministic_old";',
    ]
)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_replace_citext_with_collation"),
        ("modules", "0032_replace_citext_name_with_collation"),
        ("questions", "0049_replace_citext_name_with_collation"),
        ("surveys", "0021_replace_citext_name_with_collation"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_LIKE_INDEXES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=RECREATE_COLLATION_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
