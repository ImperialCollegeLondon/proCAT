# Generated by Django 5.2.3 on 2025-06-19 13:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_timeentry'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='notifications_effort',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='project',
            name='notifications_weeks',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
