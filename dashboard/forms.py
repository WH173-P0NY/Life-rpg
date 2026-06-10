from __future__ import annotations

from django import forms
from django.utils import timezone

from activities.models import ActivityDefinition


class ManualActivityForm(forms.Form):
    activity_definition = forms.ModelChoiceField(
        queryset=ActivityDefinition.objects.order_by("name"),
        label="Activity",
        empty_label="Choose activity",
    )
    minutes = forms.IntegerField(label="Minutes", min_value=1)
    started_at = forms.DateTimeField(
        label="Started at",
        input_formats=("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    source = forms.CharField(label="Source", max_length=240, required=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        now = timezone.localtime(timezone.now()).replace(second=0, microsecond=0)
        self.fields["started_at"].initial = now.strftime("%Y-%m-%dT%H:%M")
        for field in self.fields.values():
            css = "w-full rounded border border-slate-300 px-3 py-2 text-sm"
            field.widget.attrs["class"] = css
