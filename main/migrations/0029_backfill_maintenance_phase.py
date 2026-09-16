from typing import Any

from django.db import migrations


def set_maintenance_phase(apps: Any, schema_editor: Any) -> None:  # type: ignore [explicit-any]
    """Flag a maintenance phase for pre-existing Maintenance-status projects.

    The `is_maintenance` field defaults to False, so projects that were already
    in "Maintenance" status before this field was introduced have no phase
    flagged. This backfills that flag using the old heuristic of treating the
    last phase (by start_date) as the maintenance phase.
    """
    Project = apps.get_model("main", "Project")

    for project in Project.objects.filter(status="Maintenance"):
        if project.phases.filter(is_maintenance=True).exists():
            continue

        last_phase = project.phases.order_by("start_date").last()
        if last_phase is not None:
            last_phase.is_maintenance = True
            last_phase.save(update_fields=["is_maintenance"])


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0028_projectphase_is_maintenance"),
    ]

    operations = [
        migrations.RunPython(
            code=set_maintenance_phase,
            # Not meaningfully reversible: we can't distinguish phases flagged
            # by this migration from ones flagged manually afterwards.
            reverse_code=migrations.RunPython.noop,
        ),
    ]
