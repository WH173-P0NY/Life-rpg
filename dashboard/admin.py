from django.contrib import admin

from .models import LlmProviderConfig


@admin.register(LlmProviderConfig)
class LlmProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "model_name", "is_enabled", "updated_at")
    list_filter = ("provider", "is_enabled")
    search_fields = ("provider", "model_name")
    readonly_fields = ("created_at", "updated_at")
