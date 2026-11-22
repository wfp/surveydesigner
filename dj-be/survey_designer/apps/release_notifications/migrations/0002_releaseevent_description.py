from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("release_notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="releaseevent",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
