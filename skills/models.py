from __future__ import annotations

from math import floor, sqrt
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

if TYPE_CHECKING:
    from activities.models import ActivityEntry


def xp_required_for_level(level: int) -> int:
    """Return the total XP required to reach a level."""
    if level <= 1:
        return 0
    return 100 * (level - 1) ** 2


def calculate_level(total_xp: int) -> int:
    """Calculate a balanced RPG level from total XP."""
    return max(1, floor(sqrt(max(total_xp, 0) / 100)) + 1)


def progress_for_xp(total_xp: int) -> dict[str, int]:
    current_level = calculate_level(total_xp)
    current_level_xp = xp_required_for_level(current_level)
    next_level_xp = xp_required_for_level(current_level + 1)
    xp_in_level = max(total_xp - current_level_xp, 0)
    xp_needed_for_level = max(next_level_xp - current_level_xp, 1)
    percent = min(100, floor((xp_in_level / xp_needed_for_level) * 100))

    return {
        "level": current_level,
        "current_level_xp": current_level_xp,
        "next_level_xp": next_level_xp,
        "xp_in_level": xp_in_level,
        "xp_needed_for_level": xp_needed_for_level,
        "percent": percent,
    }


class LifeArea(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Life area name cannot be empty."})


class Skill(models.Model):
    name = models.CharField(max_length=120, unique=True)
    life_area = models.ForeignKey(
        LifeArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skills",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Skill name cannot be empty."})

    def get_total_xp(self) -> int:
        total = self.xp_events.aggregate(total=Sum("amount"))["total"]
        return int(total or 0)

    def get_level(self) -> int:
        return calculate_level(self.get_total_xp())

    def get_progress_to_next_level(self) -> dict[str, int]:
        return progress_for_xp(self.get_total_xp())

    def add_xp(
        self,
        amount: int,
        source_type: str,
        note: str = "",
        activity_entry: ActivityEntry | None = None,
    ) -> "XpEvent":
        if amount <= 0:
            raise ValueError("XP amount must be greater than 0.")
        source_type = source_type.strip()
        if not source_type:
            raise ValueError("XP source_type cannot be empty.")

        return XpEvent.objects.create(
            skill=self,
            amount=amount,
            source_type=source_type,
            note=note,
            activity_entry=activity_entry,
            earned_at=activity_entry.started_at if activity_entry else timezone.now(),
        )


class XpEvent(models.Model):
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="xp_events",
    )
    amount = models.PositiveIntegerField()
    source_type = models.CharField(max_length=40)
    activity_entry = models.ForeignKey(
        "activities.ActivityEntry",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="xp_events",
    )
    note = models.TextField(blank=True)
    earned_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-earned_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="skills_xpevent_amount_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.skill} +{self.amount} XP"

    def clean(self) -> None:
        self.source_type = self.source_type.strip()
        if self.amount <= 0:
            raise ValidationError({"amount": "XP amount must be greater than 0."})
        if not self.source_type:
            raise ValidationError({"source_type": "Source type cannot be empty."})
