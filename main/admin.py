"""Admin module for the main app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivityCode, Capacity, Department, Funding, Project, User

admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(ActivityCode)


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
        "project_code",
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
