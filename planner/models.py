from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class CalendarEventType(models.TextChoices):
    PERSONAL = "personal", "Personal"
    WORK = "work", "Work"
    RPG = "rpg", "RPG"
    HEALTH = "health", "Health"
    FINANCE = "finance", "Finance"


class CalendarRecurrenceFrequency(models.TextChoices):
    NONE = "none", "None"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class CalendarEvent(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=180, blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=CalendarEventType.choices,
        default=CalendarEventType.PERSONAL,
    )
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    recurrence_frequency = models.CharField(
        max_length=20,
        choices=CalendarRecurrenceFrequency.choices,
        default=CalendarRecurrenceFrequency.NONE,
    )
    recurrence_until = models.DateField(null=True, blank=True)
    recurrence_group = models.UUIDField(null=True, blank=True, db_index=True)
    recurrence_index = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at", "end_at", "title"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="planner_calendar_event_title_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(end_at__gte=models.F("start_at")),
                name="planner_calendar_event_end_gte_start",
            ),
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                condition=~Q(source_type="") & Q(source_id__isnull=False),
                name="planner_calendar_event_unique_source",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.location = self.location.strip()
        self.source_type = self.source_type.strip()
        if not self.title:
            raise ValidationError({"title": "Calendar event title cannot be empty."})
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValidationError({"end_at": "End time cannot be before start time."})
        if (
            self.recurrence_frequency != CalendarRecurrenceFrequency.NONE
            and not self.recurrence_until
        ):
            raise ValidationError(
                {"recurrence_until": "Recurrence end date is required."}
            )
        if (
            self.recurrence_frequency != CalendarRecurrenceFrequency.NONE
            and self.recurrence_until
            and self.start_at
            and self.recurrence_until < self.start_at.date()
        ):
            raise ValidationError(
                {"recurrence_until": "Recurrence end date cannot be before start date."}
            )
