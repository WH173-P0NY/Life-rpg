from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.utils import timezone

from activities.models import ActivityEntry
from skills.models import Skill, XpEvent

from .choices import (
    AchievementTrigger,
    ChallengeStatus,
    CreationSource,
    GoalPriority,
    GoalStatus,
    JournalEntryType,
    JournalMood,
    QuestStatus,
    QuestType,
    TargetUnit,
)
from .exceptions import (
    ChallengeNotActiveError,
    ChallengeNotCompletableError,
    GoalNotEditableError,
    HabitNotActiveError,
    QuestAlreadyCompletedError,
    QuestNotActiveError,
    QuestNotAvailableError,
    RpgValidationError,
)
from .models import (
    Achievement,
    AchievementUnlock,
    CharacterIdentity,
    Challenge,
    ChallengeCheckIn,
    ChallengeReward,
    Goal,
    GoalProgressEntry,
    GoalSkill,
    Habit,
    HabitCheckIn,
    HabitMilestone,
    HabitMilestoneUnlock,
    JournalEntry,
    Quest,
    QuestCompletion,
)

REFLECTION_QUESTIONS = (
    {
        "key": "reflection_proud",
        "question": "What am I proud of today?",
    },
    {
        "key": "reflection_challenge",
        "question": "What challenged me?",
    },
    {
        "key": "reflection_learned",
        "question": "What did I learn?",
    },
    {
        "key": "reflection_improve",
        "question": "What should I improve tomorrow?",
    },
    {
        "key": "reflection_goal_action",
        "question": "What action moved me closer to my goals?",
    },
)


def complete_quest(
    *,
    quest: Quest,
    completed_on: date | None = None,
    note: str = "",
) -> QuestCompletion:
    """Complete a quest and award its rewards exactly once."""
    day = completed_on or timezone.localdate()

    with transaction.atomic():
        locked_quest = _lock_quest(quest)
        _validate_quest_for_day(locked_quest, day)
        completion = _get_completion_for_update(quest=locked_quest, day=day)

        if _is_completed_one_time(locked_quest, completion):
            raise QuestAlreadyCompletedError("One-time quest is already completed.")

        completion.progress_value = locked_quest.target_value
        if note:
            completion.note = note.strip()
        xp_events = _mark_completed_and_award_xp(completion)
        completion._xp_events = xp_events

    _try_create_quest_completion_journal(completion)
    completion._achievement_unlocks = evaluate_achievements(
        source_type="quest_completion",
        source_id=completion.id,
    )
    return completion


def update_quest_progress(
    *,
    quest: Quest,
    progress_value: int,
    completed_on: date | None = None,
    note: str = "",
) -> QuestCompletion:
    """Update quest progress and complete it when the target is reached."""
    if progress_value < 0:
        raise RpgValidationError("Progress value cannot be negative.")

    day = completed_on or timezone.localdate()

    with transaction.atomic():
        locked_quest = _lock_quest(quest)
        _validate_quest_for_day(locked_quest, day)
        completion = _get_completion_for_update(quest=locked_quest, day=day)

        if _is_completed_one_time(locked_quest, completion):
            raise QuestAlreadyCompletedError("One-time quest is already completed.")
        if completion.completed_at and progress_value < locked_quest.target_value:
            raise QuestAlreadyCompletedError(
                "Completed quest progress cannot be lowered."
            )

        completion.progress_value = progress_value
        if note:
            completion.note = note.strip()

        completed_before_update = completion.completed_at is not None
        if progress_value >= locked_quest.target_value:
            xp_events = _mark_completed_and_award_xp(completion)
        else:
            completion.full_clean()
            completion.save(update_fields=["progress_value", "note", "updated_at"])
            xp_events = []

        completion._xp_events = xp_events

    if completion.completed_at and not completed_before_update:
        _try_create_quest_completion_journal(completion)
        completion._achievement_unlocks = evaluate_achievements(
            source_type="quest_completion",
            source_id=completion.id,
        )
    return completion


def create_journal_entry(
    *,
    title: str,
    content: str = "",
    entry_type: str = JournalEntryType.MANUAL,
    mood: str = "",
    reflection_proud: str = "",
    reflection_challenge: str = "",
    reflection_learned: str = "",
    reflection_improve: str = "",
    reflection_goal_action: str = "",
    tags: list[str] | None = None,
    source_type: str = "",
    source_id: int | None = None,
    entry_date: date | None = None,
) -> JournalEntry:
    """Create a validated journal entry."""
    selected_date = entry_date or timezone.localdate()
    clean_source_type = source_type.strip()
    if clean_source_type and source_id is not None:
        existing_entry = JournalEntry.objects.filter(
            source_type=clean_source_type,
            source_id=source_id,
        ).first()
        if existing_entry:
            return existing_entry

    entry = JournalEntry(
        title=title,
        content=content,
        entry_type=entry_type,
        mood=mood,
        reflection_proud=reflection_proud,
        reflection_challenge=reflection_challenge,
        reflection_learned=reflection_learned,
        reflection_improve=reflection_improve,
        reflection_goal_action=reflection_goal_action,
        tags=tags or [],
        source_type=clean_source_type,
        source_id=source_id,
        entry_date=selected_date,
    )
    try:
        entry.full_clean()
    except ValidationError as exc:
        raise RpgValidationError(_validation_error_message(exc)) from exc

    entry.save()
    entry._achievement_unlocks = evaluate_achievements(
        source_type="journal_entry",
        source_id=entry.id,
        trigger_types={AchievementTrigger.JOURNAL_STREAK},
    )
    return entry


def update_journal_entry(
    *,
    entry: JournalEntry,
    title: str | None = None,
    content: str | None = None,
    mood: str | None = None,
    reflection_proud: str | None = None,
    reflection_challenge: str | None = None,
    reflection_learned: str | None = None,
    reflection_improve: str | None = None,
    reflection_goal_action: str | None = None,
    tags: list[str] | None = None,
    entry_date: date | None = None,
) -> JournalEntry:
    """Update a manual journal entry without changing its source identity."""
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if mood is not None:
        entry.mood = mood
    if reflection_proud is not None:
        entry.reflection_proud = reflection_proud
    if reflection_challenge is not None:
        entry.reflection_challenge = reflection_challenge
    if reflection_learned is not None:
        entry.reflection_learned = reflection_learned
    if reflection_improve is not None:
        entry.reflection_improve = reflection_improve
    if reflection_goal_action is not None:
        entry.reflection_goal_action = reflection_goal_action
    if tags is not None:
        entry.tags = tags
    if entry_date is not None:
        entry.entry_date = entry_date

    try:
        entry.full_clean()
    except ValidationError as exc:
        raise RpgValidationError(_validation_error_message(exc)) from exc

    entry.save()
    return entry


def create_system_journal_entry(
    *,
    title: str,
    content: str = "",
    entry_type: str,
    source_type: str,
    source_id: int,
    entry_date: date | None = None,
) -> JournalEntry:
    """Create an idempotent automatic journal entry for a domain event."""
    return create_journal_entry(
        title=title,
        content=content,
        entry_type=entry_type,
        source_type=source_type,
        source_id=source_id,
        entry_date=entry_date,
    )


def build_goal_rows(*, status: str = "active") -> list[dict[str, Any]]:
    goals = Goal.objects.select_related("life_area").prefetch_related(
        "goal_skills__skill"
    )
    if status and status != "all":
        goals = goals.filter(status=status)
    return [serialize_goal(goal) for goal in goals.order_by("sort_order", "due_on", "id")]


def create_goal(
    *,
    title: str,
    description: str = "",
    status: str = GoalStatus.DRAFT,
    priority: str = GoalPriority.NORMAL,
    target_value: int = 1,
    target_unit: str = TargetUnit.COUNT,
    starts_on: date | None = None,
    due_on: date | None = None,
    life_area_id: int | None = None,
    skill_ids: list[int] | None = None,
    created_by: str = CreationSource.MANUAL,
) -> Goal:
    goal = Goal(
        title=title,
        description=description,
        status=status,
        priority=priority,
        target_value=target_value,
        target_unit=target_unit,
        starts_on=starts_on,
        due_on=due_on,
        life_area_id=life_area_id,
        created_by=created_by,
    )
    _clean_or_raise(goal)
    goal.save()
    _replace_goal_skills(goal, skill_ids or [])
    return goal


def update_goal(
    *,
    goal: Goal,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    target_value: int | None = None,
    target_unit: str | None = None,
    starts_on: date | None = None,
    due_on: date | None = None,
    life_area_id: int | None = None,
    skill_ids: list[int] | None = None,
) -> Goal:
    if goal.status in {GoalStatus.COMPLETED, GoalStatus.ARCHIVED}:
        raise GoalNotEditableError("Completed or archived goals cannot be edited.")

    with transaction.atomic():
        locked_goal = Goal.objects.select_for_update().get(pk=goal.pk)
        if title is not None:
            locked_goal.title = title
        if description is not None:
            locked_goal.description = description
        if status is not None:
            locked_goal.status = status
        if priority is not None:
            locked_goal.priority = priority
        if target_value is not None:
            locked_goal.target_value = target_value
            locked_goal.progress_value = min(
                locked_goal.progress_value,
                locked_goal.target_value,
            )
        if target_unit is not None:
            locked_goal.target_unit = target_unit
        if starts_on is not None:
            locked_goal.starts_on = starts_on
        if due_on is not None:
            locked_goal.due_on = due_on
        if life_area_id is not None:
            locked_goal.life_area_id = life_area_id

        _clean_or_raise(locked_goal)
        locked_goal.save()
        if skill_ids is not None:
            _replace_goal_skills(locked_goal, skill_ids)

    return Goal.objects.prefetch_related("goal_skills__skill").get(pk=goal.pk)


def update_goal_progress(
    *,
    goal: Goal,
    progress_value: int,
    note: str = "",
    source_type: str = "",
    source_id: int | None = None,
    recorded_at: datetime | None = None,
) -> GoalProgressEntry:
    if progress_value < 0:
        raise RpgValidationError("Progress value cannot be negative.")

    clean_source_type = source_type.strip()
    if clean_source_type and source_id is not None:
        existing_entry = GoalProgressEntry.objects.filter(
            goal=goal,
            source_type=clean_source_type,
            source_id=source_id,
        ).first()
        if existing_entry:
            return existing_entry

    completed_now = False
    with transaction.atomic():
        locked_goal = Goal.objects.select_for_update().get(pk=goal.pk)
        if locked_goal.status in {GoalStatus.COMPLETED, GoalStatus.ARCHIVED}:
            raise GoalNotEditableError(
                "Completed or archived goals cannot receive progress."
            )
        previous_value = locked_goal.progress_value
        new_value = min(progress_value, locked_goal.target_value)
        locked_goal.progress_value = new_value
        if new_value >= locked_goal.target_value:
            locked_goal.status = GoalStatus.COMPLETED
            locked_goal.completed_at = timezone.now()
            completed_now = True
        _clean_or_raise(locked_goal)
        locked_goal.save()

        entry = GoalProgressEntry(
            goal=locked_goal,
            previous_value=previous_value,
            new_value=new_value,
            delta=new_value - previous_value,
            note=note,
            source_type=clean_source_type,
            source_id=source_id,
            recorded_at=recorded_at or timezone.now(),
        )
        _clean_or_raise(entry)
        entry.save()

    if completed_now:
        _try_create_goal_completion_journal(locked_goal)
        entry._achievement_unlocks = evaluate_achievements(
            source_type="goal_completion",
            source_id=locked_goal.id,
        )
    return entry


def complete_goal(*, goal: Goal, note: str = "") -> dict[str, Any]:
    completed_now = False
    with transaction.atomic():
        locked_goal = Goal.objects.select_for_update().get(pk=goal.pk)
        if locked_goal.status == GoalStatus.ARCHIVED:
            raise GoalNotEditableError("Archived goals cannot be completed.")
        if locked_goal.status != GoalStatus.COMPLETED:
            locked_goal.progress_value = locked_goal.target_value
            locked_goal.status = GoalStatus.COMPLETED
            locked_goal.completed_at = timezone.now()
            _clean_or_raise(locked_goal)
            locked_goal.save()
            completed_now = True

    if completed_now:
        _try_create_goal_completion_journal(locked_goal, note=note)
    unlocks = evaluate_achievements(
        source_type="goal_completion",
        source_id=locked_goal.id,
    )
    journal_entry = JournalEntry.objects.filter(
        source_type="goal_completion",
        source_id=locked_goal.id,
    ).first()
    return {
        "goal": locked_goal,
        "achievement_unlocks": unlocks,
        "journal_entry": journal_entry,
    }


def archive_goal(*, goal: Goal, note: str = "") -> dict[str, Any]:
    with transaction.atomic():
        locked_goal = Goal.objects.select_for_update().get(pk=goal.pk)
        if locked_goal.status != GoalStatus.ARCHIVED:
            locked_goal.status = GoalStatus.ARCHIVED
            locked_goal.archived_at = timezone.now()
            _clean_or_raise(locked_goal)
            locked_goal.save()
    return {"goal": locked_goal, "note": note}


def build_challenge_rows(*, status: str = "active") -> list[dict[str, Any]]:
    challenges = Challenge.objects.select_related("goal").prefetch_related(
        "rewards__skill",
        "checkins",
    )
    if status and status != "all":
        challenges = challenges.filter(status=status)
    return [serialize_challenge(challenge) for challenge in challenges]


def get_active_challenge() -> Challenge | None:
    return (
        Challenge.objects.filter(status=ChallengeStatus.ACTIVE)
        .prefetch_related("rewards__skill", "checkins")
        .order_by("sort_order", "end_date", "-created_at", "id")
        .first()
    )


def create_challenge(
    *,
    title: str,
    description: str = "",
    status: str = ChallengeStatus.DRAFT,
    target_value: int = 30,
    target_unit: str = TargetUnit.CHECK,
    start_date: date,
    end_date: date,
    reward_title: str = "",
    goal_id: int | None = None,
    rewards: list[dict[str, int]] | None = None,
    created_by: str = CreationSource.MANUAL,
) -> Challenge:
    challenge = Challenge(
        title=title,
        description=description,
        status=status,
        target_value=target_value,
        target_unit=target_unit,
        start_date=start_date,
        end_date=end_date,
        reward_title=reward_title,
        goal_id=goal_id,
        created_by=created_by,
    )
    _clean_or_raise(challenge)
    challenge.save()
    _replace_challenge_rewards(challenge, rewards or [])
    return challenge


def update_challenge(
    *,
    challenge: Challenge,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    target_value: int | None = None,
    target_unit: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    reward_title: str | None = None,
    goal_id: int | None = None,
    rewards: list[dict[str, int]] | None = None,
) -> Challenge:
    with transaction.atomic():
        locked_challenge = Challenge.objects.select_for_update().get(pk=challenge.pk)
        if locked_challenge.status in {
            ChallengeStatus.COMPLETED,
            ChallengeStatus.FAILED,
            ChallengeStatus.ARCHIVED,
        }:
            raise ChallengeNotCompletableError(
                "Closed challenges cannot be edited by the API."
            )
        if title is not None:
            locked_challenge.title = title
        if description is not None:
            locked_challenge.description = description
        if status is not None:
            locked_challenge.status = status
        if target_value is not None:
            locked_challenge.target_value = target_value
            locked_challenge.current_value = min(
                locked_challenge.current_value,
                locked_challenge.target_value,
            )
        if target_unit is not None:
            locked_challenge.target_unit = target_unit
        if start_date is not None:
            locked_challenge.start_date = start_date
        if end_date is not None:
            locked_challenge.end_date = end_date
        if reward_title is not None:
            locked_challenge.reward_title = reward_title
        if goal_id is not None:
            locked_challenge.goal_id = goal_id
        _recalculate_challenge_current_value(locked_challenge)
        _clean_or_raise(locked_challenge)
        locked_challenge.save()
        if rewards is not None:
            _replace_challenge_rewards(locked_challenge, rewards)
    return Challenge.objects.prefetch_related("rewards__skill", "checkins").get(
        pk=challenge.pk
    )


def toggle_challenge_check_in(
    *,
    challenge: Challenge,
    checked_on: date | None = None,
    value: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    selected_day = checked_on or timezone.localdate()
    if value is not None and value < 0:
        raise RpgValidationError("Challenge check-in value cannot be negative.")

    with transaction.atomic():
        locked_challenge = Challenge.objects.select_for_update().get(pk=challenge.pk)
        if locked_challenge.status != ChallengeStatus.ACTIVE:
            raise ChallengeNotActiveError("Challenge is not active.")

        check_in = (
            ChallengeCheckIn.objects.select_for_update()
            .filter(challenge=locked_challenge, checked_on=selected_day)
            .first()
        )
        if check_in:
            check_in.delete()
            checked = False
            check_in = None
        else:
            check_in = ChallengeCheckIn(
                challenge=locked_challenge,
                checked_on=selected_day,
                value=1 if value is None else value,
                successful=True,
                note=note,
            )
            _clean_or_raise(check_in)
            check_in.save()
            checked = True

        _recalculate_challenge_current_value(locked_challenge)
        _clean_or_raise(locked_challenge)
        locked_challenge.save(update_fields=["current_value", "updated_at"])

    return {
        "challenge": locked_challenge,
        "check_in": check_in,
        "checked": checked,
        "completion_ready": locked_challenge.current_value >= locked_challenge.target_value,
        "xp_events": [],
        "achievement_unlocks": [],
    }


def complete_challenge(*, challenge: Challenge, note: str = "") -> dict[str, Any]:
    completed_now = False
    with transaction.atomic():
        locked_challenge = (
            Challenge.objects.select_for_update()
            .prefetch_related("rewards__skill")
            .get(pk=challenge.pk)
        )
        if locked_challenge.status in {
            ChallengeStatus.FAILED,
            ChallengeStatus.ARCHIVED,
        }:
            raise ChallengeNotCompletableError(
                "Failed or archived challenges cannot be completed."
            )

        if locked_challenge.status != ChallengeStatus.COMPLETED:
            locked_challenge.status = ChallengeStatus.COMPLETED
            locked_challenge.current_value = locked_challenge.target_value
            locked_challenge.completed_at = timezone.now()
            completed_now = True

        xp_events = award_challenge_xp(locked_challenge)
        _clean_or_raise(locked_challenge)
        locked_challenge.save()

    if completed_now:
        _try_create_challenge_completion_journal(locked_challenge, note=note)
    unlocks = evaluate_achievements(
        source_type="challenge_completion",
        source_id=locked_challenge.id,
    )
    journal_entry = JournalEntry.objects.filter(
        source_type="challenge_completion",
        source_id=locked_challenge.id,
    ).first()
    return {
        "challenge": locked_challenge,
        "xp_events": xp_events,
        "achievement_unlocks": unlocks,
        "journal_entry": journal_entry,
    }


def fail_challenge(*, challenge: Challenge, note: str = "") -> dict[str, Any]:
    with transaction.atomic():
        locked_challenge = (
            Challenge.objects.select_for_update()
            .prefetch_related("rewards__skill")
            .get(pk=challenge.pk)
        )
        if locked_challenge.status in {
            ChallengeStatus.COMPLETED,
            ChallengeStatus.ARCHIVED,
        }:
            raise ChallengeNotCompletableError(
                "Completed or archived challenges cannot be failed."
            )

        if locked_challenge.status != ChallengeStatus.FAILED:
            locked_challenge.status = ChallengeStatus.FAILED
            locked_challenge.failed_at = timezone.now()
        elif locked_challenge.failed_at is None:
            locked_challenge.failed_at = timezone.now()

        _clean_or_raise(locked_challenge)
        locked_challenge.save(update_fields=["status", "failed_at", "updated_at"])

    _try_create_challenge_failure_journal(locked_challenge, note=note)
    journal_entry = JournalEntry.objects.filter(
        source_type="challenge_failure",
        source_id=locked_challenge.id,
    ).first()
    return {
        "challenge": locked_challenge,
        "xp_events": [],
        "achievement_unlocks": [],
        "journal_entry": journal_entry,
    }


def award_challenge_xp(challenge: Challenge) -> list[XpEvent]:
    if challenge.xp_awarded_at is not None:
        return get_challenge_xp_events(challenge)

    xp_events: list[XpEvent] = []
    for reward in challenge.rewards.all():
        xp_events.append(
            reward.skill.add_xp(
                amount=reward.xp_amount,
                source_type="challenge",
                note=_challenge_xp_note(challenge),
            )
        )
    challenge.xp_awarded_at = timezone.now()
    return xp_events


def get_challenge_xp_events(challenge: Challenge) -> list[XpEvent]:
    if hasattr(challenge, "_xp_events"):
        return list(challenge._xp_events)
    return list(
        XpEvent.objects.select_related("skill").filter(
            source_type="challenge",
            note__endswith=f"challenge_id={challenge.id}",
        )
    )


def unlock_achievement(
    *,
    achievement: Achievement,
    source_type: str = "",
    source_id: int | None = None,
    note: str = "",
    snapshot: dict[str, Any] | None = None,
) -> AchievementUnlock:
    existing_unlock = AchievementUnlock.objects.filter(achievement=achievement).first()
    if existing_unlock:
        return existing_unlock

    unlock = AchievementUnlock(
        achievement=achievement,
        source_type=source_type,
        source_id=source_id,
        note=note,
        snapshot=snapshot or {},
    )
    _clean_or_raise(unlock)
    unlock.save()
    _try_create_achievement_unlock_journal(unlock)
    return unlock


def evaluate_achievements(
    *,
    source_type: str = "",
    source_id: int | None = None,
    trigger_types: set[str] | None = None,
) -> list[AchievementUnlock]:
    achievements = (
        Achievement.objects.filter(is_active=True)
        .exclude(unlocks__isnull=False)
        .order_by("sort_order", "id")
    )
    if trigger_types:
        achievements = achievements.filter(trigger_type__in=trigger_types)
    unlocks: list[AchievementUnlock] = []
    for achievement in achievements:
        if _achievement_condition_met(achievement):
            unlocks.append(
                unlock_achievement(
                    achievement=achievement,
                    source_type=source_type,
                    source_id=source_id,
                    note=f"Unlocked by {source_type or 'manual evaluation'}.",
                    snapshot={"trigger_config": achievement.trigger_config},
                )
            )
    return unlocks


def build_achievement_rows(*, status: str = "all") -> list[dict[str, Any]]:
    achievements = Achievement.objects.prefetch_related("unlocks")
    rows = [serialize_achievement(achievement) for achievement in achievements]
    if status == "unlocked":
        return [row for row in rows if row["unlocked"]]
    if status == "locked":
        return [row for row in rows if not row["unlocked"]]
    return rows


def build_recent_achievement_rows(limit: int = 5) -> list[dict[str, Any]]:
    unlocks = (
        AchievementUnlock.objects.select_related("achievement")
        .order_by("-unlocked_at", "-id")[:limit]
    )
    return [serialize_achievement_unlock(unlock) for unlock in unlocks]


def serialize_goal(goal: Goal) -> dict[str, Any]:
    linked_skills = [
        {
            "id": link.skill_id,
            "name": link.skill.name,
            "weight": link.weight,
        }
        for link in goal.goal_skills.all()
    ]
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "status": goal.status,
        "priority": goal.priority,
        "progress_value": goal.progress_value,
        "target_value": goal.target_value,
        "target_unit": goal.target_unit,
        "progress_percent": goal.progress_percent(),
        "starts_on": goal.starts_on.isoformat() if goal.starts_on else None,
        "due_on": goal.due_on.isoformat() if goal.due_on else None,
        "life_area": (
            {
                "id": goal.life_area_id,
                "name": goal.life_area.name,
            }
            if goal.life_area_id
            else None
        ),
        "linked_skills": linked_skills,
        "created_by": goal.created_by,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
        "completed_at": goal.completed_at.isoformat() if goal.completed_at else None,
        "archived_at": goal.archived_at.isoformat() if goal.archived_at else None,
    }


def serialize_goal_progress_entry(entry: GoalProgressEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "goal_id": entry.goal_id,
        "previous_value": entry.previous_value,
        "new_value": entry.new_value,
        "delta": entry.delta,
        "note": entry.note,
        "source_type": entry.source_type,
        "source_id": entry.source_id,
        "recorded_at": entry.recorded_at.isoformat(),
    }


def serialize_challenge(challenge: Challenge | None) -> dict[str, Any] | None:
    if challenge is None:
        return None

    reward_skills = [
        {
            "id": reward.skill_id,
            "name": reward.skill.name,
            "xp_amount": reward.xp_amount,
        }
        for reward in challenge.rewards.all()
    ]
    today = timezone.localdate()
    current_day = challenge.current_day(today)
    progress_percent = challenge.progress_percent()
    reward_xp = sum(reward["xp_amount"] for reward in reward_skills)
    reward_label = challenge.reward_title or (
        f"+{reward_xp} XP" if reward_xp else "No XP reward"
    )
    return {
        "id": challenge.id,
        "title": challenge.title,
        "name": challenge.title,
        "description": challenge.description,
        "status": challenge.status,
        "start_date": challenge.start_date.isoformat(),
        "end_date": challenge.end_date.isoformat(),
        "elapsed_days": current_day,
        "day": current_day,
        "total_days": challenge.total_days(),
        "total": challenge.total_days(),
        "current_value": challenge.current_value,
        "target_value": challenge.target_value,
        "target_unit": challenge.target_unit,
        "progress_percent": progress_percent,
        "progress": progress_percent,
        "reward_title": challenge.reward_title,
        "reward": reward_label,
        "reward_xp": reward_xp,
        "xp_reward": reward_xp,
        "reward_skills": reward_skills,
        "completed_at": (
            challenge.completed_at.isoformat() if challenge.completed_at else None
        ),
        "failed_at": challenge.failed_at.isoformat() if challenge.failed_at else None,
        "xp_awarded_at": (
            challenge.xp_awarded_at.isoformat() if challenge.xp_awarded_at else None
        ),
        "goal_id": challenge.goal_id,
    }


def serialize_challenge_check_in(
    check_in: ChallengeCheckIn | None,
) -> dict[str, Any] | None:
    if check_in is None:
        return None
    return {
        "id": check_in.id,
        "checked_on": check_in.checked_on.isoformat(),
        "value": check_in.value,
        "successful": check_in.successful,
        "note": check_in.note,
    }


def serialize_achievement(achievement: Achievement) -> dict[str, Any]:
    unlock = achievement.unlocks.first()
    progress = _achievement_progress(achievement)
    return {
        "id": achievement.id,
        "title": achievement.title,
        "description": achievement.description,
        "rarity": achievement.rarity,
        "trigger_type": achievement.trigger_type,
        "trigger_config": achievement.trigger_config,
        "icon": achievement.icon,
        "is_active": achievement.is_active,
        "unlocked": unlock is not None,
        "unlock": serialize_achievement_unlock(unlock) if unlock else None,
        "progress": progress,
    }


def serialize_achievement_unlock(
    unlock: AchievementUnlock | None,
) -> dict[str, Any] | None:
    if unlock is None:
        return None
    return {
        "id": unlock.id,
        "achievement_id": unlock.achievement_id,
        "title": unlock.achievement.title,
        "description": unlock.achievement.description,
        "rarity": unlock.achievement.rarity,
        "unlocked_at": unlock.unlocked_at.isoformat(),
        "source_type": unlock.source_type,
        "source_id": unlock.source_id,
        "note": unlock.note,
    }


def get_recent_journal_entries(
    *,
    limit: int = 5,
    start_date: date | None = None,
    end_date: date | None = None,
) -> QuerySet[JournalEntry]:
    """Return recent journal entries filtered by entry date when requested."""
    entries = JournalEntry.objects.all()
    if start_date is not None:
        entries = entries.filter(entry_date__gte=start_date)
    if end_date is not None:
        entries = entries.filter(entry_date__lte=end_date)
    return entries.order_by("-created_at", "-id")[:limit]


def build_journal_entry_rows(
    *,
    limit: int = 5,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    return [
        _serialize_journal_entry(entry)
        for entry in get_recent_journal_entries(
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
    ]


def search_journal_entries(
    *,
    limit: int = 30,
    start_date: date | None = None,
    end_date: date | None = None,
    query: str = "",
    tag: str = "",
) -> list[JournalEntry]:
    """Return journal entries for the full journal view."""
    entries = JournalEntry.objects.all()
    if start_date is not None:
        entries = entries.filter(entry_date__gte=start_date)
    if end_date is not None:
        entries = entries.filter(entry_date__lte=end_date)

    clean_query = query.strip()
    if clean_query:
        entries = entries.filter(
            Q(title__icontains=clean_query)
            | Q(content__icontains=clean_query)
            | Q(reflection_proud__icontains=clean_query)
            | Q(reflection_challenge__icontains=clean_query)
            | Q(reflection_learned__icontains=clean_query)
            | Q(reflection_improve__icontains=clean_query)
            | Q(reflection_goal_action__icontains=clean_query)
        )

    rows = list(entries.order_by("-entry_date", "-created_at", "-id")[:200])
    clean_tag = _normalize_tag_value(tag)
    if clean_tag:
        rows = [entry for entry in rows if clean_tag in entry.tags]
    return rows[:limit]


def build_journal_overview(
    *,
    selected_date: date | None = None,
    limit: int = 30,
    query: str = "",
    tag: str = "",
) -> dict[str, Any]:
    """Build the data contract for the Hero Journal view."""
    day = selected_date or timezone.localdate()
    entries = search_journal_entries(limit=limit, query=query, tag=tag)
    current_entry = (
        JournalEntry.objects.filter(
            entry_date=day,
            entry_type=JournalEntryType.MANUAL,
        )
        .order_by("-updated_at", "-created_at", "-id")
        .first()
    )

    return {
        "selected_date": day.isoformat(),
        "entries": [serialize_journal_entry(entry) for entry in entries],
        "current_entry": (
            serialize_journal_entry(current_entry) if current_entry else None
        ),
        "stats": build_journal_stats(),
        "activity_timeline": build_journal_activity_timeline(day),
        "chapters": build_story_chapters(),
        "identity": build_character_identity_rows(),
        "insights": build_journal_insights(day),
        "mood_options": [
            {"value": mood.value, "label": mood.label} for mood in JournalMood
        ],
        "reflection_questions": list(REFLECTION_QUESTIONS),
        "available_tags": build_journal_tags(),
    }


def build_journal_stats() -> dict[str, int]:
    entries = list(
        JournalEntry.objects.only(
            "content",
            "reflection_proud",
            "reflection_challenge",
            "reflection_learned",
            "reflection_improve",
            "reflection_goal_action",
            "entry_date",
        )
    )
    total_xp = int(XpEvent.objects.aggregate(total=Sum("amount"))["total"] or 0)
    completed_quests = QuestCompletion.objects.filter(
        completed_at__isnull=False
    ).count()

    return {
        "total_entries": len(entries),
        "current_streak": _journal_entry_streak(entries),
        "words_written": sum(entry.word_count() for entry in entries),
        "xp_logged": total_xp,
        "completed_quests": completed_quests,
        "achievements_unlocked": AchievementUnlock.objects.count(),
    }


def build_journal_activity_timeline(day: date | None = None) -> list[dict[str, Any]]:
    selected_day = day or timezone.localdate()
    start_at = _aware_datetime_for_day(selected_day)
    end_at = _aware_datetime_for_day(selected_day + timedelta(days=1))
    events: list[tuple[datetime, dict[str, Any]]] = []

    activities = (
        ActivityEntry.objects.filter(started_at__gte=start_at, started_at__lt=end_at)
        .select_related("activity_definition")
        .prefetch_related("xp_events")
    )
    for activity in activities:
        xp_amount = sum(event.amount for event in activity.xp_events.all())
        events.append(
            (
                activity.started_at,
                _timeline_event(
                    event_id=f"activity-{activity.id}",
                    occurred_at=activity.started_at,
                    title=f"{activity.activity_definition.name} session",
                    description=f"{activity.minutes} minutes from {activity.source}",
                    source_type="activity",
                    xp=xp_amount,
                ),
            )
        )

    completions = QuestCompletion.objects.filter(
        completed_at__gte=start_at,
        completed_at__lt=end_at,
    ).select_related("quest")
    for completion in completions:
        occurred_at = completion.completed_at
        if occurred_at is None:
            continue
        xp_amount = sum(event.amount for event in get_quest_completion_xp_events(completion))
        events.append(
            (
                occurred_at,
                _timeline_event(
                    event_id=f"quest-{completion.id}",
                    occurred_at=occurred_at,
                    title=f"Quest completed: {completion.quest.title}",
                    description=completion.note,
                    source_type="quest",
                    xp=xp_amount,
                ),
            )
        )

    check_ins = (
        HabitCheckIn.objects.filter(created_at__gte=start_at, created_at__lt=end_at)
        .select_related("habit")
        .order_by("created_at")
    )
    for check_in in check_ins:
        events.append(
            (
                check_in.created_at,
                _timeline_event(
                    event_id=f"habit-{check_in.id}",
                    occurred_at=check_in.created_at,
                    title=f"Habit checked: {check_in.habit.name}",
                    description=check_in.note,
                    source_type="habit",
                    xp=0,
                ),
            )
        )

    completed_goals = Goal.objects.filter(
        completed_at__gte=start_at,
        completed_at__lt=end_at,
    ).order_by("completed_at")
    for goal in completed_goals:
        if goal.completed_at is None:
            continue
        events.append(
            (
                goal.completed_at,
                _timeline_event(
                    event_id=f"goal-{goal.id}",
                    occurred_at=goal.completed_at,
                    title=f"Goal completed: {goal.title}",
                    description=goal.description,
                    source_type="goal",
                    xp=0,
                ),
            )
        )

    completed_challenges = Challenge.objects.filter(
        completed_at__gte=start_at,
        completed_at__lt=end_at,
    ).order_by("completed_at")
    for challenge in completed_challenges:
        if challenge.completed_at is None:
            continue
        xp_amount = sum(event.amount for event in get_challenge_xp_events(challenge))
        events.append(
            (
                challenge.completed_at,
                _timeline_event(
                    event_id=f"challenge-{challenge.id}",
                    occurred_at=challenge.completed_at,
                    title=f"Challenge completed: {challenge.title}",
                    description=challenge.reward_title,
                    source_type="challenge",
                    xp=xp_amount,
                ),
            )
        )

    achievement_unlocks = (
        AchievementUnlock.objects.filter(
            unlocked_at__gte=start_at,
            unlocked_at__lt=end_at,
        )
        .select_related("achievement")
        .order_by("unlocked_at")
    )
    for unlock in achievement_unlocks:
        events.append(
            (
                unlock.unlocked_at,
                _timeline_event(
                    event_id=f"achievement-{unlock.id}",
                    occurred_at=unlock.unlocked_at,
                    title=f"Achievement unlocked: {unlock.achievement.title}",
                    description=unlock.note,
                    source_type="achievement",
                    xp=0,
                ),
            )
        )

    manual_entries = JournalEntry.objects.filter(
        entry_date=selected_day,
        entry_type=JournalEntryType.MANUAL,
    ).order_by("created_at")
    for entry in manual_entries:
        events.append(
            (
                entry.created_at,
                _timeline_event(
                    event_id=f"journal-{entry.id}",
                    occurred_at=entry.created_at,
                    title="Journal entry created",
                    description=entry.title,
                    source_type="journal",
                    xp=0,
                ),
            )
        )

    return [event for _, event in sorted(events, key=lambda item: item[0])]


def build_story_chapters() -> list[dict[str, Any]]:
    first_entry_date = (
        JournalEntry.objects.order_by("entry_date")
        .values_list("entry_date", flat=True)
        .first()
    ) or timezone.localdate()
    chapters = [
        {
            "id": "chapter-1",
            "number": "Chapter I",
            "title": "The Beginning",
            "description": "The chronicle starts with the first recorded actions.",
            "status": "unlocked",
            "unlocked_on": first_entry_date.isoformat(),
        }
    ]

    progress_count = (
        QuestCompletion.objects.filter(completed_at__isnull=False).count()
        + HabitCheckIn.objects.count()
    )
    if progress_count:
        chapters.append(
            {
                "id": "chapter-2",
                "number": "Chapter II",
                "title": "Building Discipline",
                "description": "Quests and habits begin to shape daily identity.",
                "status": "unlocked",
                "unlocked_on": timezone.localdate().isoformat(),
            }
        )

    top_skill = (
        XpEvent.objects.values("skill__name")
        .annotate(total=Sum("amount"))
        .order_by("-total", "skill__name")
        .first()
    )
    if top_skill:
        chapters.append(
            {
                "id": "chapter-3",
                "number": "Chapter III",
                "title": f"{top_skill['skill__name']} Arc",
                "description": "The strongest growth theme in the current story.",
                "status": "unlocked",
                "unlocked_on": timezone.localdate().isoformat(),
            }
        )

    if CharacterIdentity.objects.filter(is_active=True).exists():
        chapters.append(
            {
                "id": "chapter-4",
                "number": "Chapter IV",
                "title": "Identity Shift",
                "description": "A declared identity starts guiding the journey.",
                "status": "active",
                "unlocked_on": timezone.localdate().isoformat(),
            }
        )

    return chapters


def build_character_identity_rows() -> dict[str, Any]:
    identities = list(CharacterIdentity.objects.order_by("-started_on", "-created_at"))
    current = next((identity for identity in identities if identity.is_active), None)
    return {
        "current": _serialize_character_identity(current) if current else None,
        "history": [_serialize_character_identity(identity) for identity in identities],
    }


def build_journal_insights(day: date | None = None) -> list[dict[str, str]]:
    selected_day = day or timezone.localdate()
    start_at = _aware_datetime_for_day(selected_day)
    end_at = _aware_datetime_for_day(selected_day + timedelta(days=1))
    day_xp = int(
        XpEvent.objects.filter(earned_at__gte=start_at, earned_at__lt=end_at).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    completed_quests = QuestCompletion.objects.filter(
        completed_at__gte=start_at,
        completed_at__lt=end_at,
    ).count()
    habit_checks = HabitCheckIn.objects.filter(
        created_at__gte=start_at,
        created_at__lt=end_at,
    ).count()
    strongest_skill = (
        XpEvent.objects.values("skill__name")
        .annotate(total=Sum("amount"))
        .order_by("-total", "skill__name")
        .first()
    )

    insights = [
        {
            "title": "Daily momentum",
            "body": (
                f"You earned {day_xp} XP, completed {completed_quests} quests "
                f"and checked {habit_checks} habits today."
            ),
        }
    ]
    if strongest_skill:
        insights.append(
            {
                "title": "Strongest attribute",
                "body": f"{strongest_skill['skill__name']} is your strongest growth theme.",
            }
        )
    insights.append(
        {
            "title": "AI companion",
            "body": "Full AI-generated chronicle summaries are reserved for the AI module.",
        }
    )
    return insights


def build_journal_tags() -> list[str]:
    tags: set[str] = set()
    for entry_tags in JournalEntry.objects.values_list("tags", flat=True):
        if isinstance(entry_tags, list):
            tags.update(tag for tag in entry_tags if isinstance(tag, str))
    return sorted(tags)


def _clean_or_raise(instance: Any) -> None:
    try:
        instance.full_clean()
    except ValidationError as exc:
        raise RpgValidationError(_validation_error_message(exc)) from exc


def _replace_goal_skills(goal: Goal, skill_ids: list[int]) -> None:
    GoalSkill.objects.filter(goal=goal).delete()
    for skill_id in dict.fromkeys(skill_ids):
        link = GoalSkill(goal=goal, skill_id=skill_id, weight=1)
        _clean_or_raise(link)
        link.save()


def _replace_challenge_rewards(
    challenge: Challenge,
    rewards: list[dict[str, int]],
) -> None:
    ChallengeReward.objects.filter(challenge=challenge).delete()
    for reward in rewards:
        skill_id = int(reward.get("skill_id", 0))
        xp_amount = int(reward.get("xp_amount", 0))
        challenge_reward = ChallengeReward(
            challenge=challenge,
            skill_id=skill_id,
            xp_amount=xp_amount,
        )
        _clean_or_raise(challenge_reward)
        challenge_reward.save()


def _recalculate_challenge_current_value(challenge: Challenge) -> None:
    total = int(
        ChallengeCheckIn.objects.filter(
            challenge=challenge,
            successful=True,
        ).aggregate(total=Sum("value"))["total"]
        or 0
    )
    challenge.current_value = min(total, challenge.target_value)


def _challenge_xp_note(challenge: Challenge) -> str:
    return f"Challenge: {challenge.title}; challenge_id={challenge.id}"


def _achievement_condition_met(achievement: Achievement) -> bool:
    config = achievement.trigger_config
    trigger = achievement.trigger_type

    if trigger == AchievementTrigger.MANUAL:
        return False
    if trigger == AchievementTrigger.TOTAL_XP:
        total_xp = int(XpEvent.objects.aggregate(total=Sum("amount"))["total"] or 0)
        return total_xp >= int(config.get("xp", 0))
    if trigger == AchievementTrigger.SKILL_LEVEL:
        skill_id = config.get("skill_id")
        level = int(config.get("level", 0))
        if not skill_id:
            return False
        skill = Skill.objects.filter(id=skill_id).first()
        return bool(skill and skill.get_level() >= level)
    if trigger == AchievementTrigger.QUEST_COUNT:
        return (
            QuestCompletion.objects.filter(completed_at__isnull=False).count()
            >= int(config.get("quest_count", 0))
        )
    if trigger == AchievementTrigger.HABIT_STREAK:
        streak_days = int(config.get("streak_days", 0))
        habit_id = config.get("habit_id")
        if habit_id:
            habit = Habit.objects.filter(id=habit_id).first()
            return bool(habit and calculate_habit_streak(habit) >= streak_days)
        max_streak = 0
        for habit in Habit.objects.filter(is_active=True):
            max_streak = max(max_streak, calculate_habit_streak(habit))
        return max_streak >= streak_days
    if trigger == AchievementTrigger.CHALLENGE_COMPLETED:
        challenge_id = config.get("challenge_id")
        challenges = Challenge.objects.filter(status=ChallengeStatus.COMPLETED)
        if challenge_id:
            challenges = challenges.filter(id=challenge_id)
        return challenges.exists()
    if trigger == AchievementTrigger.GOAL_COMPLETED:
        goal_id = config.get("goal_id")
        goals = Goal.objects.filter(status=GoalStatus.COMPLETED)
        if goal_id:
            goals = goals.filter(id=goal_id)
        return goals.exists()
    if trigger == AchievementTrigger.JOURNAL_STREAK:
        entries = list(JournalEntry.objects.only("entry_date"))
        return _journal_entry_streak(entries) >= int(config.get("streak_days", 0))
    return False


def _achievement_progress(achievement: Achievement) -> dict[str, Any]:
    config = achievement.trigger_config
    trigger = achievement.trigger_type
    current = 0
    target = 1
    unit = trigger

    if trigger == AchievementTrigger.TOTAL_XP:
        current = int(XpEvent.objects.aggregate(total=Sum("amount"))["total"] or 0)
        target = int(config.get("xp", 1))
        unit = "xp"
    elif trigger == AchievementTrigger.SKILL_LEVEL:
        skill = Skill.objects.filter(id=config.get("skill_id")).first()
        current = skill.get_level() if skill else 0
        target = int(config.get("level", 1))
        unit = "level"
    elif trigger == AchievementTrigger.QUEST_COUNT:
        current = QuestCompletion.objects.filter(completed_at__isnull=False).count()
        target = int(config.get("quest_count", 1))
        unit = "quests"
    elif trigger == AchievementTrigger.HABIT_STREAK:
        target = int(config.get("streak_days", 1))
        if config.get("habit_id"):
            habit = Habit.objects.filter(id=config.get("habit_id")).first()
            current = calculate_habit_streak(habit) if habit else 0
        else:
            current = max(
                (calculate_habit_streak(habit) for habit in Habit.objects.filter(is_active=True)),
                default=0,
            )
        unit = "days"
    elif trigger == AchievementTrigger.CHALLENGE_COMPLETED:
        challenges = Challenge.objects.filter(status=ChallengeStatus.COMPLETED)
        if config.get("challenge_id"):
            challenges = challenges.filter(id=config.get("challenge_id"))
        current = 1 if challenges.exists() else 0
        unit = "challenge"
    elif trigger == AchievementTrigger.GOAL_COMPLETED:
        goals = Goal.objects.filter(status=GoalStatus.COMPLETED)
        if config.get("goal_id"):
            goals = goals.filter(id=config.get("goal_id"))
        current = 1 if goals.exists() else 0
        unit = "goal"
    elif trigger == AchievementTrigger.JOURNAL_STREAK:
        current = _journal_entry_streak(list(JournalEntry.objects.only("entry_date")))
        target = int(config.get("streak_days", 1))
        unit = "days"

    progress_percent = min(100, int((current / max(target, 1)) * 100))
    return {
        "current": current,
        "target": target,
        "unit": unit,
        "progress_percent": progress_percent,
    }


def _validation_error_message(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        messages: list[str] = []
        for field_messages in error.message_dict.values():
            messages.extend(str(message) for message in field_messages)
        return " ".join(messages)
    return " ".join(str(message) for message in error.messages)


def build_daily_quest_rows(day: date | None = None) -> list[dict[str, Any]]:
    """Build dashboard-ready quest rows from real RPG quest data."""
    selected_day = day or timezone.localdate()
    quests = list(
        Quest.objects.filter(
            quest_type=QuestType.DAILY,
            status=QuestStatus.ACTIVE,
        )
        .prefetch_related("rewards__skill")
        .order_by("sort_order", "title")
    )
    quest_ids = [quest.id for quest in quests if quest.is_available_on(selected_day)]
    completions = {
        completion.quest_id: completion
        for completion in QuestCompletion.objects.filter(
            quest_id__in=quest_ids,
            completed_on=selected_day,
        )
    }

    rows: list[dict[str, Any]] = []
    for quest in quests:
        if not quest.is_available_on(selected_day):
            continue
        completion = completions.get(quest.id)
        current = completion.progress_value if completion else 0
        target = quest.target_value
        progress = min(100, int((current / target) * 100)) if target else 0
        reward_skills = [
            {
                "id": reward.skill_id,
                "name": reward.skill.name,
                "xp": reward.xp_amount,
            }
            for reward in quest.rewards.all()
        ]

        rows.append(
            {
                "id": quest.id,
                "completion_id": completion.id if completion else None,
                "title": quest.title,
                "description": quest.description,
                "quest_type": quest.quest_type,
                "difficulty": quest.difficulty,
                "reward_xp": sum(item["xp"] for item in reward_skills),
                "reward_skills": reward_skills,
                "rewards": reward_skills,
                "progress_value": current,
                "target_value": target,
                "target_unit": quest.target_unit,
                "progress_percent": progress,
                "completed_at": (
                    completion.completed_at.isoformat()
                    if completion and completion.completed_at
                    else None
                ),
                "current": current,
                "target": target,
                "unit": quest.target_unit,
                "progress": progress,
                "completed": bool(completion and completion.completed_at),
            }
        )
    return rows


def calculate_habit_streak(habit: Habit, day: date | None = None) -> int:
    """Return completed consecutive habit days ending on the selected day."""
    selected_day = day or timezone.localdate()
    checkins = {
        checked_on: value
        for checked_on, value in HabitCheckIn.objects.filter(
            habit=habit,
            checked_on__lte=selected_day,
        ).values_list("checked_on", "value")
    }

    streak_days = 0
    cursor = selected_day
    while checkins.get(cursor, 0) >= habit.target_value:
        streak_days += 1
        cursor -= timedelta(days=1)
    return streak_days


def toggle_habit(
    *,
    habit: Habit,
    checked_on: date | None = None,
    value: int | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Toggle a habit check-in for a day and unlock due streak milestones."""
    selected_day = checked_on or timezone.localdate()
    if value is not None and value < 0:
        raise RpgValidationError("Habit check-in value cannot be negative.")

    with transaction.atomic():
        locked_habit = Habit.objects.select_for_update().get(pk=habit.pk)
        if not locked_habit.is_active:
            raise HabitNotActiveError("Habit is not active.")

        check_in = (
            HabitCheckIn.objects.select_for_update()
            .filter(habit=locked_habit, checked_on=selected_day)
            .first()
        )

        if check_in:
            check_in.delete()
            streak_days = calculate_habit_streak(locked_habit, selected_day)
            milestone_unlocks: list[HabitMilestoneUnlock] = []
            xp_events: list[XpEvent] = []
            checked = False
            check_in = None
        else:
            check_in = HabitCheckIn(
                habit=locked_habit,
                checked_on=selected_day,
                value=locked_habit.target_value if value is None else value,
                note=note.strip(),
            )
            check_in.full_clean()
            check_in.save()
            streak_days = calculate_habit_streak(locked_habit, selected_day)
            milestone_unlocks, xp_events = unlock_due_habit_milestones(
                habit=locked_habit,
                streak_days=streak_days,
            )
            checked = check_in.is_completed()

        next_milestone = get_next_habit_milestone(
            habit=locked_habit,
            streak_days=streak_days,
        )

    return {
        "habit": locked_habit,
        "check_in": check_in,
        "checked": checked,
        "streak_days": streak_days,
        "milestone_unlocks": milestone_unlocks,
        "next_milestone": next_milestone,
        "xp_events": xp_events,
    }


def unlock_due_habit_milestones(
    *,
    habit: Habit,
    streak_days: int,
    unlocked_on: date | None = None,
) -> tuple[list[HabitMilestoneUnlock], list[XpEvent]]:
    """Unlock all active habit milestones reached by the current streak."""
    if streak_days <= 0:
        return [], []

    with transaction.atomic():
        locked_habit = Habit.objects.select_for_update().get(pk=habit.pk)
        unlocked_at = (
            _aware_datetime_for_day(unlocked_on) if unlocked_on else timezone.now()
        )
        milestones = list(
            HabitMilestone.objects.select_for_update()
            .prefetch_related("rewards__skill")
            .filter(
                Q(habit=locked_habit) | Q(habit__isnull=True),
                is_active=True,
                streak_days__lte=streak_days,
            )
            .order_by("streak_days", "id")
        )
        existing_ids = set(
            HabitMilestoneUnlock.objects.filter(
                habit=locked_habit,
                milestone_id__in=[milestone.id for milestone in milestones],
            ).values_list("milestone_id", flat=True)
        )

        created_unlocks: list[HabitMilestoneUnlock] = []
        xp_events: list[XpEvent] = []
        for milestone in milestones:
            if milestone.id in existing_ids:
                continue
            unlock = HabitMilestoneUnlock(
                milestone=milestone,
                habit=locked_habit,
                unlocked_at=unlocked_at,
                streak_days=streak_days,
                note=f"Habit streak milestone reached: {milestone.title}",
            )
            unlock.full_clean()
            unlock.save()

            unlock_xp_events: list[XpEvent] = []
            for reward in milestone.rewards.all():
                event = reward.skill.add_xp(
                    amount=reward.xp_amount,
                    source_type="habit_milestone",
                    note=_habit_milestone_xp_note(unlock),
                )
                unlock_xp_events.append(event)
                xp_events.append(event)
            unlock.xp_awarded_at = timezone.now()
            unlock.full_clean()
            unlock.save(update_fields=["xp_awarded_at"])
            unlock._xp_events = unlock_xp_events
            _try_create_habit_milestone_journal(unlock)
            created_unlocks.append(unlock)

    evaluate_achievements(
        source_type="habit_streak",
        source_id=locked_habit.id,
    )
    return created_unlocks, xp_events


def get_next_habit_milestone(
    *,
    habit: Habit,
    streak_days: int,
) -> HabitMilestone | None:
    unlocked_milestone_ids = HabitMilestoneUnlock.objects.filter(
        habit=habit,
    ).values_list("milestone_id", flat=True)
    return (
        HabitMilestone.objects.filter(
            Q(habit=habit) | Q(habit__isnull=True),
            is_active=True,
        )
        .exclude(id__in=unlocked_milestone_ids)
        .prefetch_related("rewards")
        .order_by("streak_days", "id")
        .first()
    )


def build_habit_rows(
    day: date | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Build dashboard-ready habit rows from real RPG habit data."""
    selected_day = day or timezone.localdate()
    habits = list(
        Habit.objects.filter(is_active=True)
        .prefetch_related("milestone_unlocks", "milestones", "checkins")
        .order_by("sort_order", "name")
    )
    checkins = {
        checkin.habit_id: checkin
        for checkin in HabitCheckIn.objects.filter(
            habit_id__in=[habit.id for habit in habits],
            checked_on=selected_day,
        )
    }

    rows: list[dict[str, Any]] = []
    completed_count = 0
    longest_streak = 0
    for habit in habits:
        check_in = checkins.get(habit.id)
        completed_today = bool(check_in and check_in.value >= habit.target_value)
        streak_days = calculate_habit_streak(habit, selected_day)
        next_milestone = get_next_habit_milestone(
            habit=habit,
            streak_days=streak_days,
        )
        next_milestone_row = _serialize_next_habit_milestone(
            milestone=next_milestone,
            streak_days=streak_days,
        )

        if completed_today:
            completed_count += 1
        longest_streak = max(longest_streak, streak_days)
        rows.append(
            {
                "id": habit.id,
                "name": habit.name,
                "label": habit.name,
                "description": habit.description,
                "frequency": habit.frequency,
                "target_value": habit.target_value,
                "target_unit": habit.target_unit,
                "checked": completed_today,
                "completed_today": completed_today,
                "completed": completed_today,
                "check_in_id": check_in.id if check_in else None,
                "check_in": _serialize_habit_check_in(check_in),
                "streak_days": streak_days,
                "next_milestone": next_milestone_row,
            }
        )

    return rows, {
        "completed": completed_count,
        "total": len(rows),
        "streak_days": longest_streak,
    }


def get_quest_completion_xp_events(completion: QuestCompletion) -> list[XpEvent]:
    """Return XP events tied to a quest completion by the audit note."""
    if hasattr(completion, "_xp_events"):
        return list(completion._xp_events)
    return list(
        XpEvent.objects.select_related("skill").filter(
            source_type="quest",
            note__endswith=f"completion_id={completion.id}",
        )
    )


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
    return {
        "id": milestone.id,
        "title": milestone.title,
        "streak_days": milestone.streak_days,
        "remaining_days": max(milestone.streak_days - streak_days, 0),
        "days_remaining": max(milestone.streak_days - streak_days, 0),
        "reward_xp": milestone.reward_xp_total(),
    }


def serialize_journal_entry(entry: JournalEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "title": entry.title,
        "content": entry.content,
        "body": entry.content,
        "entry_type": entry.entry_type,
        "mood": entry.mood,
        "reflection": {
            "proud": entry.reflection_proud,
            "challenge": entry.reflection_challenge,
            "learned": entry.reflection_learned,
            "improve": entry.reflection_improve,
            "goal_action": entry.reflection_goal_action,
        },
        "reflection_proud": entry.reflection_proud,
        "reflection_challenge": entry.reflection_challenge,
        "reflection_learned": entry.reflection_learned,
        "reflection_improve": entry.reflection_improve,
        "reflection_goal_action": entry.reflection_goal_action,
        "tags": entry.tags,
        "word_count": entry.word_count(),
        "source_type": entry.source_type,
        "source_id": entry.source_id,
        "entry_date": entry.entry_date.isoformat(),
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "meta": entry.entry_date.isoformat(),
    }


def _serialize_journal_entry(entry: JournalEntry) -> dict[str, Any]:
    return serialize_journal_entry(entry)


def _serialize_character_identity(
    identity: CharacterIdentity | None,
) -> dict[str, Any] | None:
    if identity is None:
        return None
    return {
        "id": identity.id,
        "title": identity.title,
        "description": identity.description,
        "started_on": identity.started_on.isoformat(),
        "ended_on": identity.ended_on.isoformat() if identity.ended_on else None,
        "is_active": identity.is_active,
        "created_at": identity.created_at.isoformat(),
        "updated_at": identity.updated_at.isoformat(),
    }


def _timeline_event(
    *,
    event_id: str,
    occurred_at: datetime,
    title: str,
    description: str,
    source_type: str,
    xp: int,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "occurred_at": occurred_at.isoformat(),
        "time_label": timezone.localtime(occurred_at).strftime("%H:%M"),
        "title": title,
        "description": description,
        "source_type": source_type,
        "xp": xp,
    }


def _journal_entry_streak(entries: list[JournalEntry]) -> int:
    entry_dates = {entry.entry_date for entry in entries}
    cursor = timezone.localdate()
    streak = 0
    while cursor in entry_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _normalize_tag_value(value: str) -> str:
    tag = value.strip().lower()
    if tag.startswith("#"):
        tag = tag[1:]
    return "-".join(part for part in tag.split() if part)


def _aware_datetime_for_day(value: date) -> datetime:
    return timezone.make_aware(datetime.combine(value, time.min))


def _lock_quest(quest: Quest) -> Quest:
    return (
        Quest.objects.select_for_update()
        .prefetch_related("rewards__skill")
        .get(pk=quest.pk)
    )


def _validate_quest_for_day(quest: Quest, day: date) -> None:
    if quest.status != QuestStatus.ACTIVE:
        raise QuestNotActiveError("Quest is not active.")
    if not quest.is_available_on(day):
        raise QuestNotAvailableError("Quest is not available on this date.")


def _get_completion_for_update(*, quest: Quest, day: date) -> QuestCompletion:
    if quest.quest_type == QuestType.ONE_TIME:
        completion = (
            QuestCompletion.objects.select_for_update()
            .filter(quest=quest)
            .order_by("created_at", "id")
            .first()
        )
        if completion:
            return completion
        return QuestCompletion.objects.create(quest=quest, completed_on=day)

    completion, created = QuestCompletion.objects.get_or_create(
        quest=quest,
        completed_on=day,
        defaults={"progress_value": 0},
    )
    if created:
        return completion
    return QuestCompletion.objects.select_for_update().get(pk=completion.pk)


def _is_completed_one_time(quest: Quest, completion: QuestCompletion) -> bool:
    return (
        quest.quest_type == QuestType.ONE_TIME
        and completion.completed_at is not None
        and completion.xp_awarded_at is not None
    )


def _mark_completed_and_award_xp(completion: QuestCompletion) -> list[XpEvent]:
    now = timezone.now()
    if completion.completed_at is None:
        completion.completed_at = now

    xp_events: list[XpEvent] = []
    if completion.xp_awarded_at is None:
        for reward in completion.quest.rewards.all():
            xp_events.append(
                reward.skill.add_xp(
                    amount=reward.xp_amount,
                    source_type="quest",
                    note=_xp_event_note(completion),
                )
            )
        completion.xp_awarded_at = now
    else:
        xp_events = get_quest_completion_xp_events(completion)

    completion.full_clean()
    completion.save(
        update_fields=[
            "progress_value",
            "completed_at",
            "xp_awarded_at",
            "note",
            "updated_at",
        ]
    )
    return xp_events


def _xp_event_note(completion: QuestCompletion) -> str:
    return f"Quest: {completion.quest.title}; completion_id={completion.id}"


def _habit_milestone_xp_note(unlock: HabitMilestoneUnlock) -> str:
    return (
        f"Habit milestone: {unlock.milestone.title}; "
        f"habit_id={unlock.habit_id}; unlock_id={unlock.id}"
    )


def _try_create_quest_completion_journal(completion: QuestCompletion) -> None:
    if completion.completed_at is None:
        return
    try:
        create_system_journal_entry(
            title=f"Quest completed: {completion.quest.title}",
            content=completion.note,
            entry_type=JournalEntryType.QUEST,
            source_type="quest_completion",
            source_id=completion.id,
            entry_date=completion.completed_on,
        )
    except Exception:
        return


def _try_create_habit_milestone_journal(unlock: HabitMilestoneUnlock) -> None:
    try:
        create_system_journal_entry(
            title=f"Habit milestone: {unlock.milestone.title}",
            content=unlock.note,
            entry_type=JournalEntryType.HABIT_MILESTONE,
            source_type="habit_milestone_unlock",
            source_id=unlock.id,
            entry_date=timezone.localdate(unlock.unlocked_at),
        )
    except Exception:
        return


def _try_create_goal_completion_journal(goal: Goal, note: str = "") -> None:
    try:
        create_system_journal_entry(
            title=f"Goal completed: {goal.title}",
            content=note or goal.description,
            entry_type=JournalEntryType.GOAL,
            source_type="goal_completion",
            source_id=goal.id,
            entry_date=timezone.localdate(goal.completed_at) if goal.completed_at else None,
        )
    except Exception:
        return


def _try_create_challenge_completion_journal(
    challenge: Challenge,
    note: str = "",
) -> None:
    try:
        create_system_journal_entry(
            title=f"Challenge completed: {challenge.title}",
            content=note or challenge.reward_title,
            entry_type=JournalEntryType.CHALLENGE,
            source_type="challenge_completion",
            source_id=challenge.id,
            entry_date=(
                timezone.localdate(challenge.completed_at)
                if challenge.completed_at
                else None
            ),
        )
    except Exception:
        return


def _try_create_challenge_failure_journal(
    challenge: Challenge,
    note: str = "",
) -> None:
    try:
        create_system_journal_entry(
            title=f"Challenge failed: {challenge.title}",
            content=note or challenge.description,
            entry_type=JournalEntryType.CHALLENGE,
            source_type="challenge_failure",
            source_id=challenge.id,
            entry_date=(
                timezone.localdate(challenge.failed_at)
                if challenge.failed_at
                else None
            ),
        )
    except Exception:
        return


def _try_create_achievement_unlock_journal(unlock: AchievementUnlock) -> None:
    try:
        create_system_journal_entry(
            title=f"Achievement unlocked: {unlock.achievement.title}",
            content=unlock.note or unlock.achievement.description,
            entry_type=JournalEntryType.ACHIEVEMENT,
            source_type="achievement_unlock",
            source_id=unlock.id,
            entry_date=timezone.localdate(unlock.unlocked_at),
        )
    except Exception:
        return
