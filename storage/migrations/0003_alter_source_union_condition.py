# Generated by Django 5.0.1 on 2024-02-10 16:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storage", "0002_remove_sourcelist_source_list_alias"),
    ]

    operations = [
        migrations.AlterField(
            model_name="source",
            name="union_condition",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
