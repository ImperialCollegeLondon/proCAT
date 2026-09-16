from datetime import timedelta
from typing import Any

from django.db import migrations

from ..utils import days_to_fte


def set_default_phase_for_active_projects(apps: Any, schema_editor: Any) -> None:  # type: ignore [explicit-any]
    """Backfill a default phase for pre-existing Active-status projects.

    `Project.total_effort`, and everything derived from it (`days_left`,
    `percent_effort_left`, monthly charge validation, notifications, etc.), now
    derives its value from non-maintenance phases for projects in Active status,
    falling back to funding only when a project has no phases at all.

    Projects that were already Active before the phases feature existed (or that
    were created directly, bypassing form/model validation) may have no
    `ProjectPhase` records. This backfills a single default phase spanning the
    whole project for any such project, using the same funding-derived effort
    figure that `total_effort` would previously have returned unconditionally, so
    that behaviour is preserved for anything relying on it.
    """
    Project = apps.get_model("main", "Project")
    ProjectPhase = apps.get_model("main", "ProjectPhase")

    for project in Project.objects.filter(status="Active"):
        if project.phases.exists():
            continue

        if not project.start_date or not project.end_date:
            continue

        total_effort = sum(
            funding.budget / funding.daily_rate
            for funding in project.funding_source.all()
            if funding.daily_rate
        )
        if not total_effort:
            continue

        # `end_date` is an inclusive calendar range, hence the `+ timedelta(days=1)`.
        value = days_to_fte(
            project.start_date,
            project.end_date + timedelta(days=1),
            float(total_effort),
        )
        ProjectPhase.objects.create(
            project=project,
            value=value,
            start_date=project.start_date,
            end_date=project.end_date,
            is_maintenance=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0029_backfill_maintenance_phase"),
    ]

    operations = [
        migrations.RunPython(
            code=set_default_phase_for_active_projects,
            # Not meaningfully reversible: we can't distinguish phases created by
            # this migration from ones created manually afterwards.
            reverse_code=migrations.RunPython.noop,
        ),
    ]
