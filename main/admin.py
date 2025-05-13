"""Admin module for the main app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivityCode, Department, User

admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(ActivityCode)
