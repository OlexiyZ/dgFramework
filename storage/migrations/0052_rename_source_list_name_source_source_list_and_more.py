# Generated by Django 5.0.2 on 2024-05-19 20:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0051_alter_report_version'),
    ]

    operations = [
        migrations.RenameField(
            model_name='source',
            old_name='source_list_name',
            new_name='source_list',
        ),
        migrations.RenameField(
            model_name='source',
            old_name='source_union_list_name',
            new_name='source_union_list',
        ),
    ]
