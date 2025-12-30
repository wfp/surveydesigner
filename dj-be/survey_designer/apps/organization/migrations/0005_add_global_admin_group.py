from django.db import migrations


def create_group(apps, _):
    group_class = apps.get_model('auth', 'Group')
    group_class(name='Global Admins').save()


class Migration(migrations.Migration):
    dependencies = [
        ('organization', '0004_remove_organization_is_shared'),
    ]

    operations = [
        migrations.RunPython(
            create_group,
            reverse_code=migrations.RunPython.noop
        ),
    ]
