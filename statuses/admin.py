from django.contrib import admin

from .models import StatusDefinition, StatusEntry


@admin.register(StatusDefinition)
class StatusDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "description")


@admin.register(StatusEntry)
class StatusEntryAdmin(admin.ModelAdmin):
    list_display = ("status_definition", "value", "recorded_at", "created_at")
    list_filter = ("status_definition", "recorded_at")
    search_fields = ("note", "status_definition__name")
    autocomplete_fields = ("status_definition",)
