# Generated for Django 5.2: replace CICharField/CIEmailField with collation-based fields

from django.contrib.postgres.operations import CreateCollation
from django.db import migrations, models

LIKE_INDEX_FILTER = "(tbl.relname = 'accounts_user' AND attr.attname = 'email')"


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


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_alter_user_is_staff"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_LIKE_INDEXES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='DROP COLLATION IF EXISTS "case_insensitive" CASCADE;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        CreateCollation(
            "case_insensitive",
            "und-u-ks-level2",
            provider="icu",
            deterministic=False,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "accounts_user" ALTER COLUMN "email" TYPE varchar(255) COLLATE "case_insensitive" USING email::text;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql='ALTER TABLE "accounts_userapikey" ALTER COLUMN "name" TYPE varchar(255) COLLATE "case_insensitive" USING name::text;',
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="email",
                    field=models.EmailField(
                        db_collation="case_insensitive",
                        max_length=255,
                        unique=True,
                    ),
                ),
                migrations.AlterField(
                    model_name="userapikey",
                    name="name",
                    field=models.CharField(
                        blank=True,
                        db_collation="case_insensitive",
                        max_length=255,
                    ),
                ),
            ],
        ),
    ]
