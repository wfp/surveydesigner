import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('surveys', '0018_auto_20230706_1312'),
        ('modules', '0023_auto_20240108_0944'),
    ]

    operations = [
        migrations.AddField(
            model_name='submodulemappingsurveymode',
            name='survey_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='modes', to='modules.submodulemappingsurveytype'),
        ),
        migrations.AlterUniqueTogether(
            name='submodulemappingsurveymode',
            unique_together={('survey_type', 'survey_mode', 'submodule_mapping')},
        ),
    ]
