from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('modules', '0025_auto_2024_0911_1533'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='submodulemappingsurveymode',
            unique_together={('survey_type', 'survey_mode')},
        ),
        migrations.RemoveField(
            model_name='submodulemappingsurveymode',
            name='submodule_mapping',
        ),
        migrations.RemoveField(
            model_name='submodulemapping',
            name='survey_modes',
        ),
    ]
