from __future__ import annotations

import json
from datetime import date
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from skills.models import XpEvent

from .exceptions import RpgDomainError, RpgValidationError
from .models import (
    Achievement,
    Challenge,
    Goal,
    Habit,
    HabitCheckIn,
    HabitMilestone,
    HabitMilestoneUnlock,
    JournalEntry,
    Quest,
    QuestCompletion,
)
from .services import (
    archive_goal,
    build_achievement_rows,
    build_challenge_rows,
    build_goal_rows,
    build_journal_overview,
    complete_challenge,
    complete_goal,
    complete_quest,
    create_challenge,
    create_goal,
    create_journal_entry,
    evaluate_achievements,
    fail_challenge,
    get_quest_completion_xp_events,
    serialize_achievement_unlock,
    serialize_challenge,
    serialize_challenge_check_in,
    serialize_goal,
    serialize_goal_progress_entry,
    serialize_journal_entry,
    toggle_habit,
    toggle_challenge_check_in,
    unlock_achievement,
    update_challenge,
    update_goal,
    update_goal_progress,
    update_journal_entry,
    update_quest_progress,
)


@require_POST
def complete_quest_api(request: HttpRequest, quest_id: int) -> JsonResponse:
    quest = get_object_or_404(Quest, pk=quest_id)
    try:
        payload = _json_payload(request)
        completion = complete_quest(
            quest=quest,
            completed_on=_optional_date(payload.get("completed_on")),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(_serialize_completion_response(completion))


@require_POST
def update_quest_progress_api(request: HttpRequest, quest_id: int) -> JsonResponse:
    quest = get_object_or_404(Quest, pk=quest_id)
    try:
        payload = _json_payload(request)
        completion = update_quest_progress(
            quest=quest,
            progress_value=_required_int(payload.get("progress_value")),
            completed_on=_optional_date(payload.get("completed_on")),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(_serialize_completion_response(completion))


@require_POST
def toggle_habit_api(request: HttpRequest, habit_id: int) -> JsonResponse:
    habit = get_object_or_404(Habit, pk=habit_id)
    try:
        payload = _json_payload(request)
        result = toggle_habit(
            habit=habit,
            checked_on=_optional_date(payload.get("checked_on")),
            value=_optional_int(payload.get("value"), field_name="value"),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(_serialize_habit_toggle_response(result))


@require_http_methods(["GET", "POST"])
def goals_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(
            {"goals": build_goal_rows(status=_optional_string(request.GET.get("status")) or "active")}
        )

    try:
        payload = _json_payload(request)
        goal = create_goal(
            title=_required_string(payload.get("title"), field_name="title"),
            description=_optional_string(payload.get("description")),
            status=_optional_string(payload.get("status")) or "draft",
            priority=_optional_string(payload.get("priority")) or "normal",
            target_value=_optional_int(payload.get("target_value"), field_name="target_value") or 1,
            target_unit=_optional_string(payload.get("target_unit")) or "count",
            starts_on=_optional_date(payload.get("starts_on")),
            due_on=_optional_date(payload.get("due_on")),
            life_area_id=_optional_int(payload.get("life_area_id"), field_name="life_area_id"),
            skill_ids=_optional_id_list(payload.get("skill_ids")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {"goal": serialize_goal(goal), "dashboard_refresh_required": True},
        status=201,
    )


@require_http_methods(["PATCH"])
def goal_detail_api(request: HttpRequest, goal_id: int) -> JsonResponse:
    goal = get_object_or_404(Goal, pk=goal_id)
    try:
        payload = _json_payload(request)
        updated_goal = update_goal(
            goal=goal,
            title=_optional_present_string(payload, "title"),
            description=_optional_present_string(payload, "description"),
            status=_optional_present_string(payload, "status"),
            priority=_optional_present_string(payload, "priority"),
            target_value=_optional_present_int(payload, "target_value"),
            target_unit=_optional_present_string(payload, "target_unit"),
            starts_on=_optional_present_date(payload, "starts_on"),
            due_on=_optional_present_date(payload, "due_on"),
            life_area_id=_optional_present_int(payload, "life_area_id"),
            skill_ids=(
                _optional_id_list(payload.get("skill_ids"))
                if "skill_ids" in payload
                else None
            ),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {"goal": serialize_goal(updated_goal), "dashboard_refresh_required": True}
    )


@require_POST
def goal_progress_api(request: HttpRequest, goal_id: int) -> JsonResponse:
    goal = get_object_or_404(Goal, pk=goal_id)
    try:
        payload = _json_payload(request)
        entry = update_goal_progress(
            goal=goal,
            progress_value=_required_int_field(
                payload.get("progress_value"),
                field_name="progress_value",
            ),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "goal": serialize_goal(Goal.objects.get(pk=goal.id)),
            "progress_entry": serialize_goal_progress_entry(entry),
            "unlocked_achievements": [
                serialize_achievement_unlock(unlock)
                for unlock in getattr(entry, "_achievement_unlocks", [])
            ],
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def goal_complete_api(request: HttpRequest, goal_id: int) -> JsonResponse:
    goal = get_object_or_404(Goal, pk=goal_id)
    try:
        payload = _json_payload(request)
        result = complete_goal(goal=goal, note=_optional_string(payload.get("note")))
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "goal": serialize_goal(result["goal"]),
            "achievement_unlocks": [
                serialize_achievement_unlock(unlock)
                for unlock in result["achievement_unlocks"]
            ],
            "journal_entry": (
                serialize_journal_entry(result["journal_entry"])
                if result["journal_entry"]
                else None
            ),
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def goal_archive_api(request: HttpRequest, goal_id: int) -> JsonResponse:
    goal = get_object_or_404(Goal, pk=goal_id)
    try:
        payload = _json_payload(request)
        result = archive_goal(goal=goal, note=_optional_string(payload.get("note")))
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {"goal": serialize_goal(result["goal"]), "dashboard_refresh_required": True}
    )


@require_http_methods(["GET", "POST"])
def challenges_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(
            {
                "challenges": build_challenge_rows(
                    status=_optional_string(request.GET.get("status")) or "active"
                )
            }
        )

    try:
        payload = _json_payload(request)
        challenge = create_challenge(
            title=_required_string(payload.get("title"), field_name="title"),
            description=_optional_string(payload.get("description")),
            status=_optional_string(payload.get("status")) or "draft",
            target_value=_optional_int(payload.get("target_value"), field_name="target_value") or 30,
            target_unit=_optional_string(payload.get("target_unit")) or "check",
            start_date=_required_date(payload.get("start_date"), field_name="start_date"),
            end_date=_required_date(payload.get("end_date"), field_name="end_date"),
            reward_title=_optional_string(payload.get("reward_title")),
            goal_id=_optional_int(payload.get("goal_id"), field_name="goal_id"),
            rewards=_optional_rewards(payload.get("rewards")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {"challenge": serialize_challenge(challenge), "dashboard_refresh_required": True},
        status=201,
    )


@require_http_methods(["PATCH"])
def challenge_detail_api(request: HttpRequest, challenge_id: int) -> JsonResponse:
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    try:
        payload = _json_payload(request)
        updated_challenge = update_challenge(
            challenge=challenge,
            title=_optional_present_string(payload, "title"),
            description=_optional_present_string(payload, "description"),
            status=_optional_present_string(payload, "status"),
            target_value=_optional_present_int(payload, "target_value"),
            target_unit=_optional_present_string(payload, "target_unit"),
            start_date=_optional_present_date(payload, "start_date"),
            end_date=_optional_present_date(payload, "end_date"),
            reward_title=_optional_present_string(payload, "reward_title"),
            goal_id=_optional_present_int(payload, "goal_id"),
            rewards=(
                _optional_rewards(payload.get("rewards"))
                if "rewards" in payload
                else None
            ),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "challenge": serialize_challenge(updated_challenge),
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def challenge_toggle_api(request: HttpRequest, challenge_id: int) -> JsonResponse:
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    try:
        payload = _json_payload(request)
        result = toggle_challenge_check_in(
            challenge=challenge,
            checked_on=_optional_date(payload.get("checked_on")),
            value=_optional_int(payload.get("value"), field_name="value"),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "challenge": serialize_challenge(result["challenge"]),
            "check_in": serialize_challenge_check_in(result["check_in"]),
            "checked": result["checked"],
            "completion_ready": result["completion_ready"],
            "xp_events": [],
            "achievement_unlocks": [],
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def challenge_complete_api(request: HttpRequest, challenge_id: int) -> JsonResponse:
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    try:
        payload = _json_payload(request)
        result = complete_challenge(
            challenge=challenge,
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "challenge": serialize_challenge(result["challenge"]),
            "xp_events": [_serialize_xp_event(event) for event in result["xp_events"]],
            "achievement_unlocks": [
                serialize_achievement_unlock(unlock)
                for unlock in result["achievement_unlocks"]
            ],
            "journal_entry": (
                serialize_journal_entry(result["journal_entry"])
                if result["journal_entry"]
                else None
            ),
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def challenge_fail_api(request: HttpRequest, challenge_id: int) -> JsonResponse:
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    try:
        payload = _json_payload(request)
        result = fail_challenge(
            challenge=challenge,
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "challenge": serialize_challenge(result["challenge"]),
            "xp_events": [],
            "achievement_unlocks": [],
            "journal_entry": (
                serialize_journal_entry(result["journal_entry"])
                if result["journal_entry"]
                else None
            ),
            "dashboard_refresh_required": True,
        }
    )


@require_http_methods(["GET"])
def achievements_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "achievements": build_achievement_rows(
                status=_optional_string(request.GET.get("status")) or "all"
            )
        }
    )


@require_POST
def achievement_unlock_api(request: HttpRequest, achievement_id: int) -> JsonResponse:
    achievement = get_object_or_404(Achievement, pk=achievement_id)
    try:
        payload = _json_payload(request)
        unlock = unlock_achievement(
            achievement=achievement,
            source_type=_optional_string(payload.get("source_type")) or "manual",
            source_id=_optional_int(payload.get("source_id"), field_name="source_id"),
            note=_optional_string(payload.get("note")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "unlock": serialize_achievement_unlock(unlock),
            "dashboard_refresh_required": True,
        }
    )


@require_POST
def achievement_evaluate_api(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_payload(request)
        unlocks = evaluate_achievements(
            source_type=_optional_string(payload.get("source_type")) or "manual_evaluation",
            source_id=_optional_int(payload.get("source_id"), field_name="source_id"),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse(
        {
            "achievement_unlocks": [
                serialize_achievement_unlock(unlock) for unlock in unlocks
            ],
            "dashboard_refresh_required": True,
        }
    )


@require_http_methods(["GET", "POST"])
def journal_entries_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        try:
            selected_date = _optional_date(request.GET.get("day"))
            limit = _clamped_limit(request.GET.get("limit"), default=30)
            overview = build_journal_overview(
                selected_date=selected_date,
                limit=limit,
                query=_optional_string(request.GET.get("query")),
                tag=_optional_string(request.GET.get("tag")),
            )
        except RpgDomainError as exc:
            return _domain_error_response(exc)
        return JsonResponse(overview)

    try:
        payload = _json_payload(request)
        entry = create_journal_entry(
            title=_required_string(payload.get("title"), field_name="title"),
            content=_optional_string(payload.get("content")),
            mood=_optional_string(payload.get("mood")),
            reflection_proud=_optional_string(payload.get("reflection_proud")),
            reflection_challenge=_optional_string(payload.get("reflection_challenge")),
            reflection_learned=_optional_string(payload.get("reflection_learned")),
            reflection_improve=_optional_string(payload.get("reflection_improve")),
            reflection_goal_action=_optional_string(payload.get("reflection_goal_action")),
            tags=_optional_tags(payload.get("tags")),
            entry_date=_optional_date(payload.get("entry_date")),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse({"entry": serialize_journal_entry(entry)}, status=201)


@require_http_methods(["PATCH"])
def journal_entry_detail_api(request: HttpRequest, entry_id: int) -> JsonResponse:
    entry = get_object_or_404(JournalEntry, pk=entry_id)
    try:
        payload = _json_payload(request)
        updated_entry = update_journal_entry(
            entry=entry,
            title=_optional_present_string(payload, "title"),
            content=_optional_present_string(payload, "content"),
            mood=_optional_present_string(payload, "mood"),
            reflection_proud=_optional_present_string(payload, "reflection_proud"),
            reflection_challenge=_optional_present_string(
                payload,
                "reflection_challenge",
            ),
            reflection_learned=_optional_present_string(payload, "reflection_learned"),
            reflection_improve=_optional_present_string(payload, "reflection_improve"),
            reflection_goal_action=_optional_present_string(
                payload,
                "reflection_goal_action",
            ),
            tags=_optional_present_tags(payload, "tags"),
            entry_date=(
                _optional_date(payload.get("entry_date"))
                if "entry_date" in payload
                else None
            ),
        )
    except RpgDomainError as exc:
        return _domain_error_response(exc)

    return JsonResponse({"entry": serialize_journal_entry(updated_entry)})


def _json_payload(request: HttpRequest) -> dict[str, Any]:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RpgValidationError("Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise RpgValidationError("JSON payload must be an object.")
    return payload


def _optional_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise RpgValidationError("Date fields must use ISO format.")
    parsed = parse_date(value)
    if parsed is None:
        raise RpgValidationError("Date fields must use ISO format.")
    return parsed


def _required_date(value: Any, *, field_name: str) -> date:
    parsed = _optional_date(value)
    if parsed is None:
        raise RpgValidationError(f"{field_name} is required.")
    return parsed


def _optional_present_date(payload: dict[str, Any], key: str) -> date | None:
    if key not in payload:
        return None
    return _optional_date(payload.get(key))


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise RpgValidationError("Text fields must be strings.")
    return value


def _optional_present_string(payload: dict[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    return _optional_string(payload.get(key))


def _optional_tags(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    if isinstance(value, list):
        if not all(isinstance(tag, str) for tag in value):
            raise RpgValidationError("tags must be a list of strings.")
        return value
    raise RpgValidationError("tags must be a list of strings.")


def _optional_present_tags(payload: dict[str, Any], key: str) -> list[str] | None:
    if key not in payload:
        return None
    return _optional_tags(payload.get(key))


def _clamped_limit(value: Any, *, default: int) -> int:
    if value in (None, ""):
        return default
    limit = _optional_int(value, field_name="limit")
    if limit is None:
        return default
    return max(1, min(limit, 100))


def _required_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise RpgValidationError(f"{field_name} is required.")
    if not isinstance(value, str):
        raise RpgValidationError(f"{field_name} must be a string.")
    return value


def _required_int(value: Any) -> int:
    return _required_int_field(value, field_name="progress_value")


def _required_int_field(value: Any, *, field_name: str) -> int:
    if value is None or isinstance(value, bool):
        raise RpgValidationError(f"{field_name} is required.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RpgValidationError(f"{field_name} must be an integer.") from exc
    return parsed


def _optional_int(value: Any, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise RpgValidationError(f"{field_name} must be an integer.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RpgValidationError(f"{field_name} must be an integer.") from exc
    return parsed


def _optional_present_int(payload: dict[str, Any], key: str) -> int | None:
    if key not in payload:
        return None
    return _optional_int(payload.get(key), field_name=key)


def _optional_id_list(value: Any) -> list[int]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise RpgValidationError("id list fields must be lists.")
    ids: list[int] = []
    for item in value:
        if isinstance(item, bool):
            raise RpgValidationError("id list fields must contain integers.")
        try:
            ids.append(int(item))
        except (TypeError, ValueError) as exc:
            raise RpgValidationError("id list fields must contain integers.") from exc
    return ids


def _optional_rewards(value: Any) -> list[dict[str, int]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise RpgValidationError("rewards must be a list.")
    rewards: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            raise RpgValidationError("rewards must contain objects.")
        rewards.append(
            {
                "skill_id": _required_int_field(
                    item.get("skill_id"),
                    field_name="skill_id",
                ),
                "xp_amount": _required_int_field(
                    item.get("xp_amount"),
                    field_name="xp_amount",
                ),
            }
        )
    return rewards


def _domain_error_response(exc: RpgDomainError) -> JsonResponse:
    return JsonResponse(
        {
            "error": {
                "code": exc.code,
                "message": str(exc),
            }
        },
        status=exc.status_code,
    )


def _serialize_completion_response(completion: QuestCompletion) -> dict[str, Any]:
    quest = completion.quest
    rewards = list(quest.rewards.select_related("skill"))
    xp_events = get_quest_completion_xp_events(completion)
    progress = min(100, int((completion.progress_value / quest.target_value) * 100))

    return {
        "quest": {
            "id": quest.id,
            "title": quest.title,
            "completed": completion.completed_at is not None,
            "progress_value": completion.progress_value,
            "target_value": quest.target_value,
            "target_unit": quest.target_unit,
            "progress_percent": progress,
            "completion_id": completion.id,
            "reward_xp": sum(reward.xp_amount for reward in rewards),
            "reward_skills": [
                {
                    "id": reward.skill_id,
                    "name": reward.skill.name,
                    "xp_amount": reward.xp_amount,
                }
                for reward in rewards
            ],
        },
        "completion": {
            "id": completion.id,
            "completed_on": completion.completed_on.isoformat(),
            "progress_value": completion.progress_value,
            "completed_at": (
                completion.completed_at.isoformat()
                if completion.completed_at
                else None
            ),
            "xp_awarded_at": (
                completion.xp_awarded_at.isoformat()
                if completion.xp_awarded_at
                else None
            ),
        },
        "xp_events": [_serialize_xp_event(event) for event in xp_events],
    }


def _serialize_habit_toggle_response(result: dict[str, Any]) -> dict[str, Any]:
    habit = result["habit"]
    check_in = result["check_in"]
    streak_days = result["streak_days"]
    next_milestone = result["next_milestone"]

    return {
        "habit": {
            "id": habit.id,
            "name": habit.name,
            "description": habit.description,
            "frequency": habit.frequency,
            "target_value": habit.target_value,
            "target_unit": habit.target_unit,
            "checked": result["checked"],
            "completed_today": result["checked"],
            "check_in_id": check_in.id if check_in else None,
            "check_in": _serialize_habit_check_in(check_in),
            "streak_days": streak_days,
            "next_milestone": _serialize_next_habit_milestone(
                milestone=next_milestone,
                streak_days=streak_days,
            ),
        },
        "milestone_unlocks": [
            _serialize_milestone_unlock(unlock)
            for unlock in result["milestone_unlocks"]
        ],
        "xp_events": [_serialize_xp_event(event) for event in result["xp_events"]],
        "dashboard_refresh_required": True,
    }


def _serialize_habit_check_in(check_in: HabitCheckIn | None) -> dict[str, Any] | None:
    if check_in is None:
        return None
    return {
        "id": check_in.id,
        "checked_on": check_in.checked_on.isoformat(),
        "value": check_in.value,
    }


def _serialize_next_habit_milestone(
    *,
    milestone: HabitMilestone | None,
    streak_days: int,
) -> dict[str, Any] | None:
    if milestone is None:
        return None
    remaining_days = max(milestone.streak_days - streak_days, 0)
    return {
        "id": milestone.id,
        "title": milestone.title,
        "streak_days": milestone.streak_days,
        "remaining_days": remaining_days,
        "days_remaining": remaining_days,
        "reward_xp": milestone.reward_xp_total(),
    }


def _serialize_milestone_unlock(unlock: HabitMilestoneUnlock) -> dict[str, Any]:
    return {
        "id": unlock.id,
        "milestone_id": unlock.milestone_id,
        "title": unlock.milestone.title,
        "habit_id": unlock.habit_id,
        "streak_days": unlock.streak_days,
        "unlocked_at": unlock.unlocked_at.isoformat(),
        "xp_awarded_at": (
            unlock.xp_awarded_at.isoformat() if unlock.xp_awarded_at else None
        ),
    }


def _serialize_xp_event(event: XpEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "skill": {
            "id": event.skill_id,
            "name": event.skill.name,
        },
        "amount": event.amount,
        "source_type": event.source_type,
        "note": event.note,
        "earned_at": event.earned_at.isoformat(),
    }
