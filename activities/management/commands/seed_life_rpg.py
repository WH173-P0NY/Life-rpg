from __future__ import annotations

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from activities.models import ActivityDefinition, ActivityEntry, ActivityReward, ActivityRule
from activities.services import create_activity_entry
from planner.models import CalendarEvent, CalendarEventType
from rpg.choices import (
    AchievementRarity,
    AchievementTrigger,
    ChallengeStatus,
    CreationSource,
    GoalPriority,
    GoalStatus,
    HabitFrequency,
    JournalEntryType,
    JournalMood,
    QuestDifficulty,
    QuestStatus,
    QuestType,
    TargetUnit,
)
from rpg.models import (
    Achievement,
    CharacterIdentity,
    Challenge,
    ChallengeReward,
    Goal,
    GoalSkill,
    Habit,
    HabitMilestone,
    HabitMilestoneReward,
    JournalEntry,
    Quest,
    QuestReward,
)
from skills.models import LifeArea, Skill
from statuses.models import StatusDefinition, StatusEntry


class Command(BaseCommand):
    help = "Seed the local Life RPG Tracker MVP with editable starter data."

    def handle(self, *args: object, **options: object) -> None:
        areas = self._seed_life_areas()
        skills = self._seed_skills(areas)
        definitions = self._seed_activity_definitions(areas)
        self._seed_activity_rewards(definitions, skills)
        self._seed_activity_rules(definitions)
        self._seed_daily_quests(skills)
        self._seed_habits()
        self._seed_habit_milestones(skills)
        goals = self._seed_goals(areas, skills)
        challenge = self._seed_challenges(goals, skills)
        self._seed_achievements(goals, challenge)
        statuses = self._seed_status_definitions()
        self._seed_sample_activities(definitions)
        self._seed_status_entries(statuses)
        self._seed_journal_entries()
        self._seed_character_identities()
        self._seed_calendar_events()
        self.stdout.write(self.style.SUCCESS("Life RPG seed completed."))

    def _today_at(self, value: time) -> datetime:
        local_day = timezone.localdate()
        naive_value = datetime.combine(local_day, value)
        return timezone.make_aware(naive_value)

    def _seed_life_areas(self) -> dict[str, LifeArea]:
        descriptions = {
            "Mind & Learning": "Learning, research, reading, and mental growth.",
            "Craft & Work": "Professional skills and focused work output.",
            "Body & Health": "Training, movement, and physical health.",
            "Creative Output": "Writing, notes, publishing, and creation.",
            "Home & Organization": "Household, planning, and order.",
            "Social & Relationships": "Relationships, communication, and community.",
            "Recovery & Wellbeing": "Rest, balance, mood, and entertainment.",
            "Finance & Admin": "Reserved for future finance and administration work.",
        }
        return {
            name: LifeArea.objects.update_or_create(
                name=name,
                defaults={"description": description},
            )[0]
            for name, description in descriptions.items()
        }

    def _seed_skills(self, areas: dict[str, LifeArea]) -> dict[str, Skill]:
        skill_areas = {
            "Programming": "Craft & Work",
            "Reading": "Mind & Learning",
            "Fitness": "Body & Health",
            "Research": "Mind & Learning",
            "Learning": "Mind & Learning",
            "Writing": "Creative Output",
        }
        return {
            name: Skill.objects.update_or_create(
                name=name,
                defaults={"life_area": areas[area_name]},
            )[0]
            for name, area_name in skill_areas.items()
        }

    def _seed_activity_definitions(
        self, areas: dict[str, LifeArea]
    ) -> dict[str, ActivityDefinition]:
        definition_data = {
            "Coding": ("Craft & Work", "Focused software development."),
            "Technical research": (
                "Mind & Learning",
                "Researching technical topics, APIs, and design choices.",
            ),
            "Reading": ("Mind & Learning", "Reading books or long-form material."),
            "Writing notes": (
                "Creative Output",
                "Writing notes, summaries, documentation, or plans.",
            ),
            "Fitness training": (
                "Body & Health",
                "Strength, cardio, mobility, or other intentional training.",
            ),
            "Watching tutorial": (
                "Mind & Learning",
                "Learning from tutorial or course video content.",
            ),
        }
        return {
            name: ActivityDefinition.objects.update_or_create(
                name=name,
                defaults={
                    "life_area": areas[area_name],
                    "description": description,
                },
            )[0]
            for name, (area_name, description) in definition_data.items()
        }

    def _seed_activity_rewards(
        self,
        definitions: dict[str, ActivityDefinition],
        skills: dict[str, Skill],
    ) -> None:
        rewards = (
            ("Coding", "Programming", 5),
            ("Coding", "Learning", 1),
            ("Technical research", "Research", 3),
            ("Technical research", "Learning", 2),
            ("Reading", "Reading", 4),
            ("Reading", "Learning", 1),
            ("Writing notes", "Writing", 4),
            ("Writing notes", "Learning", 1),
            ("Fitness training", "Fitness", 5),
            ("Watching tutorial", "Learning", 2),
            ("Watching tutorial", "Research", 1),
        )
        for definition_name, skill_name, xp_per_minute in rewards:
            ActivityReward.objects.update_or_create(
                activity_definition=definitions[definition_name],
                skill=skills[skill_name],
                defaults={"xp_per_minute": xp_per_minute},
            )

    def _seed_activity_rules(
        self, definitions: dict[str, ActivityDefinition]
    ) -> None:
        rules = {
            "code": "Coding",
            "pycharm": "Coding",
            "chrome": "Technical research",
            "youtube": "Watching tutorial",
            "kindle": "Reading",
            "obsidian": "Writing notes",
        }
        for pattern, definition_name in rules.items():
            ActivityRule.objects.update_or_create(
                pattern=pattern,
                defaults={"activity_definition": definitions[definition_name]},
            )

    def _seed_daily_quests(self, skills: dict[str, Skill]) -> dict[str, Quest]:
        quest_data = (
            (
                "Workout 30 minutes",
                "Complete a focused training session.",
                30,
                TargetUnit.MINUTES,
                QuestDifficulty.NORMAL,
                10,
                (("Fitness", 25),),
            ),
            (
                "Read 20 minutes",
                "Read a book or long-form material.",
                20,
                TargetUnit.MINUTES,
                QuestDifficulty.EASY,
                20,
                (("Reading", 20), ("Learning", 5)),
            ),
            (
                "Study AI",
                "Study an AI topic, concept, paper, or implementation.",
                1,
                TargetUnit.CHECK,
                QuestDifficulty.NORMAL,
                30,
                (("Learning", 25), ("Research", 15)),
            ),
            (
                "Write notes",
                "Write useful notes, summaries, or implementation notes.",
                1,
                TargetUnit.CHECK,
                QuestDifficulty.EASY,
                40,
                (("Writing", 20),),
            ),
            (
                "Plan tomorrow",
                "Write a short plan for tomorrow.",
                1,
                TargetUnit.CHECK,
                QuestDifficulty.EASY,
                50,
                (("Writing", 10),),
            ),
        )
        quests: dict[str, Quest] = {}
        for (
            title,
            description,
            target_value,
            target_unit,
            difficulty,
            sort_order,
            rewards,
        ) in quest_data:
            quest, _ = Quest.objects.update_or_create(
                title=title,
                defaults={
                    "description": description,
                    "quest_type": QuestType.DAILY,
                    "status": QuestStatus.ACTIVE,
                    "difficulty": difficulty,
                    "target_value": target_value,
                    "target_unit": target_unit,
                    "created_by": CreationSource.SYSTEM,
                    "sort_order": sort_order,
                },
            )
            quests[title] = quest
            for skill_name, xp_amount in rewards:
                QuestReward.objects.update_or_create(
                    quest=quest,
                    skill=skills[skill_name],
                    defaults={"xp_amount": xp_amount},
                )
        return quests

    def _seed_habits(self) -> dict[str, Habit]:
        habit_data = (
            (
                "Train",
                "Complete intentional physical training.",
                1,
                TargetUnit.CHECK,
                10,
            ),
            (
                "Read",
                "Read a book or long-form material.",
                1,
                TargetUnit.CHECK,
                20,
            ),
            (
                "Learn",
                "Study or practice a useful skill.",
                1,
                TargetUnit.CHECK,
                30,
            ),
            (
                "Hydrate",
                "Hit the daily hydration baseline.",
                1,
                TargetUnit.CHECK,
                40,
            ),
            (
                "Sleep",
                "Protect recovery and sleep quality.",
                1,
                TargetUnit.CHECK,
                50,
            ),
            (
                "Journal",
                "Write a short reflection or progress note.",
                1,
                TargetUnit.CHECK,
                60,
            ),
            (
                "Review finances",
                "Review spending, budget, or financial plan.",
                1,
                TargetUnit.CHECK,
                70,
            ),
        )
        habits: dict[str, Habit] = {}
        for name, description, target_value, target_unit, sort_order in habit_data:
            habit, _ = Habit.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "frequency": HabitFrequency.DAILY,
                    "target_value": target_value,
                    "target_unit": target_unit,
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )
            habits[name] = habit
        return habits

    def _seed_habit_milestones(self, skills: dict[str, Skill]) -> None:
        milestone_data = (
            (
                "7 Day Momentum",
                7,
                (("Learning", 50),),
            ),
            (
                "14 Day Discipline",
                14,
                (("Fitness", 100),),
            ),
            (
                "30 Day Identity Shift",
                30,
                (("Learning", 250),),
            ),
        )
        for title, streak_days, rewards in milestone_data:
            milestone, _ = HabitMilestone.objects.update_or_create(
                habit=None,
                streak_days=streak_days,
                defaults={
                    "title": title,
                    "is_active": True,
                },
            )
            for skill_name, xp_amount in rewards:
                HabitMilestoneReward.objects.update_or_create(
                    milestone=milestone,
                    skill=skills[skill_name],
                    defaults={"xp_amount": xp_amount},
                )

    def _seed_goals(
        self,
        areas: dict[str, LifeArea],
        skills: dict[str, Skill],
    ) -> dict[str, Goal]:
        today = timezone.localdate()
        goal_data = (
            (
                "Build the Life RPG foundation",
                "Ship the core RPG loop with real goals, challenges, and achievements.",
                GoalStatus.ACTIVE,
                GoalPriority.LEGENDARY,
                "Craft & Work",
                100,
                TargetUnit.COUNT,
                today,
                today + timedelta(days=45),
                ("Programming", "Learning", "Writing"),
            ),
            (
                "Read 12 books",
                "Build a durable reading habit across the year.",
                GoalStatus.ACTIVE,
                GoalPriority.HIGH,
                "Mind & Learning",
                12,
                TargetUnit.COUNT,
                today,
                today + timedelta(days=180),
                ("Reading", "Learning"),
            ),
        )
        goals: dict[str, Goal] = {}
        for (
            title,
            description,
            status,
            priority,
            area_name,
            target_value,
            target_unit,
            starts_on,
            due_on,
            skill_names,
        ) in goal_data:
            goal, _ = Goal.objects.update_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "life_area": areas[area_name],
                    "target_value": target_value,
                    "target_unit": target_unit,
                    "starts_on": starts_on,
                    "due_on": due_on,
                    "created_by": CreationSource.SYSTEM,
                    "sort_order": 10 if priority == GoalPriority.LEGENDARY else 20,
                },
            )
            goals[title] = goal
            for skill_name in skill_names:
                GoalSkill.objects.update_or_create(
                    goal=goal,
                    skill=skills[skill_name],
                    defaults={"weight": 1},
                )
        return goals

    def _seed_challenges(
        self,
        goals: dict[str, Goal],
        skills: dict[str, Skill],
    ) -> Challenge:
        today = timezone.localdate()
        challenge, _ = Challenge.objects.update_or_create(
            title="30 Days No Sugar",
            defaults={
                "description": "Build discipline by avoiding sugar for 30 days.",
                "status": ChallengeStatus.ACTIVE,
                "goal": goals["Build the Life RPG foundation"],
                "target_value": 30,
                "target_unit": TargetUnit.CHECK,
                "current_value": 0,
                "start_date": today,
                "end_date": today + timedelta(days=29),
                "reward_title": "Epic Willpower Badge",
                "created_by": CreationSource.SYSTEM,
                "sort_order": 10,
            },
        )
        rewards = (
            ("Fitness", 250),
            ("Learning", 100),
        )
        for skill_name, xp_amount in rewards:
            ChallengeReward.objects.update_or_create(
                challenge=challenge,
                skill=skills[skill_name],
                defaults={"xp_amount": xp_amount},
            )
        return challenge

    def _seed_achievements(
        self,
        goals: dict[str, Goal],
        challenge: Challenge,
    ) -> None:
        achievement_data = (
            (
                "first-quest",
                "First Quest",
                "Complete your first quest.",
                AchievementRarity.COMMON,
                AchievementTrigger.QUEST_COUNT,
                {"quest_count": 1, "period": "all_time"},
                "sparkles",
                10,
            ),
            (
                "seven-day-momentum",
                "7 Day Momentum",
                "Reach a seven day habit streak.",
                AchievementRarity.RARE,
                AchievementTrigger.HABIT_STREAK,
                {"streak_days": 7},
                "flame",
                20,
            ),
            (
                "iron-discipline",
                "Iron Discipline",
                "Complete the 30 Days No Sugar challenge.",
                AchievementRarity.EPIC,
                AchievementTrigger.CHALLENGE_COMPLETED,
                {"challenge_id": challenge.id},
                "shield",
                30,
            ),
            (
                "goal-finisher",
                "Goal Finisher",
                "Complete your first legendary goal.",
                AchievementRarity.RARE,
                AchievementTrigger.GOAL_COMPLETED,
                {"goal_id": goals["Build the Life RPG foundation"].id},
                "trophy",
                40,
            ),
            (
                "thousand-xp",
                "Thousand XP",
                "Earn 1000 XP across all skills.",
                AchievementRarity.RARE,
                AchievementTrigger.TOTAL_XP,
                {"xp": 1000},
                "medal",
                50,
            ),
        )
        for (
            code,
            title,
            description,
            rarity,
            trigger_type,
            trigger_config,
            icon,
            sort_order,
        ) in achievement_data:
            Achievement.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "description": description,
                    "rarity": rarity,
                    "trigger_type": trigger_type,
                    "trigger_config": trigger_config,
                    "icon": icon,
                    "is_active": True,
                    "sort_order": sort_order,
                },
            )

    def _seed_status_definitions(self) -> dict[str, StatusDefinition]:
        descriptions = {
            "Rested": "Sleep and recovery quality.",
            "Fed": "Food and meal adequacy.",
            "Hydrated": "Hydration status.",
            "Energy": "Available physical and mental energy.",
            "Mood": "Current emotional tone.",
            "Focus": "Ability to concentrate.",
            "Calm": "Stress balance and calmness.",
            "Entertainment": "Healthy entertainment and decompression.",
        }
        return {
            name: StatusDefinition.objects.update_or_create(
                name=name,
                defaults={"description": description},
            )[0]
            for name, description in descriptions.items()
        }

    def _seed_sample_activities(
        self, definitions: dict[str, ActivityDefinition]
    ) -> None:
        samples = (
            ("Coding", 60, "VS Code", time(9, 0)),
            ("Technical research", 30, "Chrome", time(11, 0)),
            ("Reading", 45, "Kindle", time(18, 0)),
            ("Fitness training", 20, "Fitness training", time(19, 0)),
            ("Watching tutorial", 15, "YouTube", time(20, 0)),
        )
        for definition_name, minutes, source, started_time in samples:
            started_at = self._today_at(started_time)
            exists = ActivityEntry.objects.filter(
                activity_definition=definitions[definition_name],
                source=source,
                started_at=started_at,
            ).exists()
            if not exists:
                create_activity_entry(
                    activity_definition=definitions[definition_name],
                    minutes=minutes,
                    source=source,
                    started_at=started_at,
                )

    def _seed_status_entries(
        self, statuses: dict[str, StatusDefinition]
    ) -> None:
        values = {
            "Rested": 70,
            "Fed": 75,
            "Hydrated": 65,
            "Energy": 68,
            "Mood": 72,
            "Focus": 74,
            "Calm": 66,
            "Entertainment": 45,
        }
        recorded_at = self._today_at(time(8, 0))
        for name, value in values.items():
            StatusEntry.objects.update_or_create(
                status_definition=statuses[name],
                recorded_at=recorded_at,
                defaults={"value": value, "note": "Seed sample"},
            )

    def _seed_journal_entries(self) -> None:
        entry_date = timezone.localdate()
        entries = (
            (
                1,
                "First Entry",
                JournalEntryType.MANUAL,
                JournalMood.FOCUSED,
                "Started the Life RPG system and created the first baseline.",
                "I built the foundation instead of only planning it.",
                "Keeping scope tight while adding RPG depth.",
                "Small systems become real when they collect real actions.",
                "Define the next screen before expanding mechanics.",
                "I moved closer by making progress visible.",
                ["learning", "systems", "discipline"],
            ),
            (
                2,
                "Weekly Reflection",
                JournalEntryType.SYSTEM,
                JournalMood.BALANCED,
                "Reviewed the first week of progress and prepared the next steps.",
                "The system now has a rhythm.",
                "There are still many modules to connect.",
                "A useful MVP needs fewer fake panels and more real data.",
                "Focus on one module at a time.",
                "I clarified the next implementation path.",
                ["planning", "reflection"],
            ),
        )
        for (
            source_id,
            title,
            entry_type,
            mood,
            content,
            reflection_proud,
            reflection_challenge,
            reflection_learned,
            reflection_improve,
            reflection_goal_action,
            tags,
        ) in entries:
            JournalEntry.objects.update_or_create(
                source_type="seed",
                source_id=source_id,
                defaults={
                    "title": title,
                    "content": content,
                    "entry_type": entry_type,
                    "mood": mood,
                    "reflection_proud": reflection_proud,
                    "reflection_challenge": reflection_challenge,
                    "reflection_learned": reflection_learned,
                    "reflection_improve": reflection_improve,
                    "reflection_goal_action": reflection_goal_action,
                    "tags": tags,
                    "entry_date": entry_date,
                },
            )

    def _seed_character_identities(self) -> None:
        today = timezone.localdate()
        CharacterIdentity.objects.update_or_create(
            is_active=True,
            defaults={
                "title": "Builder",
                "description": "I am becoming someone who builds systems and follows through.",
                "started_on": today,
                "ended_on": None,
            },
        )

    def _seed_calendar_events(self) -> None:
        events = (
            (
                1,
                "Weekly planning",
                "Review quests, habits, and priorities for the week.",
                time(9, 0),
                time(9, 45),
                CalendarEventType.RPG,
            ),
            (
                2,
                "Training block",
                "Protected time for physical training.",
                time(18, 0),
                time(19, 0),
                CalendarEventType.HEALTH,
            ),
        )
        for source_id, title, description, start_time, end_time, event_type in events:
            CalendarEvent.objects.update_or_create(
                source_type="seed",
                source_id=source_id,
                defaults={
                    "title": title,
                    "description": description,
                    "start_at": self._today_at(start_time),
                    "end_at": self._today_at(end_time),
                    "all_day": False,
                    "event_type": event_type,
                },
            )
