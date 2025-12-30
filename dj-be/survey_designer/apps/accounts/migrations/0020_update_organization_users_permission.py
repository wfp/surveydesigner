from django.db import migrations


def _set_group_and_is_staff(apps, _):
    user_class = apps.get_model("accounts", "User")
    group_class = apps.get_model('auth', 'Group')

    for user in user_class.objects.filter(is_staff=False).exclude(organization=None):
        user.is_staff = True
        group = group_class.objects.filter(name="Read Only").first()
        user.groups.add(group)
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_auto_20230323_1011'),
    ]

    operations = [
        migrations.RunPython(_set_group_and_is_staff, reverse_code=migrations.RunPython.noop),
    ]
