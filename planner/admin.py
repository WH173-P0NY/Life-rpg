from __future__ import annotations

from django.contrib import admin

from .models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_type",
        "start_at",
        "end_at",
        "all_day",
        "recurrence_frequency",
        "recurrence_index",
        "location",
    )
    list_filter = ("event_type", "all_day", "recurrence_frequency", "start_at")
    search_fields = ("title", "description", "location")
    readonly_fields = ("recurrence_group", "created_at", "updated_at")
    ordering = ("start_at", "end_at", "title")
