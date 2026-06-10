from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Sequence

from django.db.models import Sum
from django.utils import timezone

from activities.models import ActivityEntry
from rpg.services import (
    build_daily_quest_rows,
    build_habit_rows,
    build_journal_entry_rows,
    build_recent_achievement_rows,
    get_active_challenge,
    serialize_challenge,
)
from skills.models import Skill, XpEvent, calculate_level, progress_for_xp
from statuses.models import StatusDefinition


DEFAULT_HERO_NAME = "Username"


@dataclass(frozen=True)
class DashboardRange:
    key: str
    label: str
    start_date: date
    end_date: date
    start_at: datetime
    end_at: datetime


def _start_of_day(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.min))


def _day_after(day: date) -> datetime:
    return _start_of_day(day + timedelta(days=1))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_dashboard_range(params: dict[str, str]) -> DashboardRange:
    today = timezone.localdate()
    range_key = params.get("range", "today")

    if range_key == "week":
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        label = "Current week"
    elif range_key == "month":
        start_date = today.replace(day=1)
        next_month = (
            start_date.replace(year=start_date.year + 1, month=1)
            if start_date.month == 12
            else start_date.replace(month=start_date.month + 1)
        )
        end_date = next_month - timedelta(days=1)
        label = "Current month"
    elif range_key == "custom":
        parsed_start = _parse_date(params.get("start"))
        parsed_end = _parse_date(params.get("end"))
        if parsed_start and parsed_end:
            start_date = min(parsed_start, parsed_end)
            end_date = max(parsed_start, parsed_end)
            label = "Custom range"
        else:
            range_key = "today"
            start_date = end_date = today
            label = "Today"
    else:
        range_key = "today"
        start_date = end_date = today
        label = "Today"

    return DashboardRange(
        key=range_key,
        label=label,
        start_date=start_date,
        end_date=end_date,
        start_at=_start_of_day(start_date),
        end_at=_day_after(end_date),
    )


def _date_labels(start_date: date, end_date: date) -> list[str]:
    labels: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        labels.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return labels


def _clamp_int(value: int, lower: int = 0, upper: int = 100) -> int:
    return max(lower, min(upper, value))


def _rank_for_level(level: int) -> dict[str, str]:
    ranks = (
        (50, "Legendary"),
        (35, "Diamond"),
        (25, "Platinum"),
        (15, "Gold"),
        (8, "Silver"),
        (1, "Bronze"),
    )
    for threshold, label in ranks:
        if level >= threshold:
            return {"label": label, "threshold": str(threshold)}
    return {"label": "Bronze", "threshold": "1"}


def _status_value(
    latest_status_map: dict[str, int | None],
    name: str,
    default: int = 0,
) -> int:
    value = latest_status_map.get(name.lower())
    return default if value is None else value


def _attribute_score(total_xp: int, baseline: int = 0) -> int:
    if total_xp <= 0:
        return baseline
    progress = progress_for_xp(total_xp)
    return _clamp_int(12 + (progress["level"] * 12) + (progress["percent"] // 3))


def _build_attribute_rows(
    skill_rows: list[dict[str, Any]],
    latest_status_map: dict[str, int | None],
    today_entries: Sequence[ActivityEntry],
) -> list[dict[str, Any]]:
    total_xp_by_skill = {
        row["skill"].name.lower(): int(row["total_xp"]) for row in skill_rows
    }
    range_xp_by_skill = {
        row["skill"].name.lower(): int(row["range_xp"]) for row in skill_rows
    }

    def combined_total(names: set[str]) -> int:
        return sum(total_xp_by_skill.get(name.lower(), 0) for name in names)

    def combined_growth(names: set[str]) -> int:
        range_xp = sum(range_xp_by_skill.get(name.lower(), 0) for name in names)
        return _clamp_int(range_xp // 60, 0, 9)

    discipline_value = _clamp_int(
        20 + (len(today_entries) * 7) + (_status_value(latest_status_map, "Focus") // 3)
    )
    charisma_source = (
        _status_value(latest_status_map, "Mood")
        + _status_value(latest_status_map, "Calm")
    )
    charisma_value = _clamp_int(charisma_source // 2 if charisma_source else 0)

    attribute_specs = (
        (
            "Strength",
            _attribute_score(combined_total({"Fitness"})),
            combined_growth({"Fitness"}),
        ),
        (
            "Intelligence",
            _attribute_score(combined_total({"Learning", "Reading", "Research"})),
            combined_growth({"Learning", "Reading", "Research"}),
        ),
        ("Discipline", discipline_value, _clamp_int(len(today_entries), 0, 9)),
        ("Charisma", charisma_value, 0),
        (
            "Creativity",
            _attribute_score(combined_total({"Writing"})),
            combined_growth({"Writing"}),
        ),
        ("Wealth", 0, 0),
    )

    return [
        {
            "name": name,
            "value": value,
            "progress": _clamp_int(value),
            "growth": f"+{growth}" if growth else "0",
        }
        for name, value, growth in attribute_specs
    ]


def _build_weekly_progress(today: date, total_xp: int) -> dict[str, Any]:
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    labels = _date_labels(week_start, week_end)

    week_events = list(
        XpEvent.objects.filter(
            earned_at__gte=_start_of_day(week_start),
            earned_at__lt=_day_after(week_end),
        ).order_by("earned_at")
    )
    week_entries = list(
        ActivityEntry.objects.filter(
            started_at__gte=_start_of_day(week_start),
            started_at__lt=_day_after(week_end),
        )
    )

    xp_by_day = dict.fromkeys(labels, 0)
    for event in week_events:
        xp_by_day[timezone.localdate(event.earned_at).isoformat()] += event.amount

    values = [xp_by_day[label] for label in labels]
    max_value = max(values) if values else 0
    bars = []
    for label, value in zip(labels, values, strict=True):
        day = date.fromisoformat(label)
        height = 4 if max_value == 0 else _clamp_int(round((value / max_value) * 100), 10)
        bars.append(
            {
                "label": day.strftime("%a"),
                "xp": value,
                "height": height,
            }
        )

    weekly_xp = sum(values)
    previous_total_xp = max(total_xp - weekly_xp, 0)

    return {
        "bars": bars,
        "xp": weekly_xp,
        "quests": len(week_entries),
        "levels": max(0, calculate_level(total_xp) - calculate_level(previous_total_xp)),
    }


def build_dashboard_context(
    params: dict[str, str],
    *,
    hero_name: str | None = None,
) -> dict[str, Any]:
    selected_range = get_dashboard_range(params)
    labels = _date_labels(selected_range.start_date, selected_range.end_date)
    today = timezone.localdate()
    display_hero_name = hero_name.strip() if hero_name else DEFAULT_HERO_NAME

    range_events = list(
        XpEvent.objects.filter(
            earned_at__gte=selected_range.start_at,
            earned_at__lt=selected_range.end_at,
        )
        .select_related("skill", "activity_entry")
        .order_by("earned_at")
    )
    range_entries = list(
        ActivityEntry.objects.filter(
            started_at__gte=selected_range.start_at,
            started_at__lt=selected_range.end_at,
        ).select_related("activity_definition")
    )
    today_entries = list(
        ActivityEntry.objects.filter(
            started_at__gte=_start_of_day(today),
            started_at__lt=_day_after(today),
        ).select_related("activity_definition")
    )

    total_xp = int(XpEvent.objects.aggregate(total=Sum("amount"))["total"] or 0)
    range_xp = sum(event.amount for event in range_events)
    range_minutes = sum(entry.minutes for entry in range_entries)

    total_xp_by_skill = {
        row["skill_id"]: int(row["total"] or 0)
        for row in XpEvent.objects.values("skill_id").annotate(total=Sum("amount"))
    }
    range_xp_by_skill: dict[int, int] = {}
    range_minutes_by_skill: dict[int, int] = {}
    for event in range_events:
        range_xp_by_skill[event.skill_id] = (
            range_xp_by_skill.get(event.skill_id, 0) + event.amount
        )
        if event.activity_entry_id:
            range_minutes_by_skill[event.skill_id] = (
                range_minutes_by_skill.get(event.skill_id, 0)
                + event.activity_entry.minutes
            )

    skill_rows = []
    for skill in Skill.objects.select_related("life_area").order_by("name"):
        skill_total_xp = total_xp_by_skill.get(skill.id, 0)
        progress = progress_for_xp(skill_total_xp)
        skill_rows.append(
            {
                "skill": skill,
                "total_xp": skill_total_xp,
                "level": progress["level"],
                "progress": progress,
                "range_xp": range_xp_by_skill.get(skill.id, 0),
                "range_minutes": range_minutes_by_skill.get(skill.id, 0),
            }
        )
    skill_rows.sort(key=lambda row: (-row["total_xp"], row["skill"].name))

    latest_statuses = []
    latest_status_map: dict[str, int | None] = {}
    for definition in StatusDefinition.objects.order_by("name"):
        entry = definition.entries.order_by("-recorded_at", "-created_at").first()
        latest_statuses.append(
            {
                "definition": definition,
                "entry": entry,
            }
        )
        latest_status_map[definition.name.lower()] = entry.value if entry else None

    daily_xp = dict.fromkeys(labels, 0)
    daily_minutes = dict.fromkeys(labels, 0)
    for event in range_events:
        daily_xp[timezone.localdate(event.earned_at).isoformat()] += event.amount
    for entry in range_entries:
        daily_minutes[timezone.localdate(entry.started_at).isoformat()] += entry.minutes

    global_progress = progress_for_xp(total_xp)
    daily_quests = build_daily_quest_rows(today)
    habits, habits_summary = build_habit_rows(today)
    journal_entries = build_journal_entry_rows(
        limit=5,
        start_date=selected_range.start_date,
        end_date=selected_range.end_date,
    )
    active_challenge = serialize_challenge(get_active_challenge())
    energy_value = _status_value(latest_status_map, "Energy")
    focus_value = _status_value(latest_status_map, "Focus")
    stamina_value = _clamp_int(round(energy_value / 10), 0, 10)

    return {
        "selected_range": selected_range,
        "range_options": (
            ("today", "Today"),
            ("week", "Week"),
            ("month", "Month"),
            ("custom", "Custom"),
        ),
        "stats": {
            "range_xp": range_xp,
            "total_xp": total_xp,
            "global_level": calculate_level(total_xp),
            "activity_count": len(range_entries),
            "range_minutes": range_minutes,
        },
        "hero": {
            "name": display_hero_name or DEFAULT_HERO_NAME,
            "subtitle": "The journey shapes the legend.",
            "level": global_progress["level"],
            "total_xp": total_xp,
            "next_level_xp": global_progress["next_level_xp"],
            "progress_percent": global_progress["percent"],
            "rank": _rank_for_level(global_progress["level"]),
            "main_skill": skill_rows[0]["skill"].name if skill_rows else "No main skill",
        },
        "resource_cards": [
            {
                "name": "Energy",
                "value": energy_value,
                "max": 100,
                "progress": energy_value,
            },
            {
                "name": "Focus",
                "value": focus_value,
                "max": 100,
                "progress": focus_value,
            },
            {
                "name": "Stamina",
                "value": stamina_value,
                "max": 10,
                "progress": stamina_value * 10,
            },
        ],
        "attribute_rows": _build_attribute_rows(
            skill_rows,
            latest_status_map,
            today_entries,
        ),
        "daily_quests": daily_quests,
        "active_challenge": active_challenge,
        "habits": habits,
        "habits_summary": habits_summary,
        "weekly_progress": _build_weekly_progress(today, total_xp),
        "achievements": build_recent_achievement_rows(),
        "journal_entries": journal_entries,
        "skill_rows": skill_rows,
        "latest_statuses": latest_statuses,
        "xp_chart": {
            "labels": labels,
            "values": [daily_xp[label] for label in labels],
        },
        "time_chart": {
            "labels": labels,
            "values": [daily_minutes[label] for label in labels],
        },
    }
