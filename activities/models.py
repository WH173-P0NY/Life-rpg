from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum


class ActivityDefinition(models.Model):
    name = models.CharField(max_length=160, unique=True)
    life_area = models.ForeignKey(
        "skills.LifeArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_definitions",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Activity definition name cannot be empty."})


class ActivityReward(models.Model):
    activity_definition = models.ForeignKey(
        ActivityDefinition,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    skill = models.ForeignKey(
        "skills.Skill",
        on_delete=models.CASCADE,
        related_name="activity_rewards",
    )
    xp_per_minute = models.PositiveIntegerField()

    class Meta:
        ordering = ["activity_definition__name", "skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["activity_definition", "skill"],
                name="activities_reward_unique_activity_skill",
            ),
            models.CheckConstraint(
                condition=Q(xp_per_minute__gt=0),
                name="activities_reward_xp_per_minute_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.activity_definition} -> {self.skill} "
            f"({self.xp_per_minute} XP/min)"
        )

    def clean(self) -> None:
        if self.xp_per_minute <= 0:
            raise ValidationError(
                {"xp_per_minute": "XP per minute must be greater than 0."}
            )


class ActivityRule(models.Model):
    pattern = models.CharField(max_length=160)
    activity_definition = models.ForeignKey(
        ActivityDefinition,
        on_delete=models.CASCADE,
        related_name="rules",
    )

    class Meta:
        ordering = ["pattern"]

    def __str__(self) -> str:
        return f"{self.pattern} -> {self.activity_definition}"

    def clean(self) -> None:
        self.pattern = self.pattern.strip()
        if not self.pattern:
            raise ValidationError({"pattern": "Pattern cannot be empty."})


class ActivityEntry(models.Model):
    activity_definition = models.ForeignKey(
        ActivityDefinition,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    source = models.CharField(max_length=240, blank=True, default="manual")
    minutes = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(minutes__gt=0),
                name="activities_entry_minutes_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.activity_definition} ({self.minutes} min)"

    def clean(self) -> None:
        self.source = self.source.strip() or "manual"
        if self.minutes <= 0:
            raise ValidationError({"minutes": "Minutes must be greater than 0."})

    def total_xp(self) -> int:
        total = self.xp_events.aggregate(total=Sum("amount"))["total"]
        return int(total or 0)
