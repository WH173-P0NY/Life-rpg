from django.db import models


class QuestType(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    ONE_TIME = "one_time", "One time"
    AI_GENERATED = "ai_generated", "AI generated"


class QuestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class QuestDifficulty(models.TextChoices):
    EASY = "easy", "Easy"
    NORMAL = "normal", "Normal"
    HARD = "hard", "Hard"
    EPIC = "epic", "Epic"


class CreationSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    SYSTEM = "system", "System"
    AI = "ai", "AI"


class TargetUnit(models.TextChoices):
    COUNT = "count", "Count"
    MINUTES = "minutes", "Minutes"
    STEPS = "steps", "Steps"
    PAGES = "pages", "Pages"
    CHECK = "check", "Check"


class HabitFrequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"


class GoalStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class GoalPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    LEGENDARY = "legendary", "Legendary"


class ChallengeStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    ARCHIVED = "archived", "Archived"


class ChallengeCadence(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"


class AchievementRarity(models.TextChoices):
    COMMON = "common", "Common"
    RARE = "rare", "Rare"
    EPIC = "epic", "Epic"
    LEGENDARY = "legendary", "Legendary"


class AchievementTrigger(models.TextChoices):
    MANUAL = "manual", "Manual"
    TOTAL_XP = "total_xp", "Total XP"
    SKILL_LEVEL = "skill_level", "Skill level"
    QUEST_COUNT = "quest_count", "Quest count"
    HABIT_STREAK = "habit_streak", "Habit streak"
    CHALLENGE_COMPLETED = "challenge_completed", "Challenge completed"
    GOAL_COMPLETED = "goal_completed", "Goal completed"
    JOURNAL_STREAK = "journal_streak", "Journal streak"


class JournalEntryType(models.TextChoices):
    MANUAL = "manual", "Manual"
    QUEST = "quest", "Quest"
    HABIT = "habit", "Habit"
    HABIT_MILESTONE = "habit_milestone", "Habit milestone"
    GOAL = "goal", "Goal"
    CHALLENGE = "challenge", "Challenge"
    ACHIEVEMENT = "achievement", "Achievement"
    SYSTEM = "system", "System"


class JournalMood(models.TextChoices):
    READY_FOR_BATTLE = "ready_for_battle", "Ready for Battle"
    FOCUSED = "focused", "Focused"
    BALANCED = "balanced", "Balanced"
    TIRED = "tired", "Tired"
    EXHAUSTED = "exhausted", "Exhausted"
