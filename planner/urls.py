from __future__ import annotations

from django.urls import URLPattern, path

from . import views

app_name = "planner"
urlpatterns: list[URLPattern] = [
    path("calendar/events/", views.calendar_events_api, name="calendar_events"),
    path(
        "calendar/events/<int:event_id>/",
        views.calendar_event_detail_api,
        name="calendar_event_detail",
    ),
]
