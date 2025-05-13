"""General utilities for ProCAT."""

from typing import Any

from . import models

ACTIVITY_CODES = (
    {
        "code": 182130,
        "description": "FEC Directly Allocated EQP&FACILITIES",
        "notes": "FEC-like projects (typically UKRI, but could be others) at the "
        "pre-award stage (DA) - P accounts only",
    },
    {
        "code": 165133,
        "description": "FACILITIES USAGE (DI FEC PROJECTS)",
        "notes": "FEC-like projects (typically UKRI, but could be others) when costs"
        " were not budgeted (DI) - P accounts only",
    },
    {
        "code": 165134,
        "description": "CHG OUT FACILITY/NON-FEC",
        "notes": "Non-FEC projects (typically charities) in all cases (DI) - P accounts"
        " only",
    },
    {
        "code": 165138,
        "description": "FACILITIES USAGE (Internal funds)",
        "notes": "Used is charge to non-research accounts - NOT P accounts",
    },
)


def create_activities(*args: Any) -> None:  # type: ignore [explicit-any]
    """Create default activity codes."""
    models.ActivityCode.objects.bulk_create(
        [models.ActivityCode(**ac) for ac in ACTIVITY_CODES]
    )


def destroy_activities(*args: Any) -> None:  # type: ignore [explicit-any]
    """Delete default activity codes."""
    codes = [ac["code"] for ac in ACTIVITY_CODES]
    models.ActivityCode.objects.filter(code__in=codes).delete()
