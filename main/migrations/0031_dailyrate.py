from datetime import date
from decimal import Decimal
from typing import Any

import django.core.validators
import django.utils.timezone
from django.db import migrations, models

import main.models


def seed_initial_daily_rate(apps: Any, schema_editor: Any) -> None:  # type: ignore [explicit-any]
    """Seed a `DailyRate` matching the rate previously hardcoded as the default.

    The `effective_date` is set far in the past so this seeded rate is always
    picked up as "current" unless/until a later-dated rate is added.
    """
    DailyRate = apps.get_model("main", "DailyRate")
    DailyRate.objects.create(rate=Decimal("389.00"), effective_date=date(2000, 1, 1))


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0030_backfill_active_project_phase"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyRate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rate",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="The standard daily rate, effective from "
                        "'Effective date'.",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Daily rate",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(
                        default=django.utils.timezone.now,
                        help_text="The date from which this daily rate applies.",
                        verbose_name="Effective date",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "daily rates",
                "ordering": ("-effective_date",),
            },
        ),
        migrations.RunPython(
            code=seed_initial_daily_rate,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="funding",
            name="daily_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=main.models.get_current_daily_rate,
                help_text="The daily rate for this funding. Defaults to the "
                "current standard rate (see the 'Daily rates' admin section), "
                "but can be overridden for funding sources that use a "
                "different, bespoke rate.",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Daily rate",
            ),
        ),
    ]
