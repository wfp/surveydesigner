from django.conf import settings
from django.db import migrations


def set_default_organization(app, schema_editor):
    Organization = app.get_model("organization", "Organization")
    Module = app.get_model("modules", "Module")
    wfp = Organization.objects.get(name=settings.INITIAL_ORGANIZATION)
    for module in Module.objects.all().iterator():
        module.organizations.set([wfp])


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0017_module_organizations'),
    ]

    operations = [
        migrations.RunPython(set_default_organization, reverse_code=migrations.RunPython.noop)
    ]
