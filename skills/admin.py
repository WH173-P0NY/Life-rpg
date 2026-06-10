from django.contrib import admin

from .models import LifeArea, Skill, XpEvent


@admin.register(LifeArea)
class LifeAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "description")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "life_area", "total_xp", "level", "created_at")
    list_filter = ("life_area",)
    search_fields = ("name",)

    @admin.display(description="XP")
    def total_xp(self, obj: Skill) -> int:
        return obj.get_total_xp()

    @admin.display(description="Level")
    def level(self, obj: Skill) -> int:
        return obj.get_level()


@admin.register(XpEvent)
class XpEventAdmin(admin.ModelAdmin):
    list_display = ("skill", "amount", "source_type", "earned_at", "created_at")
    list_filter = ("skill", "source_type", "earned_at")
    search_fields = ("note", "skill__name")
    autocomplete_fields = ("skill", "activity_entry")
