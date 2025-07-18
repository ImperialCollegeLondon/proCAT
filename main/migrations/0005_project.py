# Generated by Django 5.2.1 on 2025-05-13 16:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_initial_analysis_codes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the project.', unique=True, verbose_name='Name')),
                ('nature', models.CharField(choices=[('Support', 'Support'), ('Standard', 'Standard')], help_text='Nature of the project.  Typically, support projects cannot be allocated to sprints easily, the work there is more lightweight and ad hoc, sometimes at short notice.', verbose_name='Nature')),
                ('pi', models.CharField(help_text='Name of the principal investigator responsible for the project. It should be the actual grant holder, not the main point of contact', verbose_name='Principal Investigator')),
                ('start_date', models.DateField(blank=True, help_text='Start date for the project.', null=True, verbose_name='Start date')),
                ('end_date', models.DateField(blank=True, help_text='End date for the project.', null=True, verbose_name='End date')),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Not started', 'Not started'), ('Active', 'Active'), ('Completted', 'Completted')], default='Draft', help_text="Status of the project. Unless the status is 'Draft', most other fields are mandatory.", verbose_name='Status')),
                ('charging', models.CharField(choices=[('Actual', 'Actual'), ('Pro-rata', 'Pro-rata'), ('Manual', 'Manual')], default='Actual', help_text="Method for charging the costs of the project. 'Actual' is based on timesheet records. 'Pro-rata' charges the same amount every month. Finally, in 'Manual' the charges are scheduled manually.", verbose_name='Charging method')),
                ('department', models.ForeignKey(help_text='The department in which the research project is based, primarily.', on_delete=django.db.models.deletion.PROTECT, to='main.department')),
                ('lead', models.ForeignKey(blank=True, help_text='Project lead from the RSE side.', null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
