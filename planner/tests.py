from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CalendarEvent, CalendarEventType, CalendarRecurrenceFrequency
from .services import create_calendar_event, get_calendar_events


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour=hour, minute=minute)))


class CalendarEventModelTests(TestCase):
    def test_event_rejects_empty_title(self) -> None:
        event = CalendarEvent(
            title="  ",
            start_at=_at(date(2026, 6, 10), 9),
            end_at=_at(date(2026, 6, 10), 10),
        )

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_event_rejects_end_before_start(self) -> None:
        event = CalendarEvent(
            title="Invalid",
            start_at=_at(date(2026, 6, 10), 10),
            end_at=_at(date(2026, 6, 10), 9),
        )

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_recurring_event_rejects_until_before_start(self) -> None:
        event = CalendarEvent(
            title="Invalid recurrence",
            start_at=_at(date(2026, 6, 10), 9),
            end_at=_at(date(2026, 6, 10), 10),
            recurrence_frequency=CalendarRecurrenceFrequency.WEEKLY,
            recurrence_until=date(2026, 6, 9),
        )

        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_event_source_pair_is_unique_when_source_id_is_set(self) -> None:
        CalendarEvent.objects.create(
            title="Seed event",
            start_at=_at(date(2026, 6, 10), 9),
            end_at=_at(date(2026, 6, 10), 10),
            source_type="seed",
            source_id=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CalendarEvent.objects.create(
                    title="Duplicate seed event",
                    start_at=_at(date(2026, 6, 10), 11),
                    end_at=_at(date(2026, 6, 10), 12),
                    source_type="seed",
                    source_id=1,
                )


class CalendarEventServiceTests(TestCase):
    def test_create_calendar_event(self) -> None:
        event = create_calendar_event(
            title="Project planning",
            description="Plan the next RPG modules.",
            start_at=_at(date(2026, 6, 10), 9),
            end_at=_at(date(2026, 6, 10), 10),
            event_type=CalendarEventType.WORK,
        )

        self.assertEqual(event.title, "Project planning")
        self.assertEqual(event.event_type, CalendarEventType.WORK)

    def test_get_calendar_events_returns_events_overlapping_range(self) -> None:
        day = date(2026, 6, 10)
        visible = create_calendar_event(
            title="Visible",
            start_at=_at(day, 9),
            end_at=_at(day, 10),
        )
        create_calendar_event(
            title="Outside",
            start_at=_at(day + timedelta(days=2), 9),
            end_at=_at(day + timedelta(days=2), 10),
        )

        events = list(
            get_calendar_events(
                start_at=_at(day, 0),
                end_at=_at(day, 23, 59),
            )
        )

        self.assertEqual(events, [visible])

    def test_create_calendar_event_materializes_weekly_recurrence(self) -> None:
        first = create_calendar_event(
            title="Training",
            start_at=_at(date(2026, 6, 10), 18),
            end_at=_at(date(2026, 6, 10), 19),
            recurrence_frequency=CalendarRecurrenceFrequency.WEEKLY,
            recurrence_until=date(2026, 7, 1),
        )

        events = list(CalendarEvent.objects.order_by("start_at"))

        self.assertEqual(getattr(first, "_created_events_count"), 4)
        self.assertEqual(len(events), 4)
        self.assertIsNotNone(events[0].recurrence_group)
        self.assertEqual(
            {event.recurrence_group for event in events},
            {events[0].recurrence_group},
        )
        self.assertEqual([event.recurrence_index for event in events], [0, 1, 2, 3])
        self.assertEqual([event.start_at.date() for event in events], [
            date(2026, 6, 10),
            date(2026, 6, 17),
            date(2026, 6, 24),
            date(2026, 7, 1),
        ])


class CalendarEventApiTests(TestCase):
    def test_calendar_events_endpoint_creates_event(self) -> None:
        response = self.client.post(
            reverse("planner:calendar_events"),
            data=json.dumps(
                {
                    "title": "Deep work",
                    "description": "Build calendar MVP",
                    "start_at": "2026-06-10T09:00",
                    "end_at": "2026-06-10T10:30",
                    "event_type": "work",
                    "location": "Home office",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["event"]
        self.assertEqual(payload["title"], "Deep work")
        self.assertEqual(payload["event_type"], "work")
        self.assertEqual(payload["location"], "Home office")
        self.assertEqual(CalendarEvent.objects.count(), 1)

    def test_calendar_events_endpoint_creates_recurring_event(self) -> None:
        response = self.client.post(
            reverse("planner:calendar_events"),
            data=json.dumps(
                {
                    "title": "Daily review",
                    "start_at": "2026-06-10T20:00",
                    "end_at": "2026-06-10T20:30",
                    "recurrence_frequency": "daily",
                    "recurrence_until": "2026-06-12",
                }
            ),
            content_type="application/json",
        )
        list_response = self.client.get(
            reverse("planner:calendar_events"),
            {
                "start": "2026-06-10T00:00",
                "end": "2026-06-12T23:59",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["events_created"], 3)
        self.assertEqual(CalendarEvent.objects.count(), 3)
        self.assertEqual(len(list_response.json()["events"]), 3)
        self.assertEqual(
            {event["recurrence_frequency"] for event in list_response.json()["events"]},
            {"daily"},
        )

    def test_calendar_events_endpoint_lists_range(self) -> None:
        event = create_calendar_event(
            title="Range event",
            start_at=_at(date(2026, 6, 10), 12),
            end_at=_at(date(2026, 6, 10), 13),
        )

        response = self.client.get(
            reverse("planner:calendar_events"),
            {
                "start": "2026-06-10T00:00",
                "end": "2026-06-10T23:59",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["events"][0]["id"], event.id)

    def test_calendar_events_endpoint_rejects_invalid_payload(self) -> None:
        response = self.client.post(
            reverse("planner:calendar_events"),
            data=json.dumps({"title": "Invalid", "start_at": "2026-06-10T10:00"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_calendar_event_detail_updates_and_deletes_event(self) -> None:
        event = create_calendar_event(
            title="Original",
            start_at=_at(date(2026, 6, 10), 9),
            end_at=_at(date(2026, 6, 10), 10),
        )

        update_response = self.client.patch(
            reverse("planner:calendar_event_detail", args=[event.id]),
            data=json.dumps({"title": "Updated", "event_type": "rpg"}),
            content_type="application/json",
        )
        delete_response = self.client.delete(
            reverse("planner:calendar_event_detail", args=[event.id])
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["event"]["title"], "Updated")
        self.assertEqual(update_response.json()["event"]["event_type"], "rpg")
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(CalendarEvent.objects.count(), 0)
