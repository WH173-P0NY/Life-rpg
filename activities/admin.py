from django.contrib import admin

from .models import (
    ActivityDefinition,
    ActivityEntry,
    ActivityReward,
    ActivityRule,
)


class ActivityRewardInline(admin.TabularInline):
    model = ActivityReward
    extra = 1
    autocomplete_fields = ("skill",)


@admin.register(ActivityDefinition)
class ActivityDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "life_area", "created_at")
    list_filter = ("life_area",)
    search_fields = ("name", "description")
    inlines = (ActivityRewardInline,)


@admin.register(ActivityReward)
class ActivityRewardAdmin(admin.ModelAdmin):
    list_display = ("activity_definition", "skill", "xp_per_minute")
    list_filter = ("activity_definition", "skill")
    search_fields = ("activity_definition__name", "skill__name")
    autocomplete_fields = ("activity_definition", "skill")


@admin.register(ActivityRule)
class ActivityRuleAdmin(admin.ModelAdmin):
    list_display = ("pattern", "activity_definition")
    list_filter = ("activity_definition",)
    search_fields = ("pattern", "activity_definition__name")
    autocomplete_fields = ("activity_definition",)


@admin.register(ActivityEntry)
class ActivityEntryAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "activity_definition",
        "minutes",
        "total_xp_display",
        "started_at",
        "created_at",
    )
    list_filter = ("activity_definition", "started_at")
    search_fields = ("source", "activity_definition__name")
    autocomplete_fields = ("activity_definition",)

    @admin.display(description="XP")
    def total_xp_display(self, obj: ActivityEntry) -> int:
        return obj.total_xp()
