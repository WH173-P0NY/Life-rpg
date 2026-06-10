from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from .models import CalendarEvent, CalendarEventType, CalendarRecurrenceFrequency

MAX_RECURRENCE_OCCURRENCES = 366


def create_calendar_event(
    *,
    title: str,
    start_at: datetime,
    end_at: datetime,
    description: str = "",
    all_day: bool = False,
    location: str = "",
    event_type: str = CalendarEventType.PERSONAL,
    source_type: str = "",
    source_id: int | None = None,
    recurrence_frequency: str = CalendarRecurrenceFrequency.NONE,
    recurrence_until: date | None = None,
) -> CalendarEvent:
    clean_frequency = recurrence_frequency or CalendarRecurrenceFrequency.NONE
    if clean_frequency == CalendarRecurrenceFrequency.NONE:
        events = [
            _build_calendar_event(
                title=title,
                description=description,
                start_at=start_at,
                end_at=end_at,
                all_day=all_day,
                location=location,
                event_type=event_type,
                source_type=source_type,
                source_id=source_id,
                recurrence_frequency=CalendarRecurrenceFrequency.NONE,
                recurrence_until=None,
                recurrence_group=None,
                recurrence_index=0,
            )
        ]
    else:
        if recurrence_until is None:
            raise ValueError("recurrence_until is required for recurring events.")
        events = _build_recurring_events(
            title=title,
            description=description,
            start_at=start_at,
            end_at=end_at,
            all_day=all_day,
            location=location,
            event_type=event_type,
            source_type=source_type,
            source_id=source_id,
            recurrence_frequency=clean_frequency,
            recurrence_until=recurrence_until,
        )

    for event in events:
        _validate_event(event)
    with transaction.atomic():
        for event in events:
            event.save()
    first_event = events[0]
    first_event._created_events_count = len(events)
    return first_event


def update_calendar_event(event: CalendarEvent, **changes: Any) -> CalendarEvent:
    allowed_fields = {
        "title",
        "description",
        "start_at",
        "end_at",
        "all_day",
        "location",
        "event_type",
        "source_type",
        "source_id",
        "recurrence_frequency",
        "recurrence_until",
        "recurrence_group",
        "recurrence_index",
    }
    for field, value in changes.items():
        if field in allowed_fields:
            setattr(event, field, value)
    _validate_event(event)
    event.save()
    return event


def get_calendar_events(
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> QuerySet[CalendarEvent]:
    events = CalendarEvent.objects.all()
    if start_at is not None:
        events = events.filter(end_at__gte=start_at)
    if end_at is not None:
        events = events.filter(start_at__lte=end_at)
    return events.order_by("start_at", "end_at", "title")


def serialize_calendar_event(event: CalendarEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "start_at": event.start_at.isoformat(),
        "end_at": event.end_at.isoformat(),
        "all_day": event.all_day,
        "location": event.location,
        "event_type": event.event_type,
        "source_type": event.source_type,
        "source_id": event.source_id,
        "recurrence_frequency": event.recurrence_frequency,
        "recurrence_until": (
            event.recurrence_until.isoformat() if event.recurrence_until else None
        ),
        "recurrence_group": str(event.recurrence_group) if event.recurrence_group else None,
        "recurrence_index": event.recurrence_index,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
    }


def _build_recurring_events(
    *,
    title: str,
    start_at: datetime,
    end_at: datetime,
    recurrence_frequency: str,
    recurrence_until: date,
    description: str,
    all_day: bool,
    location: str,
    event_type: str,
    source_type: str,
    source_id: int | None,
) -> list[CalendarEvent]:
    if recurrence_until < start_at.date():
        raise ValueError("recurrence_until cannot be before start_at.")

    group_id = uuid.uuid4()
    duration = end_at - start_at
    events: list[CalendarEvent] = []
    cursor = start_at
    index = 0
    while cursor.date() <= recurrence_until:
        if index >= MAX_RECURRENCE_OCCURRENCES:
            raise ValueError(
                f"Recurring events are limited to {MAX_RECURRENCE_OCCURRENCES} occurrences."
            )
        events.append(
            _build_calendar_event(
                title=title,
                description=description,
                start_at=cursor,
                end_at=cursor + duration,
                all_day=all_day,
                location=location,
                event_type=event_type,
                source_type=source_type,
                source_id=source_id,
                recurrence_frequency=recurrence_frequency,
                recurrence_until=recurrence_until,
                recurrence_group=group_id,
                recurrence_index=index,
            )
        )
        cursor = _next_occurrence(cursor, recurrence_frequency)
        index += 1

    return events


def _build_calendar_event(
    *,
    title: str,
    start_at: datetime,
    end_at: datetime,
    description: str,
    all_day: bool,
    location: str,
    event_type: str,
    source_type: str,
    source_id: int | None,
    recurrence_frequency: str,
    recurrence_until: date | None,
    recurrence_group: uuid.UUID | None,
    recurrence_index: int,
) -> CalendarEvent:
    return CalendarEvent(
        title=title,
        description=description,
        start_at=start_at,
        end_at=end_at,
        all_day=all_day,
        location=location,
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        recurrence_frequency=recurrence_frequency,
        recurrence_until=recurrence_until,
        recurrence_group=recurrence_group,
        recurrence_index=recurrence_index,
    )


def _next_occurrence(value: datetime, recurrence_frequency: str) -> datetime:
    if recurrence_frequency == CalendarRecurrenceFrequency.DAILY:
        return value + timedelta(days=1)
    if recurrence_frequency == CalendarRecurrenceFrequency.WEEKLY:
        return value + timedelta(weeks=1)
    if recurrence_frequency == CalendarRecurrenceFrequency.MONTHLY:
        return _add_month(value)
    raise ValueError("recurrence_frequency must be one of none, daily, weekly, monthly.")


def _add_month(value: datetime) -> datetime:
    next_month = value.month + 1
    year = value.year + ((next_month - 1) // 12)
    month = ((next_month - 1) % 12) + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _validate_event(event: CalendarEvent) -> None:
    try:
        event.full_clean()
    except ValidationError as exc:
        raise ValueError(_validation_error_message(exc)) from exc


def _validation_error_message(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        messages: list[str] = []
        for field_messages in error.message_dict.values():
            messages.extend(str(message) for message in field_messages)
        return " ".join(messages)
    return " ".join(str(message) for message in error.messages)
