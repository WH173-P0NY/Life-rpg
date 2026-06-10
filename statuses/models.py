from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StatusDefinition(models.Model):
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
            raise ValidationError({"name": "Status name cannot be empty."})


class StatusEntry(models.Model):
    status_definition = models.ForeignKey(
        StatusDefinition,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    value = models.PositiveSmallIntegerField()
    note = models.TextField(blank=True)
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(value__gte=0, value__lte=100),
                name="statuses_entry_value_0_100",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.status_definition}: {self.value}"

    def clean(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValidationError({"value": "Status value must be between 0 and 100."})
