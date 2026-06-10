from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


class LlmProvider(models.TextChoices):
    CHATGPT = "chatgpt", "ChatGPT"
    CLAUDE = "claude", "Claude"
    GEMINI = "gemini", "Gemini"


class LlmProviderConfig(models.Model):
    provider = models.CharField(
        max_length=20,
        choices=LlmProvider.choices,
        unique=True,
    )
    model_name = models.CharField(max_length=120, blank=True)
    api_key = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider"]

    def __str__(self) -> str:
        return self.get_provider_display()

    def clean(self) -> None:
        self.model_name = self.model_name.strip()
        self.api_key = self.api_key.strip()
        if self.is_enabled and not self.model_name:
            raise ValidationError({"model_name": "Model name is required when enabled."})
