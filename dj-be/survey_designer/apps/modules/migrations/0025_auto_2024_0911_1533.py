import django.db.models.deletion
from django.db import migrations, models


def migrate_modes_to_types(apps, schema_editor):
    # Get models
    SubmoduleMapping = apps.get_model('modules', 'SubmoduleMapping')
    SubmoduleMappingSurveyMode = apps.get_model('modules', 'SubmoduleMappingSurveyMode')
    SubmoduleMappingSurveyType = apps.get_model('modules', 'SubmoduleMappingSurveyType')

    # Iterate over each SubmoduleMapping
    for submodule_mapping in SubmoduleMapping.objects.all():
        # Get all survey types associated with this submodule mapping
        survey_types = SubmoduleMappingSurveyType.objects.filter(submodule_mapping=submodule_mapping)

        # Get all modes that belong to this submodule mapping (before we changed it to be related to types)
        survey_modes = SubmoduleMappingSurveyMode.objects.filter(submodule_mapping=submodule_mapping)

        # Assign existing modes to the first survey type
        if survey_modes.exists() and survey_types.exists():
            first_type = survey_types.first()  # Get the first type

            for mode in survey_modes:
                # If this mode doesn't already have a type, assign it to the first type
                if not mode.survey_type:
                    mode.survey_type = first_type
                    mode.save()

            # Now create new modes for the other survey types, but avoid duplicates
            for survey_type in survey_types.exclude(pk=first_type.pk):
                for mode in survey_modes:
                    # Create new SubmoduleMappingSurveyMode for this survey_type if no duplicate exists
                    if not SubmoduleMappingSurveyMode.objects.filter(
                        survey_type=survey_type, survey_mode=mode.survey_mode,
                        submodule_mapping=submodule_mapping).exists():
                        SubmoduleMappingSurveyMode.objects.create(
                            submodule_mapping=submodule_mapping,  # Still using submodule_mapping
                            survey_type=survey_type,
                            survey_mode=mode.survey_mode,
                            is_mandatory=mode.is_mandatory
                        )


class Migration(migrations.Migration):
    dependencies = [
        ('modules', '0024_auto_20240911_1426'),
    ]

    operations = [
        migrations.RunPython(migrate_modes_to_types, reverse_code=migrations.RunPython.noop),
    ]
