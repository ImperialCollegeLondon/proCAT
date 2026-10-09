"""Admin module for the main app."""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import URLPattern, path, reverse
from rangefilter.filters import DateRangeQuickSelectListFilterBuilder

from .models import (
    AnalysisCode,
    Capacity,
    DailyRate,
    Department,
    Funding,
    MonthlyCharge,
    Project,
    TimeEntry,
    User,
)
from .tasks import sync_clockify_time_entries, sync_kimai_time_entries

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


@admin.register(DailyRate)
class DailyRateAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the DailyRate model.

    Adding a new entry here changes the default rate proposed for new
    `Funding` records going forward; it does not affect existing ones.
    """

    list_display = (
        "rate",
        "effective_date",
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
        "clockify_id",
        "kimai_id",
    )
    list_filter = ("user", "project")

    def get_urls(self) -> list[URLPattern]:
        """Get urls for this admin view."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync_timesheets/",
                self.sync_time_entries_view,
                name="sync-timesheets",
            )
        ]
        return custom_urls + urls

    def sync_time_entries_view(self, request: HttpRequest) -> HttpResponse:
        """Forces a synchronisation of timesheets."""
        issues = sync_clockify_time_entries()
        issues = sync_kimai_time_entries() or issues
        if not issues:
            self.message_user(request, "Syncronysation completted successfully!")
        else:
            self.message_user(
                request,
                "Something went wrong with the synchronisation. Check the logs.",
                level=messages.ERROR,
            )
        return HttpResponseRedirect(reverse("admin:main_timeentry_changelist"))


@admin.register(MonthlyCharge)
class MonthlyChargeAdmin(admin.ModelAdmin):  # type: ignore [type-arg]
    """Admin class for the MonthlyCharge model."""

    list_display = (
        "project",
        "funding",
        "amount",
        "date",
        "description",
        "status",
    )
    list_filter = ("project", ("date", DateRangeQuickSelectListFilterBuilder()))
    actions = ("confirm_charge",)

    @admin.action(description="Confirm monthly charges")
    def confirm_charge(
        self, request: HttpRequest, queryset: QuerySet[MonthlyCharge]
    ) -> None:
        """Update monthly charge status to 'Confirmed'."""
        queryset.update(status="Confirmed")
