from __future__ import annotations

from datetime import datetime

from django.db import transaction

from .models import ActivityDefinition, ActivityEntry


@transaction.atomic
def create_activity_entry(
    *,
    activity_definition: ActivityDefinition,
    minutes: int,
    started_at: datetime,
    source: str = "manual",
) -> ActivityEntry:
    """Create an activity entry and award XP to every rewarded skill."""
    if minutes <= 0:
        raise ValueError("Activity minutes must be greater than 0.")

    entry = ActivityEntry(
        activity_definition=activity_definition,
        minutes=minutes,
        started_at=started_at,
        source=source.strip() or "manual",
    )
    entry.full_clean()
    entry.save()

    xp_events = []
    rewards = activity_definition.rewards.select_related("skill")
    for reward in rewards:
        xp_events.append(
            reward.skill.add_xp(
                amount=minutes * reward.xp_per_minute,
                source_type="activity",
                note=activity_definition.name,
                activity_entry=entry,
            )
        )

    if xp_events:
        from rpg.services import evaluate_achievements

        entry._achievement_unlocks = evaluate_achievements(
            source_type="activity",
            source_id=entry.id,
        )

    return entry
