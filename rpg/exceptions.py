from __future__ import annotations


class RpgDomainError(Exception):
    """Base exception for RPG domain-service failures."""

    status_code = 400
    code = "rpg_domain_error"


class RpgValidationError(RpgDomainError):
    code = "validation_error"


class QuestNotActiveError(RpgDomainError):
    status_code = 409
    code = "quest_not_active"


class QuestNotAvailableError(RpgDomainError):
    status_code = 409
    code = "quest_not_available"


class QuestAlreadyCompletedError(RpgDomainError):
    status_code = 409
    code = "quest_already_completed"


class HabitNotActiveError(RpgDomainError):
    status_code = 409
    code = "habit_not_active"


class GoalNotEditableError(RpgDomainError):
    status_code = 409
    code = "goal_not_editable"


class ChallengeNotActiveError(RpgDomainError):
    status_code = 409
    code = "challenge_not_active"


class ChallengeNotCompletableError(RpgDomainError):
    status_code = 409
    code = "challenge_not_completable"
