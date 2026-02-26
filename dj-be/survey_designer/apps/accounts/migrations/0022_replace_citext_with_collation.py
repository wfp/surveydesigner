# Generated for Django 5.2: replace CICharField/CIEmailField with collation-based fields

from django.contrib.postgres.operations import CreateCollation
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_alter_user_is_staff"),
    ]

    operations = [
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
