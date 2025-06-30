"""General utilities for ProCAT."""

from typing import Any

from . import models

ANALYSIS_CODES = (
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
        "notes": "Used if charged to non-research accounts - NOT P accounts",
    },
)


def create_analysis(*args: Any) -> None:  # type: ignore [explicit-any]
    """Create default analysis codes."""
    models.AnalysisCode.objects.bulk_create(
        [models.AnalysisCode(**ac) for ac in ANALYSIS_CODES]
    )


def destroy_analysis(*args: Any) -> None:  # type: ignore [explicit-any]
    """Delete default analysis codes."""
    codes = [ac["code"] for ac in ANALYSIS_CODES]
    models.AnalysisCode.objects.filter(code__in=codes).delete()
