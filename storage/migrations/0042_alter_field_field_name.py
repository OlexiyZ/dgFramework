# Generated by Django 5.0.1 on 2024-04-18 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0041_alter_field_field_function'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='field_name',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]