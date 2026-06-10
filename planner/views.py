from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from .models import CalendarEvent
from .services import (
    create_calendar_event,
    get_calendar_events,
    serialize_calendar_event,
    update_calendar_event,
)


@require_http_methods(["GET", "POST"])
def calendar_events_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        start_at = _optional_datetime(request.GET.get("start"))
        end_at = _optional_datetime(request.GET.get("end"))
        events = get_calendar_events(start_at=start_at, end_at=end_at)
        return JsonResponse(
            {"events": [serialize_calendar_event(event) for event in events]}
        )

    try:
        payload = _json_payload(request)
        event = create_calendar_event(
            title=_required_string(payload.get("title"), field_name="title"),
            description=_optional_string(payload.get("description")),
            start_at=_required_datetime(payload.get("start_at"), field_name="start_at"),
            end_at=_required_datetime(payload.get("end_at"), field_name="end_at"),
            all_day=_optional_bool(payload.get("all_day")),
            location=_optional_string(payload.get("location")),
            event_type=_optional_string(payload.get("event_type")) or "personal",
            recurrence_frequency=(
                _optional_string(payload.get("recurrence_frequency")) or "none"
            ),
            recurrence_until=_optional_date(payload.get("recurrence_until")),
        )
    except ValueError as exc:
        return _validation_error_response(str(exc))

    return JsonResponse(
        {
            "event": serialize_calendar_event(event),
            "events_created": getattr(event, "_created_events_count", 1),
        },
        status=201,
    )


@require_http_methods(["PATCH", "DELETE"])
def calendar_event_detail_api(request: HttpRequest, event_id: int) -> HttpResponse:
    event = get_object_or_404(CalendarEvent, pk=event_id)

    if request.method == "DELETE":
        event.delete()
        return HttpResponse(status=204)

    try:
        payload = _json_payload(request)
        changes: dict[str, Any] = {}
        if "title" in payload:
            changes["title"] = _required_string(payload.get("title"), field_name="title")
        if "description" in payload:
            changes["description"] = _optional_string(payload.get("description"))
        if "start_at" in payload:
            changes["start_at"] = _required_datetime(
                payload.get("start_at"),
                field_name="start_at",
            )
        if "end_at" in payload:
            changes["end_at"] = _required_datetime(payload.get("end_at"), field_name="end_at")
        if "all_day" in payload:
            changes["all_day"] = _optional_bool(payload.get("all_day"))
        if "location" in payload:
            changes["location"] = _optional_string(payload.get("location"))
        if "event_type" in payload:
            changes["event_type"] = _optional_string(payload.get("event_type")) or "personal"
        if "recurrence_frequency" in payload:
            changes["recurrence_frequency"] = (
                _optional_string(payload.get("recurrence_frequency")) or "none"
            )
        if "recurrence_until" in payload:
            changes["recurrence_until"] = _optional_date(payload.get("recurrence_until"))
        event = update_calendar_event(event, **changes)
    except ValueError as exc:
        return _validation_error_response(str(exc))

    return JsonResponse({"event": serialize_calendar_event(event)})


def _json_payload(request: HttpRequest) -> dict[str, Any]:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object.")
    return payload


def _optional_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return _required_datetime(value, field_name="datetime")


def _optional_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("Date fields must use ISO date format.")
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError("Date fields must use ISO date format.")
    return parsed


def _required_datetime(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} is required.")
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"{field_name} must use ISO datetime format.")
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed)
    return parsed


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Text fields must be strings.")
    return value


def _required_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    return value


def _optional_bool(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value
    raise ValueError("Boolean fields must be booleans.")


def _validation_error_response(message: str) -> JsonResponse:
    return JsonResponse(
        {
            "error": {
                "code": "validation_error",
                "message": message,
            }
        },
        status=400,
    )
