from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.text import slugify

from .choices import (
    AchievementRarity,
    AchievementTrigger,
    CampaignCreatedBy,
    CampaignDifficulty,
    CampaignNodeKind,
    CampaignQuestUnlockMode,
    CampaignStatus,
    ChallengeCadence,
    ChallengeStatus,
    CreationSource,
    GoalPriority,
    GoalStatus,
    HabitFrequency,
    JournalEntryType,
    JournalMood,
    QuestDifficulty,
    QuestStatus,
    QuestType,
    TargetUnit,
)


class Quest(models.Model):
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    quest_type = models.CharField(
        max_length=20,
        choices=QuestType.choices,
        default=QuestType.DAILY,
    )
    status = models.CharField(
        max_length=20,
        choices=QuestStatus.choices,
        default=QuestStatus.ACTIVE,
    )
    difficulty = models.CharField(
        max_length=20,
        choices=QuestDifficulty.choices,
        default=QuestDifficulty.NORMAL,
    )
    target_value = models.PositiveIntegerField(default=1)
    target_unit = models.CharField(
        max_length=20,
        choices=TargetUnit.choices,
        default=TargetUnit.COUNT,
    )
    created_by = models.CharField(
        max_length=20,
        choices=CreationSource.choices,
        default=CreationSource.MANUAL,
    )
    available_from = models.DateField(null=True, blank=True)
    available_until = models.DateField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(target_value__gt=0),
                name="rpg_quest_target_value_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValidationError({"title": "Quest title cannot be empty."})
        if self.target_value is not None and self.target_value <= 0:
            raise ValidationError(
                {"target_value": "Target value must be greater than 0."}
            )
        if (
            self.available_from
            and self.available_until
            and self.available_until < self.available_from
        ):
            raise ValidationError(
                {"available_until": "Available until cannot be before available from."}
            )
        if (
            self._state.adding
            and self.created_by == CreationSource.AI
            and self.status != QuestStatus.DRAFT
        ):
            raise ValidationError(
                {"status": "AI-created quests must start as draft."}
            )

    def is_available_on(self, day: date) -> bool:
        if self.available_from and day < self.available_from:
            return False
        if self.available_until and day > self.available_until:
            return False
        return True

    def is_repeatable_daily(self) -> bool:
        return self.quest_type == QuestType.DAILY

    def reward_xp_total(self) -> int:
        total = self.rewards.aggregate(total=Sum("xp_amount"))["total"]
        return int(total or 0)


class QuestReward(models.Model):
    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.CASCADE,
        related_name="quest_rewards",
    )
    xp_amount = models.PositiveIntegerField()

    class Meta:
        ordering = ["quest__title", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["quest", "skill"],
                name="rpg_quest_reward_unique_quest_skill",
            ),
            models.CheckConstraint(
                condition=Q(xp_amount__gt=0),
                name="rpg_quest_reward_xp_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quest} -> {self.skill} (+{self.xp_amount} XP)"

    def clean(self) -> None:
        if self.xp_amount is not None and self.xp_amount <= 0:
            raise ValidationError({"xp_amount": "XP amount must be greater than 0."})


class QuestCompletion(models.Model):
    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    completed_on = models.DateField()
    progress_value = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-completed_on", "quest__sort_order", "quest__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["quest", "completed_on"],
                name="rpg_quest_completion_unique_quest_day",
            ),
            models.CheckConstraint(
                condition=Q(progress_value__gte=0),
                name="rpg_quest_completion_progress_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quest} on {self.completed_on}"

    def clean(self) -> None:
        if self.progress_value is not None and self.progress_value < 0:
            raise ValidationError(
                {"progress_value": "Progress value cannot be negative."}
            )
        if (
            self.completed_at
            and self.quest_id
            and self.progress_value < self.quest.target_value
        ):
            raise ValidationError(
                {
                    "progress_value": (
                        "Completed quest progress must be greater than or equal "
                        "to the target value."
                    )
                }
            )


class Campaign(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT,
    )
    created_by = models.CharField(
        max_length=20,
        choices=CampaignCreatedBy.choices,
        default=CampaignCreatedBy.USER,
    )
    difficulty = models.CharField(
        max_length=20,
        choices=CampaignDifficulty.choices,
        default=CampaignDifficulty.NORMAL,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    life_area = models.ForeignKey(
        "skills.LifeArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    starts_on = models.DateField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True)
    reward_xp = models.PositiveIntegerField(default=0)
    reward_skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_rewards",
    )
    reward_title = models.CharField(max_length=180, blank=True)
    ai_prompt = models.TextField(blank=True)
    ai_provider = models.CharField(max_length=40, blank=True)
    ai_model = models.CharField(max_length=120, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_on", "title"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_campaign_title_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(reward_xp__gte=0),
                name="rpg_campaign_reward_xp_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    Q(due_on__isnull=True)
                    | Q(starts_on__isnull=True)
                    | Q(due_on__gte=models.F("starts_on"))
                ),
                name="rpg_campaign_due_on_gte_starts_on",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.reward_title = self.reward_title.strip()
        self.ai_prompt = self.ai_prompt.strip()
        self.ai_provider = self.ai_provider.strip()
        self.ai_model = self.ai_model.strip()
        if not self.title:
            raise ValidationError({"title": "Campaign title cannot be empty."})
        if self.starts_on and self.due_on and self.due_on < self.starts_on:
            raise ValidationError({"due_on": "Due on cannot be before starts on."})
        if self.reward_xp and self.reward_skill_id is None:
            raise ValidationError(
                {"reward_skill": "Campaign XP reward requires a reward skill."}
            )
        if self.status == CampaignStatus.COMPLETED and self.completed_at is None:
            raise ValidationError(
                {"completed_at": "Completed campaigns require completed_at."}
            )
        if self.completed_at and self.status != CampaignStatus.COMPLETED:
            raise ValidationError(
                {"status": "Completed campaigns must use completed status."}
            )
        if self.xp_awarded_at and self.completed_at is None:
            raise ValidationError(
                {"xp_awarded_at": "Campaign XP can be awarded only after completion."}
            )
        if self.status == CampaignStatus.DRAFT and self.xp_awarded_at is not None:
            raise ValidationError({"status": "Draft campaigns cannot award XP."})

    def reward_xp_total(self) -> int:
        return int(self.reward_xp or 0)


class CampaignQuest(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="campaign_quests",
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name="campaign_links",
    )
    stage = models.CharField(max_length=120, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    unlock_mode = models.CharField(
        max_length=30,
        choices=CampaignQuestUnlockMode.choices,
        default=CampaignQuestUnlockMode.AFTER_DEPENDENCIES,
    )
    node_kind = models.CharField(
        max_length=20,
        choices=CampaignNodeKind.choices,
        default=CampaignNodeKind.QUEST,
    )
    config = models.JSONField(default=dict, blank=True)
    map_x = models.PositiveIntegerField(default=0)
    map_y = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["campaign", "stage", "order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "quest"],
                name="rpg_campaign_quest_unique_campaign_quest",
            ),
            models.CheckConstraint(
                condition=Q(order__gte=0),
                name="rpg_campaign_quest_order_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(map_x__gte=0),
                name="rpg_campaign_quest_map_x_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(map_y__gte=0),
                name="rpg_campaign_quest_map_y_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.campaign}: {self.quest}"

    def clean(self) -> None:
        self.stage = self.stage.strip()
        if self.config is None:
            self.config = {}
        if not isinstance(self.config, dict):
            raise ValidationError({"config": "Campaign node config must be an object."})


class CampaignQuestDependency(models.Model):
    campaign_quest = models.ForeignKey(
        CampaignQuest,
        on_delete=models.CASCADE,
        related_name="dependencies",
    )
    depends_on = models.ForeignKey(
        CampaignQuest,
        on_delete=models.CASCADE,
        related_name="unlocks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["campaign_quest__campaign", "campaign_quest__order", "depends_on__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign_quest", "depends_on"],
                name="rpg_campaign_dependency_unique_edge",
            ),
            models.CheckConstraint(
                condition=~Q(campaign_quest=models.F("depends_on")),
                name="rpg_campaign_dependency_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.depends_on} -> {self.campaign_quest}"

    def clean(self) -> None:
        if (
            self.campaign_quest_id
            and self.depends_on_id
            and self.campaign_quest_id == self.depends_on_id
        ):
            raise ValidationError(
                {"depends_on": "Campaign quest cannot depend on itself."}
            )
        if self.campaign_quest_id and self.depends_on_id:
            if self.campaign_quest.campaign_id != self.depends_on.campaign_id:
                raise ValidationError(
                    {"depends_on": "Campaign dependencies cannot cross campaigns."}
                )


class Habit(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    frequency = models.CharField(
        max_length=20,
        choices=HabitFrequency.choices,
        default=HabitFrequency.DAILY,
    )
    target_value = models.PositiveIntegerField(default=1)
    target_unit = models.CharField(
        max_length=20,
        choices=TargetUnit.choices,
        default=TargetUnit.CHECK,
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="rpg_habit_unique_name"),
            models.CheckConstraint(
                condition=Q(target_value__gt=0),
                name="rpg_habit_target_value_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Habit name cannot be empty."})
        if self.target_value is not None and self.target_value <= 0:
            raise ValidationError(
                {"target_value": "Target value must be greater than 0."}
            )


class HabitCheckIn(models.Model):
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    checked_on = models.DateField()
    value = models.PositiveIntegerField(default=1)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checked_on", "habit__sort_order", "habit__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "checked_on"],
                name="rpg_habit_checkin_unique_habit_day",
            ),
            models.CheckConstraint(
                condition=Q(value__gte=0),
                name="rpg_habit_checkin_value_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.habit} on {self.checked_on}"

    def clean(self) -> None:
        if self.value is not None and self.value < 0:
            raise ValidationError({"value": "Check-in value cannot be negative."})

    def is_completed(self) -> bool:
        return self.value >= self.habit.target_value


class HabitMilestone(models.Model):
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="milestones",
    )
    title = models.CharField(max_length=160)
    streak_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["streak_days", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["habit", "streak_days"],
                name="rpg_habit_milestone_unique_habit_days",
            ),
            models.UniqueConstraint(
                fields=["streak_days"],
                condition=Q(habit__isnull=True),
                name="rpg_habit_milestone_unique_global_days",
            ),
            models.CheckConstraint(
                condition=Q(streak_days__gt=0),
                name="rpg_habit_milestone_streak_days_gt_0",
            ),
        ]

    def __str__(self) -> str:
        if self.habit_id:
            return f"{self.title} ({self.habit})"
        return f"{self.title} (global)"

    def clean(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValidationError({"title": "Milestone title cannot be empty."})
        if self.streak_days is not None and self.streak_days <= 0:
            raise ValidationError(
                {"streak_days": "Streak days must be greater than 0."}
            )
        if self.habit_id is None and self.streak_days:
            duplicate_global = HabitMilestone.objects.filter(
                habit__isnull=True,
                streak_days=self.streak_days,
            )
            if self.pk:
                duplicate_global = duplicate_global.exclude(pk=self.pk)
            if duplicate_global.exists():
                raise ValidationError(
                    {
                        "streak_days": (
                            "A global milestone with this streak length already exists."
                        )
                    }
                )

    def reward_xp_total(self) -> int:
        total = self.rewards.aggregate(total=Sum("xp_amount"))["total"]
        return int(total or 0)


class HabitMilestoneReward(models.Model):
    milestone = models.ForeignKey(
        HabitMilestone,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.CASCADE,
        related_name="habit_milestone_rewards",
    )
    xp_amount = models.PositiveIntegerField()

    class Meta:
        ordering = ["milestone__streak_days", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "skill"],
                name="rpg_habit_milestone_reward_unique_milestone_skill",
            ),
            models.CheckConstraint(
                condition=Q(xp_amount__gt=0),
                name="rpg_habit_milestone_reward_xp_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.milestone} -> {self.skill} (+{self.xp_amount} XP)"

    def clean(self) -> None:
        if self.xp_amount is not None and self.xp_amount <= 0:
            raise ValidationError({"xp_amount": "XP amount must be greater than 0."})


class HabitMilestoneUnlock(models.Model):
    milestone = models.ForeignKey(
        HabitMilestone,
        on_delete=models.CASCADE,
        related_name="unlocks",
    )
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name="milestone_unlocks",
    )
    unlocked_at = models.DateTimeField(default=timezone.now)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    streak_days = models.PositiveIntegerField()
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-unlocked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["milestone", "habit"],
                name="rpg_habit_milestone_unlock_unique_milestone_habit",
            ),
            models.CheckConstraint(
                condition=Q(streak_days__gt=0),
                name="rpg_habit_milestone_unlock_streak_days_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.habit} unlocked {self.milestone}"

    def clean(self) -> None:
        if self.streak_days is not None and self.streak_days <= 0:
            raise ValidationError(
                {"streak_days": "Streak days must be greater than 0."}
            )
        if (
            self.milestone_id
            and self.habit_id
            and self.milestone.habit_id is not None
            and self.milestone.habit_id != self.habit_id
        ):
            raise ValidationError(
                {
                    "milestone": (
                        "Habit-specific milestone must match the unlocked habit."
                    )
                }
            )


class Goal(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=GoalStatus.choices,
        default=GoalStatus.DRAFT,
    )
    priority = models.CharField(
        max_length=20,
        choices=GoalPriority.choices,
        default=GoalPriority.NORMAL,
    )
    life_area = models.ForeignKey(
        "skills.LifeArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goals",
    )
    target_value = models.PositiveIntegerField(default=1)
    progress_value = models.PositiveIntegerField(default=0)
    target_unit = models.CharField(
        max_length=20,
        choices=TargetUnit.choices,
        default=TargetUnit.COUNT,
    )
    starts_on = models.DateField(null=True, blank=True)
    due_on = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(
        max_length=20,
        choices=CreationSource.choices,
        default=CreationSource.MANUAL,
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "due_on", "title"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_goal_title_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(target_value__gt=0),
                name="rpg_goal_target_value_gt_0",
            ),
            models.CheckConstraint(
                condition=Q(progress_value__gte=0),
                name="rpg_goal_progress_value_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(progress_value__lte=models.F("target_value")),
                name="rpg_goal_progress_lte_target",
            ),
            models.CheckConstraint(
                condition=(
                    Q(due_on__isnull=True)
                    | Q(starts_on__isnull=True)
                    | Q(due_on__gte=models.F("starts_on"))
                ),
                name="rpg_goal_due_on_gte_starts_on",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.title:
            raise ValidationError({"title": "Goal title cannot be empty."})
        if self.target_value is not None and self.target_value <= 0:
            raise ValidationError(
                {"target_value": "Target value must be greater than 0."}
            )
        if self.progress_value is not None and self.progress_value < 0:
            raise ValidationError(
                {"progress_value": "Progress value cannot be negative."}
            )
        if (
            self.progress_value is not None
            and self.target_value is not None
            and self.progress_value > self.target_value
        ):
            raise ValidationError(
                {"progress_value": "Progress value cannot exceed target value."}
            )
        if self.starts_on and self.due_on and self.due_on < self.starts_on:
            raise ValidationError({"due_on": "Due on cannot be before starts on."})
        if self.completed_at and self.status != GoalStatus.COMPLETED:
            raise ValidationError(
                {"status": "Completed goals must use completed status."}
            )
        if self.archived_at and self.status != GoalStatus.ARCHIVED:
            raise ValidationError({"status": "Archived goals must use archived status."})
        if self.created_by == CreationSource.AI and self.status != GoalStatus.DRAFT:
            raise ValidationError({"status": "AI-created goals must start as draft."})

    def progress_percent(self) -> int:
        if self.target_value <= 0:
            return 0
        return min(100, int((self.progress_value / self.target_value) * 100))

    def is_complete(self) -> bool:
        return self.status == GoalStatus.COMPLETED


class GoalSkill(models.Model):
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="goal_skills",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.CASCADE,
        related_name="goals",
    )
    weight = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["goal__sort_order", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["goal", "skill"],
                name="rpg_goal_skill_unique_goal_skill",
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0),
                name="rpg_goal_skill_weight_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.goal} -> {self.skill}"

    def clean(self) -> None:
        if self.weight is not None and self.weight <= 0:
            raise ValidationError({"weight": "Weight must be greater than 0."})


class GoalProgressEntry(models.Model):
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    previous_value = models.PositiveIntegerField()
    new_value = models.PositiveIntegerField()
    delta = models.IntegerField()
    note = models.TextField(blank=True)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(previous_value__gte=0),
                name="rpg_goal_progress_previous_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(new_value__gte=0),
                name="rpg_goal_progress_new_gte_0",
            ),
            models.UniqueConstraint(
                fields=["goal", "source_type", "source_id"],
                condition=~Q(source_type="") & Q(source_id__isnull=False),
                name="rpg_goal_progress_unique_source",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.goal}: {self.previous_value} -> {self.new_value}"

    def clean(self) -> None:
        self.note = self.note.strip()
        self.source_type = self.source_type.strip()
        if self.previous_value is not None and self.previous_value < 0:
            raise ValidationError(
                {"previous_value": "Previous value cannot be negative."}
            )
        if self.new_value is not None and self.new_value < 0:
            raise ValidationError({"new_value": "New value cannot be negative."})
        if self.goal_id and self.new_value is not None and self.new_value > self.goal.target_value:
            raise ValidationError({"new_value": "New value cannot exceed target value."})
        if self.delta != self.new_value - self.previous_value:
            raise ValidationError({"delta": "Delta must match the value change."})
        if self.source_type and self.source_id is None:
            raise ValidationError({"source_id": "Source id is required for source type."})
        if self.source_id is not None and not self.source_type:
            raise ValidationError({"source_type": "Source type is required for source id."})


class Challenge(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ChallengeStatus.choices,
        default=ChallengeStatus.DRAFT,
    )
    cadence = models.CharField(
        max_length=20,
        choices=ChallengeCadence.choices,
        default=ChallengeCadence.DAILY,
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="challenges",
    )
    target_value = models.PositiveIntegerField(default=30)
    target_unit = models.CharField(
        max_length=20,
        choices=TargetUnit.choices,
        default=TargetUnit.CHECK,
    )
    current_value = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    xp_awarded_at = models.DateTimeField(null=True, blank=True)
    reward_title = models.CharField(max_length=180, blank=True)
    created_by = models.CharField(
        max_length=20,
        choices=CreationSource.choices,
        default=CreationSource.MANUAL,
    )
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "end_date", "-created_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_challenge_title_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(target_value__gt=0),
                name="rpg_challenge_target_value_gt_0",
            ),
            models.CheckConstraint(
                condition=Q(current_value__gte=0),
                name="rpg_challenge_current_value_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(current_value__lte=models.F("target_value")),
                name="rpg_challenge_current_lte_target",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="rpg_challenge_end_gte_start",
            ),
            models.CheckConstraint(
                condition=Q(completed_at__isnull=True) | Q(failed_at__isnull=True),
                name="rpg_challenge_not_completed_and_failed",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.reward_title = self.reward_title.strip()
        if not self.title:
            raise ValidationError({"title": "Challenge title cannot be empty."})
        if self.target_value is not None and self.target_value <= 0:
            raise ValidationError(
                {"target_value": "Target value must be greater than 0."}
            )
        if self.current_value is not None and self.current_value < 0:
            raise ValidationError(
                {"current_value": "Current value cannot be negative."}
            )
        if (
            self.current_value is not None
            and self.target_value is not None
            and self.current_value > self.target_value
        ):
            raise ValidationError(
                {"current_value": "Current value cannot exceed target value."}
            )
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        if self.completed_at and self.status != ChallengeStatus.COMPLETED:
            raise ValidationError(
                {"status": "Completed challenges must use completed status."}
            )
        if self.failed_at and self.status != ChallengeStatus.FAILED:
            raise ValidationError({"status": "Failed challenges must use failed status."})
        if self.completed_at and self.failed_at:
            raise ValidationError(
                {"status": "Challenge cannot be completed and failed at once."}
            )
        if self.xp_awarded_at and not self.completed_at:
            raise ValidationError({"xp_awarded_at": "XP can be awarded only after completion."})
        if self.created_by == CreationSource.AI and self.status != ChallengeStatus.DRAFT:
            raise ValidationError(
                {"status": "AI-created challenges must start as draft."}
            )

    def progress_percent(self) -> int:
        if self.target_value <= 0:
            return 0
        return min(100, int((self.current_value / self.target_value) * 100))

    def reward_xp_total(self) -> int:
        total = self.rewards.aggregate(total=Sum("xp_amount"))["total"]
        return int(total or 0)

    def total_days(self) -> int:
        return max((self.end_date - self.start_date).days + 1, 1)

    def current_day(self, day: date | None = None) -> int:
        selected_day = day or timezone.localdate()
        if selected_day < self.start_date:
            return 0
        return min((selected_day - self.start_date).days + 1, self.total_days())


class ChallengeReward(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.CASCADE,
        related_name="challenge_rewards",
    )
    xp_amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["challenge__title", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "skill"],
                name="rpg_challenge_reward_unique_challenge_skill",
            ),
            models.CheckConstraint(
                condition=Q(xp_amount__gt=0),
                name="rpg_challenge_reward_xp_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.challenge} -> {self.skill} (+{self.xp_amount} XP)"

    def clean(self) -> None:
        if self.xp_amount is not None and self.xp_amount <= 0:
            raise ValidationError({"xp_amount": "XP amount must be greater than 0."})


class ChallengeCheckIn(models.Model):
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    checked_on = models.DateField()
    value = models.PositiveIntegerField(default=1)
    successful = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checked_on", "challenge__sort_order", "challenge__title"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "checked_on"],
                name="rpg_challenge_checkin_unique_challenge_day",
            ),
            models.CheckConstraint(
                condition=Q(value__gte=0),
                name="rpg_challenge_checkin_value_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.challenge} on {self.checked_on}"

    def clean(self) -> None:
        self.note = self.note.strip()
        if self.value is not None and self.value < 0:
            raise ValidationError({"value": "Check-in value cannot be negative."})
        if self.successful and self.value <= 0:
            raise ValidationError(
                {"value": "Successful check-in value must be greater than 0."}
            )
        if self.challenge_id and self.checked_on:
            if self.checked_on < self.challenge.start_date or self.checked_on > self.challenge.end_date:
                raise ValidationError(
                    {"checked_on": "Check-in date must be inside challenge range."}
                )


class Achievement(models.Model):
    code = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    rarity = models.CharField(
        max_length=20,
        choices=AchievementRarity.choices,
        default=AchievementRarity.COMMON,
    )
    trigger_type = models.CharField(
        max_length=40,
        choices=AchievementTrigger.choices,
        default=AchievementTrigger.MANUAL,
    )
    trigger_config = models.JSONField(default=dict, blank=True)
    icon = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(code=""),
                name="rpg_achievement_code_not_empty",
            ),
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_achievement_title_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.icon = self.icon.strip()
        self.code = self.code.strip() or slugify(self.title)[:80]
        if not self.title:
            raise ValidationError({"title": "Achievement title cannot be empty."})
        if not self.code:
            raise ValidationError({"code": "Achievement code cannot be empty."})
        if not isinstance(self.trigger_config, dict):
            raise ValidationError({"trigger_config": "Trigger config must be an object."})
        _validate_achievement_trigger_config(self.trigger_type, self.trigger_config)


class AchievementUnlock(models.Model):
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="unlocks",
    )
    unlocked_at = models.DateTimeField(default=timezone.now)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-unlocked_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["achievement"],
                name="rpg_achievement_unlock_unique_achievement",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.achievement} unlocked"

    def clean(self) -> None:
        self.source_type = self.source_type.strip()
        self.note = self.note.strip()
        if self.source_id is not None and not self.source_type:
            raise ValidationError({"source_type": "Source type is required for source id."})
        if not isinstance(self.snapshot, dict):
            raise ValidationError({"snapshot": "Snapshot must be an object."})


class JournalEntry(models.Model):
    title = models.CharField(max_length=180)
    content = models.TextField(blank=True)
    entry_type = models.CharField(
        max_length=30,
        choices=JournalEntryType.choices,
        default=JournalEntryType.MANUAL,
    )
    mood = models.CharField(
        max_length=40,
        choices=JournalMood.choices,
        blank=True,
    )
    reflection_proud = models.TextField(blank=True)
    reflection_challenge = models.TextField(blank=True)
    reflection_learned = models.TextField(blank=True)
    reflection_improve = models.TextField(blank=True)
    reflection_goal_action = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    entry_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date", "-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_journal_entry_title_not_empty",
            ),
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                condition=~Q(source_type="") & Q(source_id__isnull=False),
                name="rpg_journal_entry_unique_source",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.content = self.content.strip()
        self.mood = self.mood.strip()
        self.reflection_proud = self.reflection_proud.strip()
        self.reflection_challenge = self.reflection_challenge.strip()
        self.reflection_learned = self.reflection_learned.strip()
        self.reflection_improve = self.reflection_improve.strip()
        self.reflection_goal_action = self.reflection_goal_action.strip()
        self.source_type = self.source_type.strip()
        self.tags = _normalize_tags(self.tags)
        if not self.title:
            raise ValidationError({"title": "Journal entry title cannot be empty."})

    def word_count(self) -> int:
        reflection_text = " ".join(
            (
                self.reflection_proud,
                self.reflection_challenge,
                self.reflection_learned,
                self.reflection_improve,
                self.reflection_goal_action,
            )
        )
        return len(f"{self.content} {reflection_text}".split())


class CharacterIdentity(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    started_on = models.DateField(default=timezone.localdate)
    ended_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-started_on", "-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="rpg_character_identity_title_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True) | Q(ended_on__gte=models.F("started_on")),
                name="rpg_character_identity_end_gte_start",
            ),
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="rpg_character_identity_single_active",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        if not self.title:
            raise ValidationError({"title": "Character identity title cannot be empty."})
        if self.ended_on and self.ended_on < self.started_on:
            raise ValidationError(
                {"ended_on": "Ended on cannot be before started on."}
            )


def _normalize_tags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValidationError({"tags": "Tags must be a list of strings."})

    tags: list[str] = []
    for raw_tag in value:
        if not isinstance(raw_tag, str):
            raise ValidationError({"tags": "Tags must be a list of strings."})
        tag = raw_tag.strip().lower()
        if tag.startswith("#"):
            tag = tag[1:]
        tag = "-".join(part for part in tag.split() if part)
        if tag and tag not in tags:
            tags.append(tag[:40])
    return tags


def _validate_achievement_trigger_config(
    trigger_type: str,
    trigger_config: dict[str, object],
) -> None:
    def require_positive_int(key: str) -> None:
        value = trigger_config.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValidationError(
                {"trigger_config": f"{key} must be a positive integer."}
            )

    def optional_positive_int(key: str) -> None:
        if key not in trigger_config or trigger_config.get(key) in (None, ""):
            return
        require_positive_int(key)

    if trigger_type == AchievementTrigger.MANUAL:
        return
    if trigger_type == AchievementTrigger.TOTAL_XP:
        require_positive_int("xp")
        return
    if trigger_type == AchievementTrigger.SKILL_LEVEL:
        require_positive_int("skill_id")
        require_positive_int("level")
        return
    if trigger_type == AchievementTrigger.QUEST_COUNT:
        require_positive_int("quest_count")
        period = trigger_config.get("period", "all_time")
        if period not in ("all_time", "day", "week", "month"):
            raise ValidationError(
                {"trigger_config": "period must be all_time, day, week, or month."}
            )
        return
    if trigger_type == AchievementTrigger.HABIT_STREAK:
        optional_positive_int("habit_id")
        require_positive_int("streak_days")
        return
    if trigger_type == AchievementTrigger.CHALLENGE_COMPLETED:
        optional_positive_int("challenge_id")
        return
    if trigger_type == AchievementTrigger.GOAL_COMPLETED:
        optional_positive_int("goal_id")
        return
    if trigger_type == AchievementTrigger.JOURNAL_STREAK:
        require_positive_int("streak_days")
