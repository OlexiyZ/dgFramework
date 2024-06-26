# Generated by Django 5.0.1 on 2024-02-10 19:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storage", "0016_alter_field_field_description_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="source",
            name="source_name",
        ),
        migrations.AddField(
            model_name="source",
            name="union_source_list_name",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_list_names",
                to="storage.sourcelist",
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="source_list_name",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_names",
                to="storage.sourcelist",
            ),
        ),
    ]
