# Generated by Django 5.0.2 on 2024-02-18 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0032_rename_field_data_source_field_field_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='source_type',
            field=models.CharField(choices=[('tbd', 'To be defined'), ('table', 'Table'), ('data_source', 'Data Source'), ('query', 'Query')], default='tbd', max_length=30),
        ),
        migrations.AddConstraint(
            model_name='field',
            constraint=models.UniqueConstraint(fields=('field_list', 'field_alias', 'source_list'), name='field_constraint'),
        ),
    ]
