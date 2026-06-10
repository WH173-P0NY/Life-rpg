import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from activities.models import ActivityDefinition, ActivityReward
from activities.services import create_activity_entry
from dashboard.models import LlmProviderConfig
from rpg.choices import TargetUnit
from rpg.models import Habit, JournalEntry, Quest, QuestReward
from rpg.services import complete_quest, toggle_habit
from skills.models import LifeArea, Skill, XpEvent


def _local_datetime(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(hour=9)))


def _create_rewarded_activity(
    *,
    day: date,
    minutes: int,
    xp_per_minute: int = 5,
) -> ActivityDefinition:
    area, _ = LifeArea.objects.get_or_create(name="Craft & Work")
    skill, _ = Skill.objects.get_or_create(name="Programming", life_area=area)
    definition, _ = ActivityDefinition.objects.get_or_create(
        name="Coding",
        life_area=area,
    )
    ActivityReward.objects.get_or_create(
        activity_definition=definition,
        skill=skill,
        defaults={"xp_per_minute": xp_per_minute},
    )
    create_activity_entry(
        activity_definition=definition,
        minutes=minutes,
        started_at=_local_datetime(day),
        source="api range test",
    )
    return definition


class ReactShellViewTests(TestCase):
    def test_react_shell_returns_developer_message_when_build_is_missing(self) -> None:
        with TemporaryDirectory() as tmpdir:
            missing_build_dir = Path(tmpdir) / "missing-dist"

            with override_settings(REACT_BUILD_DIR=missing_build_dir):
                response = self.client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response["Content-Type"].startswith("text/plain"))
        self.assertContains(
            response,
            "React build not found",
            status_code=503,
        )
        self.assertContains(response, "npm run build", status_code=503)
        self.assertContains(response, "http://127.0.0.1:5173/", status_code=503)

    def test_react_shell_serves_index_html_when_build_exists(self) -> None:
        with TemporaryDirectory() as tmpdir:
            build_dir = Path(tmpdir)
            (build_dir / "index.html").write_text(
                (
                    "<!doctype html><html><head>"
                    '<script type="module" src="/assets/app.js"></script>'
                    '<link rel="stylesheet" href="/assets/app.css">'
                    "</head><body><div id=\"root\"></div></body></html>"
                ),
                encoding="utf-8",
            )

            with override_settings(REACT_BUILD_DIR=build_dir):
                response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/html"))
        self.assertContains(response, '<div id="root"></div>')
        self.assertContains(response, "/static/frontend/assets/app.js")
        self.assertContains(response, "/static/frontend/assets/app.css")

    def test_dashboard_api_still_returns_json_under_api_prefix(self) -> None:
        response = self.client.get("/api/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        self.assertEqual(response.json()["hero"]["name"], "Username")


class DashboardViewTests(TestCase):
    def test_dashboard_works_on_empty_database(self) -> None:
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No skills yet")

    def test_dashboard_shows_seed_data(self) -> None:
        call_command("seed_life_rpg")

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Programming")
        self.assertContains(response, "Entertainment")

    def test_dashboard_renders_theme_switcher(self) -> None:
        call_command("seed_life_rpg")

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-theme-select')
        self.assertContains(response, "Minimal Dark RPG")
        self.assertContains(response, "Cyberpunk Life RPG")
        self.assertContains(response, "Living World")
        self.assertContains(response, "adventurers-journal")
        self.assertContains(response, "Legendary Hero")
        self.assertContains(response, "Today's Quests")
        self.assertContains(response, "Active Challenge")
        self.assertContains(response, "Attributes")
        self.assertContains(response, "Journal")
        self.assertContains(response, "data-quest-item")
        self.assertContains(response, "data-habit-dot")
        self.assertContains(response, "data-feedback-layer")

    def test_dashboard_api_returns_json_payload_on_empty_database(self) -> None:
        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stats"]["total_xp"], 0)
        self.assertEqual(payload["hero"]["name"], "Username")
        self.assertEqual(payload["selected_range"]["key"], "today")
        self.assertEqual(payload["skill_rows"], [])
        self.assertEqual(payload["latest_statuses"], [])
        self.assertIn("activity_definitions", payload)
        self.assertIn("daily_quests", payload)
        self.assertIn("weekly_progress", payload)

    def test_dashboard_api_uses_existing_username_for_hero_name(self) -> None:
        get_user_model().objects.create_user(username="local-user")

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["hero"]["name"], "local-user")

    def test_dashboard_api_replaces_legacy_warrior_username(self) -> None:
        get_user_model().objects.create_user(username="wojownik")

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["hero"]["name"], "Username")

    def test_dashboard_api_returns_rpg_quests_with_real_ids(self) -> None:
        skill = Skill.objects.create(name="Reading")
        quest = Quest.objects.create(
            title="Read API contract",
            target_value=20,
            target_unit=TargetUnit.MINUTES,
        )
        QuestReward.objects.create(quest=quest, skill=skill, xp_amount=20)

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        quests = response.json()["daily_quests"]
        self.assertEqual(len(quests), 1)
        self.assertEqual(quests[0]["id"], quest.id)
        self.assertEqual(quests[0]["title"], "Read API contract")
        self.assertIsNone(quests[0]["completion_id"])
        self.assertEqual(quests[0]["progress_value"], 0)
        self.assertEqual(quests[0]["target_value"], 20)
        self.assertEqual(quests[0]["target_unit"], TargetUnit.MINUTES)
        self.assertEqual(quests[0]["progress_percent"], 0)
        self.assertFalse(quests[0]["completed"])
        self.assertEqual(quests[0]["current"], 0)
        self.assertEqual(quests[0]["target"], 20)
        self.assertEqual(quests[0]["unit"], TargetUnit.MINUTES)
        self.assertEqual(quests[0]["progress"], 0)

    def test_dashboard_api_returns_completed_rpg_quest_progress(self) -> None:
        reading = Skill.objects.create(name="Reading")
        learning = Skill.objects.create(name="Learning")
        quest = Quest.objects.create(
            title="Complete daily reading",
            target_value=20,
            target_unit=TargetUnit.MINUTES,
        )
        QuestReward.objects.create(quest=quest, skill=reading, xp_amount=20)
        QuestReward.objects.create(quest=quest, skill=learning, xp_amount=5)
        completion = complete_quest(
            quest=quest,
            completed_on=timezone.localdate(),
        )

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        quest_row = response.json()["daily_quests"][0]
        self.assertEqual(quest_row["id"], quest.id)
        self.assertEqual(quest_row["completion_id"], completion.id)
        self.assertEqual(quest_row["progress_value"], 20)
        self.assertEqual(quest_row["target_value"], 20)
        self.assertEqual(quest_row["progress_percent"], 100)
        self.assertIsNotNone(quest_row["completed_at"])
        self.assertTrue(quest_row["completed"])
        self.assertEqual(quest_row["reward_xp"], 25)

    def test_dashboard_api_returns_rpg_habits_with_check_in_state(self) -> None:
        habit = Habit.objects.create(name="Hydrate")
        result = toggle_habit(
            habit=habit,
            checked_on=timezone.localdate(),
        )

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        habits = payload["habits"]
        self.assertEqual(len(habits), 1)
        self.assertEqual(habits[0]["id"], habit.id)
        self.assertEqual(habits[0]["name"], "Hydrate")
        self.assertEqual(habits[0]["label"], "Hydrate")
        self.assertTrue(habits[0]["completed_today"])
        self.assertTrue(habits[0]["completed"])
        self.assertTrue(habits[0]["checked"])
        self.assertEqual(habits[0]["check_in_id"], result["check_in"].id)
        self.assertEqual(habits[0]["check_in"]["id"], result["check_in"].id)
        self.assertEqual(
            habits[0]["check_in"]["checked_on"],
            timezone.localdate().isoformat(),
        )
        self.assertEqual(habits[0]["streak_days"], result["streak_days"])
        self.assertEqual(payload["habits_summary"]["completed"], 1)
        self.assertEqual(payload["habits_summary"]["total"], 1)
        self.assertEqual(
            payload["habits_summary"]["streak_days"],
            result["streak_days"],
        )

    def test_dashboard_api_uses_empty_challenge_and_achievements_until_later_modules(self) -> None:
        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["active_challenge"])
        self.assertEqual(payload["achievements"], [])
        self.assertEqual(payload["journal_entries"], [])

    def test_dashboard_api_returns_recent_journal_entries_from_range(self) -> None:
        today = timezone.localdate()
        old_entry = JournalEntry.objects.create(
            title="Old reflection",
            content="Outside range",
            entry_date=today - timedelta(days=1),
        )
        current_entry = JournalEntry.objects.create(
            title="Daily reflection",
            content="Today I completed every quest.",
            mood="focused",
            entry_date=today,
        )

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        entries = response.json()["journal_entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], current_entry.id)
        self.assertEqual(entries[0]["title"], "Daily reflection")
        self.assertEqual(entries[0]["content"], "Today I completed every quest.")
        self.assertEqual(entries[0]["body"], "Today I completed every quest.")
        self.assertEqual(entries[0]["entry_type"], "manual")
        self.assertEqual(entries[0]["mood"], "focused")
        self.assertEqual(entries[0]["entry_date"], today.isoformat())
        self.assertNotEqual(entries[0]["id"], old_entry.id)

    def test_dashboard_api_sets_csrf_cookie(self) -> None:
        dashboard_response = self.client.get(reverse("dashboard:dashboard_api"))
        csrf_response = self.client.get(reverse("dashboard:csrf_api"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(csrf_response.status_code, 200)
        self.assertIn("csrftoken", dashboard_response.cookies)
        self.assertIn("csrftoken", csrf_response.cookies)
        self.assertEqual(csrf_response.json(), {"ok": True})

    def test_dashboard_api_supports_week_month_and_custom_ranges(self) -> None:
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        next_month = (
            month_start.replace(year=month_start.year + 1, month=1)
            if month_start.month == 12
            else month_start.replace(month=month_start.month + 1)
        )
        month_end = next_month - timedelta(days=1)
        created_entries = (
            (week_start, 6),
            (month_start, 8),
            (today, 10),
        )

        for day, minutes in created_entries:
            _create_rewarded_activity(day=day, minutes=minutes)

        week_response = self.client.get(
            reverse("dashboard:dashboard_api"),
            {"range": "week"},
        )
        month_response = self.client.get(
            reverse("dashboard:dashboard_api"),
            {"range": "month"},
        )
        custom_response = self.client.get(
            reverse("dashboard:dashboard_api"),
            {
                "range": "custom",
                "start": month_start.isoformat(),
                "end": month_start.isoformat(),
            },
        )

        self.assertEqual(week_response.status_code, 200)
        self.assertEqual(month_response.status_code, 200)
        self.assertEqual(custom_response.status_code, 200)

        week_payload = week_response.json()
        month_payload = month_response.json()
        custom_payload = custom_response.json()

        expected_week_xp = sum(
            minutes * 5
            for day, minutes in created_entries
            if week_start <= day <= week_end
        )
        expected_month_xp = sum(
            minutes * 5
            for day, minutes in created_entries
            if month_start <= day <= month_end
        )
        expected_custom_xp = sum(
            minutes * 5 for day, minutes in created_entries if day == month_start
        )

        self.assertEqual(week_payload["selected_range"]["key"], "week")
        self.assertEqual(week_payload["selected_range"]["start_date"], week_start.isoformat())
        self.assertEqual(week_payload["selected_range"]["end_date"], week_end.isoformat())
        self.assertEqual(week_payload["stats"]["range_xp"], expected_week_xp)
        self.assertEqual(len(week_payload["xp_chart"]["labels"]), 7)

        self.assertEqual(month_payload["selected_range"]["key"], "month")
        self.assertEqual(month_payload["selected_range"]["start_date"], month_start.isoformat())
        self.assertEqual(month_payload["selected_range"]["end_date"], month_end.isoformat())
        self.assertEqual(month_payload["stats"]["range_xp"], expected_month_xp)

        self.assertEqual(custom_payload["selected_range"]["key"], "custom")
        self.assertEqual(custom_payload["selected_range"]["start_date"], month_start.isoformat())
        self.assertEqual(custom_payload["selected_range"]["end_date"], month_start.isoformat())
        self.assertEqual(custom_payload["stats"]["range_xp"], expected_custom_xp)

    def test_dashboard_api_falls_back_to_today_for_invalid_custom_range(self) -> None:
        response = self.client.get(
            reverse("dashboard:dashboard_api"),
            {"range": "custom", "start": "not-a-date", "end": "2026-06-10"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["selected_range"]["key"], "today")
        self.assertEqual(
            payload["selected_range"]["start_date"],
            timezone.localdate().isoformat(),
        )

    def test_dashboard_api_serializes_seed_data(self) -> None:
        call_command("seed_life_rpg")

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        skill_names = {row["name"] for row in payload["skill_rows"]}
        status_names = {
            row["definition"]["name"] for row in payload["latest_statuses"]
        }
        activity_names = {
            row["name"] for row in payload["activity_definitions"]
        }
        self.assertIn("Programming", skill_names)
        self.assertIn("Entertainment", status_names)
        self.assertIn("Coding", activity_names)
        self.assertGreaterEqual(len(payload["journal_entries"]), 2)

    def test_manual_activity_form_creates_activity_and_xp(self) -> None:
        area = LifeArea.objects.create(name="Craft & Work")
        skill = Skill.objects.create(name="Programming", life_area=area)
        definition = ActivityDefinition.objects.create(name="Coding", life_area=area)
        ActivityReward.objects.create(
            activity_definition=definition,
            skill=skill,
            xp_per_minute=5,
        )

        started_at = timezone.localtime(timezone.now()).replace(
            second=0,
            microsecond=0,
        )
        response = self.client.post(
            reverse("dashboard:index"),
            data={
                "activity_definition": definition.id,
                "minutes": 10,
                "started_at": started_at.strftime("%Y-%m-%dT%H:%M"),
                "source": "manual test",
            },
        )

        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertEqual(XpEvent.objects.count(), 1)
        self.assertEqual(XpEvent.objects.get().amount, 50)

    def test_manual_activity_api_creates_activity_and_xp(self) -> None:
        area = LifeArea.objects.create(name="Craft & Work")
        skill = Skill.objects.create(name="Programming", life_area=area)
        definition = ActivityDefinition.objects.create(name="Coding", life_area=area)
        ActivityReward.objects.create(
            activity_definition=definition,
            skill=skill,
            xp_per_minute=5,
        )

        started_at = timezone.localtime(timezone.now()).replace(
            second=0,
            microsecond=0,
        )
        response = self.client.post(
            reverse("dashboard:manual_activity_api"),
            data=json.dumps(
                {
                    "activity_definition_id": definition.id,
                    "minutes": 10,
                    "started_at": started_at.strftime("%Y-%m-%dT%H:%M"),
                    "source": "react dashboard",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["entry"]["activity_definition"]["name"], "Coding")
        self.assertEqual(payload["entry"]["source"], "react dashboard")
        self.assertEqual(payload["entry"]["total_xp"], 50)
        self.assertEqual(
            payload["entry"]["xp_events"][0]["skill"]["name"],
            "Programming",
        )
        self.assertEqual(XpEvent.objects.count(), 1)
        self.assertEqual(XpEvent.objects.get().amount, 50)

    def test_manual_activity_api_accepts_json_post_with_csrf(self) -> None:
        definition = _create_rewarded_activity(day=timezone.localdate(), minutes=1)
        XpEvent.objects.all().delete()
        definition.entries.all().delete()

        client = Client(enforce_csrf_checks=True)
        csrf_response = client.get(reverse("dashboard:csrf_api"))
        csrf_token = csrf_response.cookies["csrftoken"].value

        response = client.post(
            reverse("dashboard:manual_activity_api"),
            data=json.dumps(
                {
                    "activityDefinitionId": definition.id,
                    "minutes": 12,
                    "startedAt": timezone.localtime(timezone.now()).strftime(
                        "%Y-%m-%dT%H:%M"
                    ),
                    "source": "vite proxy",
                }
            ),
            content_type="application/json",
            HTTP_ORIGIN="http://127.0.0.1:5173",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["entry"]["total_xp"], 60)
        self.assertEqual(XpEvent.objects.count(), 1)

    def test_manual_activity_api_rejects_invalid_payload(self) -> None:
        response = self.client.post(
            reverse("dashboard:manual_activity_api"),
            data=json.dumps({"minutes": 0}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("activity_definition", payload["errors"])
        self.assertIn("minutes", payload["errors"])

    def test_manual_activity_api_rejects_non_object_json_payload(self) -> None:
        response = self.client.post(
            reverse("dashboard:manual_activity_api"),
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("activity_definition", payload["errors"])
        self.assertIn("minutes", payload["errors"])


class AppSettingsApiTests(TestCase):
    def test_app_settings_endpoint_returns_account_catalogs_and_llm_configs(self) -> None:
        response = self.client.get(reverse("dashboard:app_settings_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("account", payload)
        self.assertEqual(
            {provider["provider"] for provider in payload["llm_providers"]},
            {"chatgpt", "claude", "gemini"},
        )
        self.assertIn("skills", payload)
        self.assertIn("activity_definitions", payload)

    def test_account_settings_updates_local_user(self) -> None:
        user = get_user_model().objects.create_user(username="old-name")

        response = self.client.post(
            reverse("dashboard:account_settings_api"),
            data=json.dumps({"username": "new-name", "password": "strong-pass-123"}),
            content_type="application/json",
        )
        user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.username, "new-name")
        self.assertTrue(user.check_password("strong-pass-123"))

    def test_llm_settings_endpoint_stores_keys_without_returning_raw_value(self) -> None:
        response = self.client.post(
            reverse("dashboard:llm_settings_api"),
            data=json.dumps(
                {
                    "providers": [
                        {
                            "provider": "chatgpt",
                            "model_name": "gpt-4.1",
                            "api_key": "sk-test-secret",
                            "is_enabled": True,
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        config = LlmProviderConfig.objects.get(provider="chatgpt")
        provider = response.json()["llm_providers"][0]
        self.assertEqual(config.model_name, "gpt-4.1")
        self.assertEqual(config.api_key, "sk-test-secret")
        self.assertTrue(provider["api_key_set"])
        self.assertNotEqual(provider["api_key_preview"], "sk-test-secret")

    def test_skills_endpoint_creates_skill(self) -> None:
        area = LifeArea.objects.create(name="Craft")

        response = self.client.post(
            reverse("dashboard:skills_api"),
            data=json.dumps({"name": "Public Speaking", "life_area_id": area.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["skill"]["name"], "Public Speaking")
        self.assertEqual(Skill.objects.get().life_area, area)

    def test_activity_definitions_endpoint_creates_definition_with_multiple_rewards(self) -> None:
        first_skill = Skill.objects.create(name="Programming")
        second_skill = Skill.objects.create(name="Writing")

        response = self.client.post(
            reverse("dashboard:activity_definitions_api"),
            data=json.dumps(
                {
                    "name": "Build product",
                    "description": "Focused project work",
                    "rewards": [
                        {"skill_id": first_skill.id, "xp_per_minute": 2},
                        {"skill_id": second_skill.id, "xp_per_minute": 1},
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ActivityDefinition.objects.count(), 1)
        self.assertEqual(ActivityReward.objects.count(), 2)
        self.assertEqual(
            len(response.json()["activity_definition"]["rewards"]),
            2,
        )
