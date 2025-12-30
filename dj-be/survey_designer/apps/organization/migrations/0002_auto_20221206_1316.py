from django.db import migrations


def create_base_organizations(app, schema_editor):
    Organization = app.get_model("organization", "Organization")
    for organization_name, allowed_domains in {
        "WFP": ["wfp.org"],
        "UNICEF": ["unicef.org"],
    }.items():
        Organization.objects.create(
            name=organization_name, allowed_domains=allowed_domains
        )


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_base_organizations, reverse_code=migrations.RunPython.noop)]
