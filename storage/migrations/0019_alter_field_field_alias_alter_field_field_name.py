# Generated by Django 5.0.1 on 2024-02-10 19:43

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storage", "0018_field_field_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="field",
            name="field_alias",
            field=models.CharField(max_length=30),
        ),
        migrations.AlterField(
            model_name="field",
            name="field_name",
            field=models.CharField(max_length=30),
        ),
    ]
