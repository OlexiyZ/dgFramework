# Generated by Django 5.0.1 on 2024-02-18 09:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0019_alter_field_field_alias_alter_field_field_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='field',
            old_name='field_list',
            new_name='field_list_id',
        ),
    ]
