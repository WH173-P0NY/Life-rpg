from __future__ import annotations

from django.contrib import admin

from .models import (
    Achievement,
    AchievementUnlock,
    CharacterIdentity,
    Challenge,
    ChallengeCheckIn,
    ChallengeReward,
    Goal,
    GoalProgressEntry,
    GoalSkill,
    Habit,
    HabitCheckIn,
    HabitMilestone,
    HabitMilestoneReward,
    HabitMilestoneUnlock,
    JournalEntry,
    Quest,
    QuestCompletion,
    QuestReward,
)


class QuestRewardInline(admin.TabularInline):
    model = QuestReward
    extra = 1
    autocomplete_fields = ("skill",)


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "quest_type",
        "status",
        "difficulty",
        "target_value",
        "target_unit",
        "sort_order",
    )
    list_filter = ("quest_type", "status", "difficulty", "created_by")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    inlines = (QuestRewardInline,)


@admin.register(QuestCompletion)
class QuestCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "quest",
        "completed_on",
        "progress_value",
        "completed_at",
        "xp_awarded_at",
    )
    list_filter = ("completed_on", "quest__quest_type")
    search_fields = ("quest__title", "note")
    readonly_fields = ("created_at", "updated_at", "xp_awarded_at")
    autocomplete_fields = ("quest",)


@admin.register(QuestReward)
class QuestRewardAdmin(admin.ModelAdmin):
    list_display = ("quest", "skill", "xp_amount")
    list_filter = ("quest", "skill")
    search_fields = ("quest__title", "skill__name")
    autocomplete_fields = ("quest", "skill")


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "frequency",
        "target_value",
        "target_unit",
        "is_active",
        "sort_order",
    )
    list_filter = ("frequency", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HabitCheckIn)
class HabitCheckInAdmin(admin.ModelAdmin):
    list_display = ("habit", "checked_on", "value")
    list_filter = ("checked_on", "habit")
    search_fields = ("habit__name", "note")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("habit",)


class HabitMilestoneRewardInline(admin.TabularInline):
    model = HabitMilestoneReward
    extra = 1
    autocomplete_fields = ("skill",)


@admin.register(HabitMilestone)
class HabitMilestoneAdmin(admin.ModelAdmin):
    list_display = ("title", "habit", "streak_days", "is_active")
    list_filter = ("is_active", "streak_days", "habit")
    search_fields = ("title", "habit__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("habit",)
    inlines = (HabitMilestoneRewardInline,)


@admin.register(HabitMilestoneReward)
class HabitMilestoneRewardAdmin(admin.ModelAdmin):
    list_display = ("milestone", "skill", "xp_amount")
    list_filter = ("milestone", "skill")
    search_fields = ("milestone__title", "skill__name")
    autocomplete_fields = ("milestone", "skill")


@admin.register(HabitMilestoneUnlock)
class HabitMilestoneUnlockAdmin(admin.ModelAdmin):
    list_display = ("habit", "milestone", "streak_days", "unlocked_at", "xp_awarded_at")
    list_filter = ("milestone", "habit", "unlocked_at")
    search_fields = ("habit__name", "milestone__title", "note")
    readonly_fields = ("unlocked_at", "xp_awarded_at")
    autocomplete_fields = ("habit", "milestone")


class GoalSkillInline(admin.TabularInline):
    model = GoalSkill
    extra = 1
    autocomplete_fields = ("skill",)


class GoalProgressEntryInline(admin.TabularInline):
    model = GoalProgressEntry
    extra = 0
    readonly_fields = ("previous_value", "new_value", "delta", "recorded_at", "created_at")
    can_delete = False


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "progress_value",
        "target_value",
        "due_on",
        "sort_order",
    )
    list_filter = ("status", "priority", "created_by", "life_area")
    search_fields = ("title", "description")
    readonly_fields = ("completed_at", "archived_at", "created_at", "updated_at")
    autocomplete_fields = ("life_area",)
    inlines = (GoalSkillInline, GoalProgressEntryInline)


@admin.register(GoalSkill)
class GoalSkillAdmin(admin.ModelAdmin):
    list_display = ("goal", "skill", "weight")
    list_filter = ("skill",)
    search_fields = ("goal__title", "skill__name")
    autocomplete_fields = ("goal", "skill")


@admin.register(GoalProgressEntry)
class GoalProgressEntryAdmin(admin.ModelAdmin):
    list_display = ("goal", "previous_value", "new_value", "delta", "source_type", "recorded_at")
    list_filter = ("source_type", "recorded_at")
    search_fields = ("goal__title", "note", "source_type")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("goal",)


class ChallengeRewardInline(admin.TabularInline):
    model = ChallengeReward
    extra = 1
    autocomplete_fields = ("skill",)


class ChallengeCheckInInline(admin.TabularInline):
    model = ChallengeCheckIn
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "start_date",
        "end_date",
        "current_value",
        "target_value",
        "reward_title",
    )
    list_filter = ("status", "cadence", "created_by", "start_date", "end_date")
    search_fields = ("title", "description", "reward_title")
    readonly_fields = ("completed_at", "failed_at", "xp_awarded_at", "created_at", "updated_at")
    autocomplete_fields = ("goal",)
    inlines = (ChallengeRewardInline, ChallengeCheckInInline)


@admin.register(ChallengeReward)
class ChallengeRewardAdmin(admin.ModelAdmin):
    list_display = ("challenge", "skill", "xp_amount")
    list_filter = ("challenge", "skill")
    search_fields = ("challenge__title", "skill__name")
    autocomplete_fields = ("challenge", "skill")


@admin.register(ChallengeCheckIn)
class ChallengeCheckInAdmin(admin.ModelAdmin):
    list_display = ("challenge", "checked_on", "value", "successful")
    list_filter = ("checked_on", "successful", "challenge")
    search_fields = ("challenge__title", "note")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("challenge",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "rarity", "trigger_type", "is_active", "sort_order")
    list_filter = ("rarity", "trigger_type", "is_active")
    search_fields = ("title", "description", "code")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AchievementUnlock)
class AchievementUnlockAdmin(admin.ModelAdmin):
    list_display = ("achievement", "unlocked_at", "source_type", "source_id")
    list_filter = ("source_type", "unlocked_at", "achievement__rarity")
    search_fields = ("achievement__title", "note", "source_type")
    readonly_fields = ("unlocked_at", "created_at")
    autocomplete_fields = ("achievement",)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "entry_type", "entry_date", "source_type", "created_at")
    list_filter = ("entry_type", "source_type", "entry_date", "mood")
    search_fields = (
        "title",
        "content",
        "reflection_proud",
        "reflection_challenge",
        "reflection_learned",
        "reflection_improve",
        "reflection_goal_action",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-entry_date", "-created_at", "-id")


@admin.register(CharacterIdentity)
class CharacterIdentityAdmin(admin.ModelAdmin):
    list_display = ("title", "started_on", "ended_on", "is_active", "created_at")
    list_filter = ("is_active", "started_on")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
