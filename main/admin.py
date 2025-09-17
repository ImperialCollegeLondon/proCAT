"""Admin module for the main app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from rangefilter.filters import DateRangeQuickSelectListFilterBuilder

from .models import (
    AnalysisCode,
    Capacity,
    Department,
    Funding,
    MonthlyCharge,
    Project,
    TimeEntry,
    User,
)

admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(AnalysisCode)


@admin.register(Capacity)
class CapacityAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the Capacity model."""

    list_display = (
        "user",
        "value",
        "start_date",
    )


@admin.register(Funding)
class FundingAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the Funding model."""

    list_display = (
        "project",
        "cost_centre",
        "activity",
        "funding_body",
        "source",
        "expiry_date",
        "budget",
        "effort",
        "effort_left",
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the Project model."""

    list_display = (
        "name",
        "nature",
        "department",
        "status",
        "charging",
        "start_date",
        "end_date",
        "weeks_to_deadline",
        "days_left",
    )


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the TimeEntry model."""

    filter_horizontal = ("monthly_charge",)

    list_display = (
        "user",
        "project",
        "start_time",
        "end_time",
    )
    list_filter = ("user", "project")


@admin.register(MonthlyCharge)
class MonthlyChargeAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the MonthlyCharge model."""

    list_display = (
        "project",
        "funding",
        "amount",
        "date",
        "description",
    )
    list_filter = ("project", ("date", DateRangeQuickSelectListFilterBuilder()))
