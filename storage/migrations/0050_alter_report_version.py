# Generated by Django 5.0.2 on 2024-05-17 08:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0049_report_change_date_report_change_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='version',
            field=models.CharField(max_length=10),
        ),
    ]
