from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("saved_surveys", "0006_savedsurvey_languages"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedsurvey",
            name="indicator_areas_order",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="savedsurvey",
            name="indicators_order",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="savedsurvey",
            name="modules_order",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
