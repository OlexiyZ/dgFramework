# Generated by Django 5.0.1 on 2024-02-10 19:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storage", "0017_remove_source_source_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="field",
            name="field_name",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
