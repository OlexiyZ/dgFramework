# Generated by Django 5.0.1 on 2024-02-10 18:12

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("storage", "0013_alter_source_source_list_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="source",
            name="source_list_name",
        ),
    ]
