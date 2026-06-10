from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from planner.models import CalendarEvent
from skills.models import LifeArea, Skill, XpEvent
from statuses.models import StatusDefinition

from .models import ActivityDefinition, ActivityEntry, ActivityReward
from .services import create_activity_entry


class ActivityServiceTests(TestCase):
    def setUp(self) -> None:
        area = LifeArea.objects.create(name="Craft & Work")
        self.programming = Skill.objects.create(name="Programming", life_area=area)
        self.learning = Skill.objects.create(name="Learning", life_area=area)
        self.definition = ActivityDefinition.objects.create(
            name="Coding",
            life_area=area,
        )
        ActivityReward.objects.create(
            activity_definition=self.definition,
            skill=self.programming,
            xp_per_minute=5,
        )
        ActivityReward.objects.create(
            activity_definition=self.definition,
            skill=self.learning,
            xp_per_minute=1,
        )

    def test_activity_creates_xp_event_for_every_rewarded_skill(self) -> None:
        entry = create_activity_entry(
            activity_definition=self.definition,
            minutes=30,
            started_at=timezone.now(),
            source="VS Code",
        )

        events = XpEvent.objects.order_by("skill__name")
        self.assertEqual(events.count(), 2)
        self.assertEqual(
            {(event.skill.name, event.amount) for event in events},
            {("Learning", 30), ("Programming", 150)},
        )
        self.assertEqual(entry.total_xp(), 180)

    def test_activity_rejects_non_positive_minutes(self) -> None:
        with self.assertRaises(ValueError):
            create_activity_entry(
                activity_definition=self.definition,
                minutes=0,
                started_at=timezone.now(),
            )


class SeedLifeRpgTests(TestCase):
    def test_seed_is_idempotent_and_keeps_entertainment_as_status(self) -> None:
        call_command("seed_life_rpg")
        counts_after_first_run = {
            "skills": Skill.objects.count(),
            "definitions": ActivityDefinition.objects.count(),
            "entries": ActivityEntry.objects.count(),
            "events": XpEvent.objects.count(),
            "statuses": StatusDefinition.objects.count(),
            "calendar_events": CalendarEvent.objects.count(),
        }

        call_command("seed_life_rpg")

        self.assertEqual(Skill.objects.count(), counts_after_first_run["skills"])
        self.assertEqual(
            ActivityDefinition.objects.count(),
            counts_after_first_run["definitions"],
        )
        self.assertEqual(
            ActivityEntry.objects.count(),
            counts_after_first_run["entries"],
        )
        self.assertEqual(XpEvent.objects.count(), counts_after_first_run["events"])
        self.assertEqual(
            StatusDefinition.objects.count(),
            counts_after_first_run["statuses"],
        )
        self.assertEqual(
            CalendarEvent.objects.count(),
            counts_after_first_run["calendar_events"],
        )
        self.assertEqual(CalendarEvent.objects.count(), 2)
        self.assertTrue(StatusDefinition.objects.filter(name="Entertainment").exists())
        self.assertFalse(Skill.objects.filter(name="Entertainment").exists())
