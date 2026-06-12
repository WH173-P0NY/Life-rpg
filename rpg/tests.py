from __future__ import annotations

import json
from datetime import date, timedelta
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activities.models import ActivityDefinition, ActivityReward
from activities.services import create_activity_entry
from skills.models import LifeArea, Skill, XpEvent

from .choices import (
    AchievementRarity,
    AchievementTrigger,
    CampaignCreatedBy,
    CampaignDifficulty,
    CampaignNodeKind,
    CampaignQuestUnlockMode,
    CampaignStatus,
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
from .exceptions import (
    ChallengeNotActiveError,
    ChallengeNotCompletableError,
    HabitNotActiveError,
    QuestAlreadyCompletedError,
    QuestNotActiveError,
    QuestNotAvailableError,
    RpgValidationError,
)
from .models import (
    Achievement,
    AchievementUnlock,
    Campaign,
    CampaignQuest,
    CampaignQuestDependency,
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
    HabitMilestoneReward,
    HabitMilestoneUnlock,
    JournalEntry,
    Quest,
    QuestCompletion,
    QuestReward,
)
from .campaign_services import (
    activate_campaign,
    add_quest_to_campaign,
    bulk_update_campaign_node_positions,
    complete_campaign_if_ready,
    create_campaign_edge,
    create_campaign_node,
    create_campaign,
    delete_campaign_node,
    generate_campaign_draft,
    get_campaign_detail,
    serialize_campaign_studio,
    set_campaign_dependencies,
    update_campaign_node,
    validate_campaign_studio,
)
from .services import (
    build_daily_quest_rows,
    build_achievement_rows,
    build_challenge_rows,
    build_goal_rows,
    build_habit_rows,
    build_journal_overview,
    build_journal_entry_rows,
    calculate_habit_streak,
    complete_challenge,
    complete_goal,
    complete_quest,
    create_journal_entry,
    create_system_journal_entry,
    fail_challenge,
    get_active_challenge,
    toggle_habit,
    toggle_challenge_check_in,
    update_journal_entry,
    update_goal_progress,
    update_quest_progress,
)


class RpgFoundationTests(TestCase):
    def test_rpg_app_is_installed(self) -> None:
        self.assertTrue(apps.is_installed("rpg"))

    def test_rpg_urls_import_with_quest_endpoints(self) -> None:
        urlconf = import_module("rpg.urls")

        self.assertEqual(urlconf.app_name, "rpg")
        self.assertGreaterEqual(len(urlconf.urlpatterns), 2)

    def test_existing_dashboard_api_routes_still_reverse(self) -> None:
        self.assertEqual(reverse("dashboard:dashboard_api"), "/api/dashboard/")
        self.assertEqual(reverse("dashboard:csrf_api"), "/api/csrf/")
        self.assertEqual(
            reverse("dashboard:manual_activity_api"),
            "/api/activities/manual/",
        )

    def test_daily_rpg_timezone_is_local(self) -> None:
        self.assertEqual(settings.TIME_ZONE, "Europe/Warsaw")

    def test_module_1_2_choices_are_available(self) -> None:
        self.assertEqual(QuestType.DAILY, "daily")
        self.assertEqual(QuestStatus.DRAFT, "draft")
        self.assertEqual(QuestDifficulty.NORMAL, "normal")
        self.assertEqual(CampaignStatus.DRAFT, "draft")
        self.assertEqual(CampaignCreatedBy.AI, "ai")
        self.assertEqual(CampaignDifficulty.LEGENDARY, "legendary")
        self.assertEqual(CampaignNodeKind.MILESTONE, "milestone")
        self.assertEqual(CampaignQuestUnlockMode.IMMEDIATE, "immediate")
        self.assertEqual(CreationSource.AI, "ai")
        self.assertEqual(TargetUnit.MINUTES, "minutes")
        self.assertEqual(HabitFrequency.WEEKLY, "weekly")
        self.assertEqual(JournalEntryType.MANUAL, "manual")
        self.assertEqual(JournalMood.READY_FOR_BATTLE, "ready_for_battle")


class QuestModelTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Reading")
        self.quest = Quest.objects.create(
            title="Read 20 minutes",
            target_value=20,
            target_unit=TargetUnit.MINUTES,
        )

    def test_quest_clean_rejects_empty_title(self) -> None:
        quest = Quest(title="  ", target_value=1)

        with self.assertRaises(ValidationError):
            quest.full_clean()

    def test_quest_clean_rejects_non_positive_target_value(self) -> None:
        quest = Quest(title="Invalid target", target_value=0)

        with self.assertRaises(ValidationError):
            quest.full_clean()

    def test_quest_clean_rejects_invalid_availability_range(self) -> None:
        quest = Quest(
            title="Invalid range",
            target_value=1,
            available_from=date(2026, 6, 11),
            available_until=date(2026, 6, 10),
        )

        with self.assertRaises(ValidationError):
            quest.full_clean()

    def test_ai_created_quest_must_start_as_draft(self) -> None:
        quest = Quest(
            title="AI quest",
            target_value=1,
            created_by=CreationSource.AI,
            status=QuestStatus.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            quest.full_clean()

    def test_quest_reward_requires_positive_xp(self) -> None:
        reward = QuestReward(quest=self.quest, skill=self.skill, xp_amount=0)

        with self.assertRaises(ValidationError):
            reward.full_clean()

    def test_quest_reward_is_unique_per_quest_and_skill(self) -> None:
        QuestReward.objects.create(quest=self.quest, skill=self.skill, xp_amount=10)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestReward.objects.create(
                    quest=self.quest,
                    skill=self.skill,
                    xp_amount=5,
                )

    def test_completion_is_unique_per_quest_and_day(self) -> None:
        day = date(2026, 6, 10)
        QuestCompletion.objects.create(quest=self.quest, completed_on=day)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestCompletion.objects.create(quest=self.quest, completed_on=day)


class QuestServiceTests(TestCase):
    def setUp(self) -> None:
        area = LifeArea.objects.create(name="Mind & Learning")
        self.reading = Skill.objects.create(name="Reading", life_area=area)
        self.learning = Skill.objects.create(name="Learning", life_area=area)
        self.quest = Quest.objects.create(
            title="Read 20 minutes",
            target_value=20,
            target_unit=TargetUnit.MINUTES,
        )
        QuestReward.objects.create(
            quest=self.quest,
            skill=self.reading,
            xp_amount=20,
        )
        QuestReward.objects.create(
            quest=self.quest,
            skill=self.learning,
            xp_amount=5,
        )

    def test_complete_quest_creates_completion_and_xp_events_per_reward(self) -> None:
        completion = complete_quest(
            quest=self.quest,
            completed_on=date(2026, 6, 10),
        )

        self.assertEqual(completion.progress_value, 20)
        self.assertIsNotNone(completion.completed_at)
        self.assertIsNotNone(completion.xp_awarded_at)
        self.assertEqual(XpEvent.objects.count(), 2)
        event_rows = {
            (event.skill.name, event.amount, event.source_type)
            for event in XpEvent.objects.all()
        }
        self.assertEqual(event_rows, {("Reading", 20, "quest"), ("Learning", 5, "quest")})
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.get().source_type,
            "quest_completion",
        )

    def test_complete_quest_unlocks_quest_count_achievement_once(self) -> None:
        achievement = Achievement.objects.create(
            code="first-quest",
            title="First Quest",
            trigger_type=AchievementTrigger.QUEST_COUNT,
            trigger_config={"quest_count": 1},
        )

        completion = complete_quest(
            quest=self.quest,
            completed_on=date(2026, 6, 10),
        )
        complete_quest(
            quest=self.quest,
            completed_on=date(2026, 6, 10),
        )

        unlock = AchievementUnlock.objects.get(achievement=achievement)
        self.assertEqual(unlock.source_type, "quest_completion")
        self.assertEqual(unlock.source_id, completion.id)
        self.assertEqual(AchievementUnlock.objects.count(), 1)
        self.assertEqual(XpEvent.objects.count(), 2)

    def test_repeated_daily_completion_does_not_duplicate_xp(self) -> None:
        day = date(2026, 6, 10)
        first = complete_quest(quest=self.quest, completed_on=day)
        second = complete_quest(quest=self.quest, completed_on=day)

        self.assertEqual(first.id, second.id)
        self.assertEqual(QuestCompletion.objects.count(), 1)
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_one_time_quest_cannot_be_completed_twice(self) -> None:
        self.quest.quest_type = QuestType.ONE_TIME
        self.quest.save(update_fields=["quest_type", "updated_at"])

        complete_quest(quest=self.quest, completed_on=date(2026, 6, 10))

        with self.assertRaises(QuestAlreadyCompletedError):
            complete_quest(quest=self.quest, completed_on=date(2026, 6, 11))
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_inactive_quest_cannot_be_completed(self) -> None:
        self.quest.status = QuestStatus.ARCHIVED
        self.quest.save(update_fields=["status", "updated_at"])

        with self.assertRaises(QuestNotActiveError):
            complete_quest(quest=self.quest, completed_on=date(2026, 6, 10))

        self.assertEqual(XpEvent.objects.count(), 0)

    def test_unavailable_quest_cannot_be_completed(self) -> None:
        self.quest.available_from = date(2026, 6, 11)
        self.quest.save(update_fields=["available_from", "updated_at"])

        with self.assertRaises(QuestNotAvailableError):
            complete_quest(quest=self.quest, completed_on=date(2026, 6, 10))

        self.assertEqual(XpEvent.objects.count(), 0)

    def test_update_progress_saves_partial_progress_without_xp(self) -> None:
        completion = update_quest_progress(
            quest=self.quest,
            progress_value=12,
            completed_on=date(2026, 6, 10),
        )

        self.assertEqual(completion.progress_value, 12)
        self.assertIsNone(completion.completed_at)
        self.assertEqual(XpEvent.objects.count(), 0)

    def test_update_progress_reaching_target_awards_xp_once(self) -> None:
        day = date(2026, 6, 10)
        completion = update_quest_progress(
            quest=self.quest,
            progress_value=20,
            completed_on=day,
        )
        repeated = update_quest_progress(
            quest=self.quest,
            progress_value=25,
            completed_on=day,
        )

        self.assertEqual(completion.id, repeated.id)
        self.assertIsNotNone(repeated.completed_at)
        self.assertEqual(repeated.progress_value, 25)
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_update_progress_unlocks_achievement_only_when_quest_completes(self) -> None:
        achievement = Achievement.objects.create(
            code="progress-quest",
            title="Progress Quest",
            trigger_type=AchievementTrigger.QUEST_COUNT,
            trigger_config={"quest_count": 1},
        )
        day = date(2026, 6, 10)

        update_quest_progress(
            quest=self.quest,
            progress_value=10,
            completed_on=day,
        )
        self.assertFalse(
            AchievementUnlock.objects.filter(achievement=achievement).exists()
        )

        completion = update_quest_progress(
            quest=self.quest,
            progress_value=20,
            completed_on=day,
        )
        update_quest_progress(
            quest=self.quest,
            progress_value=25,
            completed_on=day,
        )

        unlock = AchievementUnlock.objects.get(achievement=achievement)
        self.assertEqual(unlock.source_type, "quest_completion")
        self.assertEqual(unlock.source_id, completion.id)
        self.assertEqual(AchievementUnlock.objects.count(), 1)

    def test_build_daily_quest_rows_uses_stable_backend_ids(self) -> None:
        complete_quest(quest=self.quest, completed_on=date(2026, 6, 10))

        rows = build_daily_quest_rows(date(2026, 6, 10))

        self.assertEqual(rows[0]["id"], self.quest.id)
        self.assertEqual(rows[0]["reward_xp"], 25)
        self.assertEqual(rows[0]["progress_value"], 20)
        self.assertEqual(rows[0]["target_value"], 20)
        self.assertEqual(rows[0]["target_unit"], TargetUnit.MINUTES)
        self.assertEqual(rows[0]["progress_percent"], 100)
        self.assertEqual(rows[0]["completion_id"], QuestCompletion.objects.get().id)
        self.assertEqual(
            {reward["name"] for reward in rows[0]["rewards"]},
            {"Reading", "Learning"},
        )
        self.assertEqual(rows[0]["current"], 20)
        self.assertTrue(rows[0]["completed"])


class QuestApiTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Fitness")
        self.quest = Quest.objects.create(
            title="Workout 30 minutes",
            target_value=30,
            target_unit=TargetUnit.MINUTES,
        )
        QuestReward.objects.create(
            quest=self.quest,
            skill=self.skill,
            xp_amount=25,
        )

    def test_complete_endpoint_returns_snake_case_json(self) -> None:
        response = self.client.post(
            reverse("rpg:quest_complete", args=[self.quest.id]),
            data=json.dumps({"completed_on": "2026-06-10"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["quest"]["id"], self.quest.id)
        self.assertEqual(payload["quest"]["target_unit"], "minutes")
        self.assertEqual(payload["quest"]["progress_percent"], 100)
        self.assertEqual(payload["quest"]["completion_id"], payload["completion"]["id"])
        self.assertEqual(payload["quest"]["reward_xp"], 25)
        self.assertEqual(payload["completion"]["completed_on"], "2026-06-10")
        self.assertEqual(payload["xp_events"][0]["source_type"], "quest")

    def test_progress_endpoint_completes_when_target_is_reached(self) -> None:
        response = self.client.post(
            reverse("rpg:quest_progress", args=[self.quest.id]),
            data=json.dumps(
                {
                    "progress_value": 30,
                    "completed_on": "2026-06-10",
                    "note": "finished",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["quest"]["completed"])
        self.assertEqual(payload["completion"]["progress_value"], 30)
        self.assertEqual(XpEvent.objects.count(), 1)

    def test_endpoint_rejects_invalid_json(self) -> None:
        response = self.client.post(
            reverse("rpg:quest_complete", args=[self.quest.id]),
            data="{",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_endpoint_returns_404_for_missing_quest(self) -> None:
        response = self.client.post(
            reverse("rpg:quest_complete", args=[999999]),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_endpoint_returns_conflict_for_completed_one_time_quest(self) -> None:
        self.quest.quest_type = QuestType.ONE_TIME
        self.quest.save(update_fields=["quest_type", "updated_at"])
        complete_quest(quest=self.quest, completed_on=date(2026, 6, 10))

        response = self.client.post(
            reverse("rpg:quest_complete", args=[self.quest.id]),
            data=json.dumps({"completed_on": "2026-06-11"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["error"]["code"],
            "quest_already_completed",
        )


class CampaignServiceTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Programming")
        self.quest_a = self._quest("Define skills", 10)
        self.quest_b = self._quest("Add activity definitions", 20)
        self.quest_c = self._quest("Complete MVP review", 30)
        self.campaign = create_campaign(
            title="Life RPG MVP Arc",
            difficulty=CampaignDifficulty.EPIC,
            reward_xp=100,
            reward_skill_id=self.skill.id,
        )
        self.node_a = add_quest_to_campaign(
            campaign=self.campaign,
            quest=self.quest_a,
            stage="Foundation",
            order=10,
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
            map_x=10,
            map_y=20,
        )
        self.node_b = add_quest_to_campaign(
            campaign=self.campaign,
            quest=self.quest_b,
            stage="Foundation",
            order=20,
            map_x=50,
            map_y=20,
        )
        self.node_c = add_quest_to_campaign(
            campaign=self.campaign,
            quest=self.quest_c,
            stage="Finish",
            order=30,
            map_x=90,
            map_y=20,
        )
        set_campaign_dependencies(
            campaign=self.campaign,
            dependencies=[
                {
                    "campaign_quest_id": self.node_b.id,
                    "depends_on_id": self.node_a.id,
                },
                {
                    "campaign_quest_id": self.node_c.id,
                    "depends_on_id": self.node_b.id,
                },
            ],
        )

    def _quest(self, title: str, reward_xp: int) -> Quest:
        quest = Quest.objects.create(
            title=title,
            quest_type=QuestType.ONE_TIME,
            target_value=1,
            target_unit=TargetUnit.CHECK,
        )
        QuestReward.objects.create(
            quest=quest,
            skill=self.skill,
            xp_amount=reward_xp,
        )
        return quest

    def _node_state(self, campaign: Campaign, node: CampaignQuest) -> str:
        detail = get_campaign_detail(campaign)
        nodes = {row["id"]: row for row in detail["map"]["nodes"]}
        return nodes[node.id]["state"]

    def test_dependency_model_rejects_cross_campaign_edges(self) -> None:
        other_campaign = create_campaign(title="Other")
        other_node = add_quest_to_campaign(
            campaign=other_campaign,
            quest_title="Other quest",
            stage="Other",
        )
        dependency = CampaignQuestDependency(
            campaign_quest=self.node_a,
            depends_on=other_node,
        )

        with self.assertRaises(ValidationError):
            dependency.full_clean()

    def test_cycle_detection_rejects_invalid_graph(self) -> None:
        with self.assertRaises(RpgValidationError):
            set_campaign_dependencies(
                campaign=self.campaign,
                dependencies=[
                    {
                        "campaign_quest_id": self.node_b.id,
                        "depends_on_id": self.node_a.id,
                    },
                    {
                        "campaign_quest_id": self.node_a.id,
                        "depends_on_id": self.node_b.id,
                    },
                ],
            )

    def test_campaign_studio_serializes_nodes_edges_and_validation(self) -> None:
        studio = serialize_campaign_studio(self.campaign)
        nodes_by_id = {node["id"]: node for node in studio["nodes"]}

        self.assertEqual(studio["campaign"]["id"], self.campaign.id)
        self.assertEqual(nodes_by_id[self.node_a.id]["node_kind"], CampaignNodeKind.QUEST)
        self.assertEqual(nodes_by_id[self.node_a.id]["position"], {"x": 10, "y": 20})
        self.assertEqual(studio["edges"][0]["source_node_id"], self.node_a.id)
        self.assertEqual(studio["edges"][0]["target_node_id"], self.node_b.id)
        self.assertTrue(studio["validation"]["valid"])
        self.assertIn(
            {"value": "milestone", "label": "Milestone"},
            studio["available_node_types"],
        )

    def test_campaign_node_services_create_update_position_and_delete_edges(self) -> None:
        node = create_campaign_node(
            campaign=self.campaign,
            node_kind=CampaignNodeKind.MILESTONE,
            title="Review milestone",
            config={"summary_prompt": "What changed?"},
            map_x=120,
            map_y=160,
        )

        self.assertEqual(node.node_kind, CampaignNodeKind.MILESTONE)
        self.assertEqual(node.config["summary_prompt"], "What changed?")

        updated = update_campaign_node(
            campaign=self.campaign,
            node_id=node.id,
            updates={
                "title": "Updated milestone",
                "position": {"x": 240, "y": 260},
                "config": {"summary_prompt": "What improved?"},
            },
        )

        self.assertEqual(updated.quest.title, "Updated milestone")
        self.assertEqual(updated.map_x, 240)
        self.assertEqual(updated.config["summary_prompt"], "What improved?")

        edge = create_campaign_edge(
            campaign=self.campaign,
            source_node_id=self.node_c.id,
            target_node_id=node.id,
        )
        self.assertEqual(edge.depends_on_id, self.node_c.id)

        delete_campaign_node(campaign=self.campaign, node_id=node.id)

        self.assertFalse(CampaignQuest.objects.filter(pk=node.id).exists())
        self.assertFalse(CampaignQuestDependency.objects.filter(pk=edge.id).exists())

    def test_position_updates_are_allowed_for_active_campaigns(self) -> None:
        activate_campaign(campaign=self.campaign)

        nodes = bulk_update_campaign_node_positions(
            campaign=self.campaign,
            positions=[
                {
                    "node_id": self.node_a.id,
                    "position": {"x": 300, "y": 80},
                }
            ],
        )

        updated_by_id = {node.id: node for node in nodes}
        self.assertEqual(updated_by_id[self.node_a.id].map_x, 300)
        self.assertEqual(updated_by_id[self.node_a.id].map_y, 80)

    def test_validate_campaign_studio_reports_empty_campaign_as_invalid(self) -> None:
        empty_campaign = create_campaign(title="Empty")

        validation = validate_campaign_studio(empty_campaign)

        self.assertFalse(validation["valid"])
        self.assertIn(
            "missing_nodes",
            {issue["code"] for issue in validation["issues"]},
        )

    def test_activation_and_availability_follow_dependencies(self) -> None:
        activated = activate_campaign(campaign=self.campaign)

        self.assertEqual(activated.status, CampaignStatus.ACTIVE)
        self.assertEqual(self._node_state(activated, self.node_a), "available")
        self.assertEqual(self._node_state(activated, self.node_b), "locked")

        complete_quest(quest=self.quest_a, completed_on=date(2026, 6, 10))

        self.assertEqual(self._node_state(activated, self.node_a), "completed")
        self.assertEqual(self._node_state(activated, self.node_b), "available")

    def test_completing_all_required_quests_completes_campaign_and_awards_xp_once(self) -> None:
        achievement = Achievement.objects.create(
            code="campaign-finished",
            title="Campaign Finished",
            trigger_type=AchievementTrigger.CAMPAIGN_COMPLETED,
            trigger_config={"campaign_id": self.campaign.id},
        )
        activate_campaign(campaign=self.campaign)

        complete_quest(quest=self.quest_a, completed_on=date(2026, 6, 10))
        complete_quest(quest=self.quest_b, completed_on=date(2026, 6, 10))
        complete_quest(quest=self.quest_c, completed_on=date(2026, 6, 10))
        completed_campaign = Campaign.objects.get(pk=self.campaign.id)
        complete_campaign_if_ready(campaign=completed_campaign)

        self.assertEqual(completed_campaign.status, CampaignStatus.COMPLETED)
        self.assertIsNotNone(completed_campaign.completed_at)
        self.assertIsNotNone(completed_campaign.xp_awarded_at)
        self.assertEqual(
            XpEvent.objects.filter(source_type="campaign").count(),
            1,
        )
        self.assertEqual(
            XpEvent.objects.filter(source_type="campaign").get().amount,
            100,
        )
        self.assertEqual(
            JournalEntry.objects.filter(source_type="campaign", source_id=self.campaign.id).count(),
            1,
        )
        unlock = AchievementUnlock.objects.get(achievement=achievement)
        self.assertEqual(unlock.source_type, "campaign_completion")
        self.assertEqual(unlock.source_id, self.campaign.id)

    def test_generate_campaign_draft_creates_ai_draft_without_activation(self) -> None:
        draft = generate_campaign_draft(
            goal="Learn Django",
            timeframe_days=14,
            available_minutes_per_day=45,
            skill_ids=[self.skill.id],
            difficulty=CampaignDifficulty.NORMAL,
        )

        self.assertEqual(draft.status, CampaignStatus.DRAFT)
        self.assertEqual(draft.created_by, CampaignCreatedBy.AI)
        self.assertEqual(CampaignQuest.objects.filter(campaign=draft).count(), 3)
        self.assertFalse(
            CampaignQuest.objects.filter(campaign=draft, quest__status=QuestStatus.ACTIVE).exists()
        )
        self.assertTrue(
            JournalEntry.objects.filter(
                source_type="campaign_ai_draft",
                source_id=draft.id,
            ).exists()
        )


class CampaignApiTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Learning")

    def test_campaign_create_detail_and_activate_endpoints_return_map(self) -> None:
        create_response = self.client.post(
            reverse("rpg:campaigns"),
            data=json.dumps(
                {
                    "title": "Django Foundations",
                    "difficulty": "normal",
                    "reward_xp": 100,
                    "reward_skill_id": self.skill.id,
                    "quests": [
                        {
                            "title": "Prepare project",
                            "stage": "Setup",
                            "unlock_mode": "immediate",
                            "reward_skill_id": self.skill.id,
                            "reward_xp": 25,
                            "map_x": 20,
                            "map_y": 30,
                        }
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        campaign_id = create_response.json()["campaign"]["id"]
        self.assertEqual(create_response.json()["campaign"]["status"], "draft")
        self.assertEqual(len(create_response.json()["campaign"]["map"]["nodes"]), 1)

        detail_response = self.client.get(
            reverse("rpg:campaign_detail", args=[campaign_id])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            detail_response.json()["campaign"]["map"]["nodes"][0]["state"],
            "locked",
        )

        activate_response = self.client.post(
            reverse("rpg:campaign_activate", args=[campaign_id]),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(activate_response.status_code, 200)
        self.assertEqual(activate_response.json()["campaign"]["status"], "active")
        self.assertEqual(
            activate_response.json()["campaign"]["map"]["nodes"][0]["state"],
            "available",
        )

        list_response = self.client.get(reverse("rpg:campaigns"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["campaigns"][0]["title"], "Django Foundations")

    def test_campaign_dependencies_endpoint_rejects_cycles(self) -> None:
        campaign = create_campaign(title="Cycle test")
        node_a = add_quest_to_campaign(
            campaign=campaign,
            quest_title="A",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )
        node_b = add_quest_to_campaign(campaign=campaign, quest_title="B")

        response = self.client.post(
            reverse("rpg:campaign_dependencies", args=[campaign.id]),
            data=json.dumps(
                {
                    "dependencies": [
                        {
                            "campaign_quest_id": node_b.id,
                            "depends_on_id": node_a.id,
                        },
                        {
                            "campaign_quest_id": node_a.id,
                            "depends_on_id": node_b.id,
                        },
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_campaign_studio_endpoint_returns_canvas_contract(self) -> None:
        campaign = create_campaign(title="Studio contract")
        node = create_campaign_node(
            campaign=campaign,
            title="Start here",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
            reward_skill_id=self.skill.id,
            reward_xp=15,
            map_x=40,
            map_y=80,
        )

        response = self.client.get(reverse("rpg:campaign_studio", args=[campaign.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["campaign"]["id"], campaign.id)
        self.assertEqual(payload["nodes"][0]["id"], node.id)
        self.assertEqual(payload["nodes"][0]["position"], {"x": 40, "y": 80})
        self.assertEqual(payload["nodes"][0]["reward_xp"], 15)
        self.assertEqual(payload["edges"], [])
        self.assertTrue(payload["validation"]["valid"])

    def test_campaign_node_and_edge_endpoints_create_update_and_delete(self) -> None:
        campaign = create_campaign(title="Canvas CRUD")
        first_response = self.client.post(
            reverse("rpg:campaign_nodes", args=[campaign.id]),
            data=json.dumps(
                {
                    "title": "Start",
                    "unlock_mode": "immediate",
                    "position": {"x": 20, "y": 30},
                    "reward_skill_id": self.skill.id,
                    "reward_xp": 10,
                }
            ),
            content_type="application/json",
        )
        second_response = self.client.post(
            reverse("rpg:campaign_nodes", args=[campaign.id]),
            data=json.dumps(
                {
                    "node_kind": "milestone",
                    "title": "Milestone",
                    "position": {"x": 220, "y": 30},
                    "config": {"tone": "reflective"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        first_id = first_response.json()["node"]["id"]
        second_id = second_response.json()["node"]["id"]
        self.assertEqual(second_response.json()["node"]["node_kind"], "milestone")
        self.assertEqual(second_response.json()["node"]["config"]["tone"], "reflective")

        edge_response = self.client.post(
            reverse("rpg:campaign_edges", args=[campaign.id]),
            data=json.dumps(
                {
                    "source_node_id": first_id,
                    "target_node_id": second_id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(edge_response.status_code, 201)
        edge_id = edge_response.json()["edge"]["id"]
        self.assertEqual(edge_response.json()["edge"]["source_node_id"], first_id)
        self.assertEqual(edge_response.json()["edge"]["target_node_id"], second_id)

        update_response = self.client.patch(
            reverse("rpg:campaign_node_detail", args=[campaign.id, second_id]),
            data=json.dumps(
                {
                    "title": "Updated milestone",
                    "position": {"x": 260, "y": 90},
                    "config": {"tone": "direct"},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["node"]["title"], "Updated milestone")
        self.assertEqual(update_response.json()["node"]["position"], {"x": 260, "y": 90})
        self.assertEqual(update_response.json()["node"]["config"]["tone"], "direct")

        delete_edge_response = self.client.delete(
            reverse("rpg:campaign_edge_detail", args=[campaign.id, edge_id]),
        )

        self.assertEqual(delete_edge_response.status_code, 200)
        self.assertFalse(CampaignQuestDependency.objects.filter(pk=edge_id).exists())

        delete_node_response = self.client.delete(
            reverse("rpg:campaign_node_detail", args=[campaign.id, second_id]),
        )

        self.assertEqual(delete_node_response.status_code, 200)
        self.assertFalse(CampaignQuest.objects.filter(pk=second_id).exists())

    def test_campaign_edges_endpoint_rejects_cycle(self) -> None:
        campaign = create_campaign(title="Canvas cycle")
        node_a = create_campaign_node(
            campaign=campaign,
            title="A",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )
        node_b = create_campaign_node(campaign=campaign, title="B")
        create_campaign_edge(
            campaign=campaign,
            source_node_id=node_a.id,
            target_node_id=node_b.id,
        )

        response = self.client.post(
            reverse("rpg:campaign_edges", args=[campaign.id]),
            data=json.dumps(
                {
                    "source_node_id": node_b.id,
                    "target_node_id": node_a.id,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_campaign_positions_endpoint_allows_active_campaign_layout_update(self) -> None:
        campaign = create_campaign(title="Active layout")
        node = create_campaign_node(
            campaign=campaign,
            title="Start",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )
        activate_campaign(campaign=campaign)

        response = self.client.patch(
            reverse("rpg:campaign_node_positions", args=[campaign.id]),
            data=json.dumps(
                {
                    "positions": [
                        {
                            "node_id": node.id,
                            "position": {"x": 500, "y": 140},
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        node.refresh_from_db()
        self.assertEqual(node.map_x, 500)
        self.assertEqual(node.map_y, 140)

    def test_campaign_publish_endpoint_blocks_invalid_campaign(self) -> None:
        campaign = create_campaign(title="No nodes")

        response = self.client.post(
            reverse("rpg:campaign_publish", args=[campaign.id]),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "campaign_not_ready")
        self.assertFalse(response.json()["validation"]["valid"])

    def test_campaign_publish_endpoint_activates_valid_campaign(self) -> None:
        campaign = create_campaign(title="Publish ready")
        create_campaign_node(
            campaign=campaign,
            title="Start",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )

        response = self.client.post(
            reverse("rpg:campaign_publish", args=[campaign.id]),
            data=json.dumps({}),
            content_type="application/json",
        )

        campaign.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["campaign"]["status"], "active")
        self.assertEqual(campaign.status, CampaignStatus.ACTIVE)

    def test_structural_node_edit_is_blocked_after_publish(self) -> None:
        campaign = create_campaign(title="Published")
        node = create_campaign_node(
            campaign=campaign,
            title="Start",
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )
        activate_campaign(campaign=campaign)

        response = self.client.patch(
            reverse("rpg:campaign_node_detail", args=[campaign.id, node.id]),
            data=json.dumps({"title": "Should fail"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_campaign_ai_draft_endpoint_creates_draft(self) -> None:
        response = self.client.post(
            reverse("rpg:campaign_ai_drafts"),
            data=json.dumps(
                {
                    "goal": "Build an AI learning routine",
                    "timeframe_days": 30,
                    "available_minutes_per_day": 60,
                    "skill_ids": [self.skill.id],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["campaign"]
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["created_by"], "ai")
        self.assertEqual(len(payload["map"]["nodes"]), 3)

    def test_quest_completion_endpoint_returns_completed_campaign_results(self) -> None:
        campaign = create_campaign(
            title="API Campaign",
            reward_xp=50,
            reward_skill_id=self.skill.id,
        )
        quest = Quest.objects.create(
            title="Finish API campaign quest",
            quest_type=QuestType.ONE_TIME,
            target_value=1,
            target_unit=TargetUnit.CHECK,
        )
        QuestReward.objects.create(quest=quest, skill=self.skill, xp_amount=10)
        add_quest_to_campaign(
            campaign=campaign,
            quest=quest,
            unlock_mode=CampaignQuestUnlockMode.IMMEDIATE,
        )
        activate_campaign(campaign=campaign)
        Achievement.objects.create(
            code="api-campaign-finished",
            title="API Campaign Finished",
            trigger_type=AchievementTrigger.CAMPAIGN_COMPLETED,
            trigger_config={"campaign_id": campaign.id},
        )

        response = self.client.post(
            reverse("rpg:quest_complete", args=[quest.id]),
            data=json.dumps({"completed_on": "2026-06-10"}),
            content_type="application/json",
        )

        payload = response.json()
        campaign.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["dashboard_refresh_required"])
        self.assertEqual(payload["campaign_results"][0]["campaign"]["id"], campaign.id)
        self.assertTrue(payload["campaign_results"][0]["completed"])
        self.assertEqual(
            payload["campaign_results"][0]["achievement_unlocks"][0]["title"],
            "API Campaign Finished",
        )
        self.assertEqual(campaign.status, CampaignStatus.COMPLETED)


class HabitModelTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Learning")
        self.habit = Habit.objects.create(name="Read", sort_order=10)

    def test_habit_clean_rejects_empty_name(self) -> None:
        habit = Habit(name="  ")

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_habit_clean_rejects_non_positive_target_value(self) -> None:
        habit = Habit(name="Invalid", target_value=0)

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_habit_name_is_unique(self) -> None:
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Habit.objects.create(name="Read")

    def test_check_in_is_unique_per_habit_and_day(self) -> None:
        day = date(2026, 6, 10)
        HabitCheckIn.objects.create(habit=self.habit, checked_on=day)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HabitCheckIn.objects.create(habit=self.habit, checked_on=day)

    def test_milestone_clean_rejects_non_positive_streak_days(self) -> None:
        milestone = HabitMilestone(title="Invalid", streak_days=0)

        with self.assertRaises(ValidationError):
            milestone.full_clean()

    def test_global_milestone_streak_days_are_unique(self) -> None:
        HabitMilestone.objects.create(title="7 Day Momentum", streak_days=7)

        duplicate = HabitMilestone(title="Second 7 Day", streak_days=7)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HabitMilestone.objects.create(title="DB duplicate", streak_days=7)

    def test_habit_specific_milestone_can_share_global_streak_days(self) -> None:
        HabitMilestone.objects.create(title="Global 7", streak_days=7)

        specific = HabitMilestone.objects.create(
            habit=self.habit,
            title="Read 7",
            streak_days=7,
        )

        self.assertEqual(specific.habit, self.habit)

    def test_milestone_reward_requires_positive_xp(self) -> None:
        milestone = HabitMilestone.objects.create(title="7 Day Momentum", streak_days=7)
        reward = HabitMilestoneReward(
            milestone=milestone,
            skill=self.skill,
            xp_amount=0,
        )

        with self.assertRaises(ValidationError):
            reward.full_clean()

    def test_milestone_unlock_requires_matching_specific_habit(self) -> None:
        other_habit = Habit.objects.create(name="Train", sort_order=20)
        milestone = HabitMilestone.objects.create(
            habit=other_habit,
            title="Train 7",
            streak_days=7,
        )
        unlock = HabitMilestoneUnlock(
            milestone=milestone,
            habit=self.habit,
            streak_days=7,
        )

        with self.assertRaises(ValidationError):
            unlock.full_clean()


class HabitServiceTests(TestCase):
    def setUp(self) -> None:
        area = LifeArea.objects.create(name="Habit Area")
        self.learning = Skill.objects.create(name="Learning", life_area=area)
        self.fitness = Skill.objects.create(name="Fitness", life_area=area)
        self.habit = Habit.objects.create(name="Read", sort_order=10)

    def _create_global_milestone_with_rewards(self, streak_days: int = 7) -> HabitMilestone:
        milestone = HabitMilestone.objects.create(
            title=f"{streak_days} Day Momentum",
            streak_days=streak_days,
        )
        HabitMilestoneReward.objects.create(
            milestone=milestone,
            skill=self.learning,
            xp_amount=50,
        )
        HabitMilestoneReward.objects.create(
            milestone=milestone,
            skill=self.fitness,
            xp_amount=25,
        )
        return milestone

    def _create_completed_days(self, end_on: date, days: int) -> None:
        for offset in range(days):
            HabitCheckIn.objects.create(
                habit=self.habit,
                checked_on=end_on - timedelta(days=offset),
                value=1,
            )

    def test_toggle_habit_creates_and_deletes_check_in(self) -> None:
        day = date(2026, 6, 10)

        created = toggle_habit(habit=self.habit, checked_on=day)
        deleted = toggle_habit(habit=self.habit, checked_on=day)

        self.assertTrue(created["checked"])
        self.assertEqual(created["check_in"].checked_on, day)
        self.assertFalse(deleted["checked"])
        self.assertIsNone(deleted["check_in"])
        self.assertEqual(HabitCheckIn.objects.count(), 0)

    def test_check_in_without_due_milestone_does_not_create_xp(self) -> None:
        self._create_global_milestone_with_rewards(streak_days=7)

        toggle_habit(habit=self.habit, checked_on=date(2026, 6, 10))

        self.assertEqual(HabitCheckIn.objects.count(), 1)
        self.assertEqual(HabitMilestoneUnlock.objects.count(), 0)
        self.assertEqual(XpEvent.objects.count(), 0)

    def test_calculate_habit_streak_counts_consecutive_completed_days(self) -> None:
        end_on = date(2026, 6, 10)
        self._create_completed_days(end_on, 3)
        HabitCheckIn.objects.create(
            habit=self.habit,
            checked_on=end_on - timedelta(days=4),
            value=1,
        )

        self.assertEqual(calculate_habit_streak(self.habit, end_on), 3)

    def test_milestone_unlocks_once_and_creates_xp_per_reward(self) -> None:
        milestone = self._create_global_milestone_with_rewards(streak_days=7)
        end_on = date(2026, 6, 10)
        self._create_completed_days(end_on - timedelta(days=1), 6)

        first = toggle_habit(habit=self.habit, checked_on=end_on)
        toggle_habit(habit=self.habit, checked_on=end_on)
        second_create = toggle_habit(habit=self.habit, checked_on=end_on)

        self.assertEqual(first["streak_days"], 7)
        self.assertEqual(len(first["milestone_unlocks"]), 1)
        self.assertEqual(first["milestone_unlocks"][0].milestone, milestone)
        self.assertEqual(len(first["xp_events"]), 2)
        self.assertEqual(HabitMilestoneUnlock.objects.count(), 1)
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(second_create["milestone_unlocks"], [])
        self.assertEqual(second_create["xp_events"], [])
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.get().source_type,
            "habit_milestone_unlock",
        )

    def test_habit_streak_achievement_unlocks_after_check_in_without_milestone(
        self,
    ) -> None:
        today = timezone.localdate()
        self._create_completed_days(today - timedelta(days=1), 2)
        achievement = Achievement.objects.create(
            code="three-day-reader",
            title="Three Day Reader",
            trigger_type=AchievementTrigger.HABIT_STREAK,
            trigger_config={"habit_id": self.habit.id, "streak_days": 3},
        )

        result = toggle_habit(habit=self.habit, checked_on=today)

        unlock = AchievementUnlock.objects.get(achievement=achievement)
        self.assertEqual(result["streak_days"], 3)
        self.assertEqual(result["milestone_unlocks"], [])
        self.assertEqual(unlock.source_type, "habit_streak")
        self.assertEqual(unlock.source_id, self.habit.id)
        self.assertEqual(AchievementUnlock.objects.count(), 1)

    def test_deleting_check_in_does_not_revoke_milestone_or_xp(self) -> None:
        self._create_global_milestone_with_rewards(streak_days=7)
        end_on = date(2026, 6, 10)
        self._create_completed_days(end_on - timedelta(days=1), 6)
        toggle_habit(habit=self.habit, checked_on=end_on)

        toggle_habit(habit=self.habit, checked_on=end_on)

        self.assertFalse(HabitCheckIn.objects.filter(checked_on=end_on).exists())
        self.assertEqual(HabitMilestoneUnlock.objects.count(), 1)
        self.assertEqual(XpEvent.objects.count(), 2)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_inactive_habit_cannot_be_toggled(self) -> None:
        self.habit.is_active = False
        self.habit.save(update_fields=["is_active", "updated_at"])

        with self.assertRaises(HabitNotActiveError):
            toggle_habit(habit=self.habit, checked_on=date(2026, 6, 10))

    def test_build_habit_rows_returns_real_rows_and_legacy_aliases(self) -> None:
        day = date(2026, 6, 10)
        toggle_habit(habit=self.habit, checked_on=day)

        rows, summary = build_habit_rows(day)

        self.assertEqual(rows[0]["id"], self.habit.id)
        self.assertEqual(rows[0]["name"], "Read")
        self.assertEqual(rows[0]["label"], "Read")
        self.assertTrue(rows[0]["completed_today"])
        self.assertTrue(rows[0]["completed"])
        self.assertIsNotNone(rows[0]["check_in_id"])
        self.assertEqual(rows[0]["check_in"]["checked_on"], "2026-06-10")
        self.assertEqual(rows[0]["streak_days"], 1)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["streak_days"], 1)


class HabitApiTests(TestCase):
    def setUp(self) -> None:
        self.habit = Habit.objects.create(name="Hydrate", sort_order=10)

    def test_toggle_endpoint_returns_snake_case_json(self) -> None:
        response = self.client.post(
            reverse("rpg:habit_toggle", args=[self.habit.id]),
            data=json.dumps({"checked_on": "2026-06-10", "note": "done"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["habit"]["id"], self.habit.id)
        self.assertEqual(payload["habit"]["completed_today"], True)
        self.assertIsNotNone(payload["habit"]["check_in_id"])
        self.assertEqual(payload["habit"]["check_in"]["checked_on"], "2026-06-10")
        self.assertIn("next_milestone", payload["habit"])
        self.assertEqual(payload["milestone_unlocks"], [])
        self.assertEqual(payload["xp_events"], [])
        self.assertTrue(payload["dashboard_refresh_required"])
        self.assertNotIn("completedToday", payload["habit"])

    def test_toggle_endpoint_second_click_deletes_check_in(self) -> None:
        url = reverse("rpg:habit_toggle", args=[self.habit.id])
        body = json.dumps({"checked_on": "2026-06-10"})
        self.client.post(url, data=body, content_type="application/json")

        response = self.client.post(url, data=body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["habit"]["completed_today"])
        self.assertIsNone(payload["habit"]["check_in_id"])
        self.assertIsNone(payload["habit"]["check_in"])
        self.assertEqual(HabitCheckIn.objects.count(), 0)

    def test_toggle_endpoint_returns_conflict_for_inactive_habit(self) -> None:
        self.habit.is_active = False
        self.habit.save(update_fields=["is_active", "updated_at"])

        response = self.client.post(
            reverse("rpg:habit_toggle", args=[self.habit.id]),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "habit_not_active")


class ProgressionModelTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Discipline")
        self.goal = Goal.objects.create(
            title="Build discipline",
            status=GoalStatus.ACTIVE,
            target_value=10,
        )
        self.challenge = Challenge.objects.create(
            title="10 Day Focus",
            status=ChallengeStatus.ACTIVE,
            target_value=10,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 10),
        )

    def test_goal_rejects_empty_title_and_progress_above_target(self) -> None:
        empty_goal = Goal(title="  ", target_value=1)
        invalid_progress = Goal(title="Invalid", target_value=5, progress_value=6)

        with self.assertRaises(ValidationError):
            empty_goal.full_clean()
        with self.assertRaises(ValidationError):
            invalid_progress.full_clean()

    def test_goal_skill_is_unique_per_goal_skill(self) -> None:
        GoalSkill.objects.create(goal=self.goal, skill=self.skill)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GoalSkill.objects.create(goal=self.goal, skill=self.skill)

    def test_challenge_check_in_validates_date_range_and_uniqueness(self) -> None:
        invalid = ChallengeCheckIn(
            challenge=self.challenge,
            checked_on=date(2026, 6, 11),
        )

        with self.assertRaises(ValidationError):
            invalid.full_clean()

        ChallengeCheckIn.objects.create(
            challenge=self.challenge,
            checked_on=date(2026, 6, 5),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChallengeCheckIn.objects.create(
                    challenge=self.challenge,
                    checked_on=date(2026, 6, 5),
                )

    def test_challenge_reward_requires_positive_xp(self) -> None:
        reward = ChallengeReward(
            challenge=self.challenge,
            skill=self.skill,
            xp_amount=0,
        )

        with self.assertRaises(ValidationError):
            reward.full_clean()

    def test_achievement_requires_dict_trigger_config(self) -> None:
        achievement = Achievement(
            code="bad",
            title="Bad achievement",
            trigger_type=AchievementTrigger.QUEST_COUNT,
            trigger_config=[],
        )

        with self.assertRaises(ValidationError):
            achievement.full_clean()


class ProgressionServiceTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Willpower")
        self.goal = Goal.objects.create(
            title="Build the Life RPG foundation",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.LEGENDARY,
            target_value=3,
        )
        self.challenge = Challenge.objects.create(
            title="3 Days No Sugar",
            status=ChallengeStatus.ACTIVE,
            goal=self.goal,
            target_value=3,
            start_date=date(2026, 6, 8),
            end_date=date(2026, 6, 10),
            reward_title="Willpower Badge",
        )
        ChallengeReward.objects.create(
            challenge=self.challenge,
            skill=self.skill,
            xp_amount=120,
        )

    def test_goal_progress_completion_creates_journal_without_xp(self) -> None:
        achievement = Achievement.objects.create(
            code="goal-finished",
            title="Goal Finished",
            rarity=AchievementRarity.RARE,
            trigger_type=AchievementTrigger.GOAL_COMPLETED,
            trigger_config={"goal_id": self.goal.id},
        )

        entry = update_goal_progress(
            goal=self.goal,
            progress_value=3,
            note="done",
        )
        self.goal.refresh_from_db()

        self.assertEqual(entry.new_value, 3)
        self.assertEqual(self.goal.status, GoalStatus.COMPLETED)
        self.assertEqual(XpEvent.objects.count(), 0)
        self.assertTrue(
            JournalEntry.objects.filter(
                source_type="goal_completion",
                source_id=self.goal.id,
            ).exists()
        )
        self.assertTrue(AchievementUnlock.objects.filter(achievement=achievement).exists())

    def test_complete_goal_is_idempotent(self) -> None:
        first = complete_goal(goal=self.goal)
        second = complete_goal(goal=self.goal)

        self.assertEqual(first["goal"].id, second["goal"].id)
        self.assertEqual(XpEvent.objects.count(), 0)
        self.assertEqual(
            JournalEntry.objects.filter(source_type="goal_completion").count(),
            1,
        )

    def test_challenge_toggle_creates_and_deletes_check_in_without_xp(self) -> None:
        created = toggle_challenge_check_in(
            challenge=self.challenge,
            checked_on=date(2026, 6, 8),
        )
        deleted = toggle_challenge_check_in(
            challenge=self.challenge,
            checked_on=date(2026, 6, 8),
        )

        self.assertTrue(created["checked"])
        self.assertEqual(created["challenge"].current_value, 1)
        self.assertFalse(deleted["checked"])
        self.assertEqual(ChallengeCheckIn.objects.count(), 0)
        self.assertEqual(XpEvent.objects.count(), 0)

    def test_completed_challenge_cannot_be_toggled(self) -> None:
        complete_challenge(challenge=self.challenge)

        with self.assertRaises(ChallengeNotActiveError):
            toggle_challenge_check_in(
                challenge=self.challenge,
                checked_on=date(2026, 6, 9),
            )

    def test_complete_challenge_awards_xp_once_and_unlocks_achievement(self) -> None:
        achievement = Achievement.objects.create(
            code="challenge-finished",
            title="Challenge Finished",
            rarity=AchievementRarity.EPIC,
            trigger_type=AchievementTrigger.CHALLENGE_COMPLETED,
            trigger_config={"challenge_id": self.challenge.id},
        )

        first = complete_challenge(challenge=self.challenge)
        second = complete_challenge(challenge=self.challenge)

        self.assertEqual(len(first["xp_events"]), 1)
        self.assertEqual(len(second["xp_events"]), 1)
        self.assertEqual(XpEvent.objects.count(), 1)
        self.assertEqual(XpEvent.objects.get().source_type, "challenge")
        self.assertTrue(
            JournalEntry.objects.filter(
                source_type="challenge_completion",
                source_id=self.challenge.id,
            ).exists()
        )
        self.assertTrue(AchievementUnlock.objects.filter(achievement=achievement).exists())

    def test_fail_challenge_closes_without_xp_and_creates_journal_once(self) -> None:
        ChallengeCheckIn.objects.create(
            challenge=self.challenge,
            checked_on=date(2026, 6, 8),
            value=1,
        )

        first = fail_challenge(challenge=self.challenge, note="Broke the streak.")
        second = fail_challenge(challenge=self.challenge)
        self.challenge.refresh_from_db()

        self.assertEqual(self.challenge.status, ChallengeStatus.FAILED)
        self.assertIsNotNone(self.challenge.failed_at)
        self.assertEqual(first["challenge"].id, second["challenge"].id)
        self.assertEqual(first["xp_events"], [])
        self.assertEqual(second["xp_events"], [])
        self.assertEqual(XpEvent.objects.count(), 0)
        self.assertEqual(ChallengeCheckIn.objects.count(), 1)
        self.assertEqual(
            JournalEntry.objects.filter(
                source_type="challenge_failure",
                source_id=self.challenge.id,
            ).count(),
            1,
        )

    def test_completed_challenge_cannot_be_failed(self) -> None:
        complete_challenge(challenge=self.challenge)

        with self.assertRaises(ChallengeNotCompletableError):
            fail_challenge(challenge=self.challenge)

    def test_progression_selectors_return_real_rows(self) -> None:
        self.assertEqual(get_active_challenge(), self.challenge)
        self.assertEqual(build_goal_rows(status="all")[0]["id"], self.goal.id)
        self.assertEqual(build_challenge_rows(status="all")[0]["id"], self.challenge.id)


class ActivityAchievementAutomationTests(TestCase):
    def setUp(self) -> None:
        area = LifeArea.objects.create(name="Activity Area")
        self.skill = Skill.objects.create(name="Programming", life_area=area)
        self.definition = ActivityDefinition.objects.create(
            name="Coding",
            life_area=area,
        )
        ActivityReward.objects.create(
            activity_definition=self.definition,
            skill=self.skill,
            xp_per_minute=100,
        )

    def test_activity_xp_unlocks_total_xp_and_skill_level_achievements(self) -> None:
        total_xp = Achievement.objects.create(
            code="hundred-xp",
            title="Hundred XP",
            trigger_type=AchievementTrigger.TOTAL_XP,
            trigger_config={"xp": 100},
            sort_order=10,
        )
        skill_level = Achievement.objects.create(
            code="programming-level-2",
            title="Programming Level 2",
            trigger_type=AchievementTrigger.SKILL_LEVEL,
            trigger_config={"skill_id": self.skill.id, "level": 2},
            sort_order=20,
        )

        entry = create_activity_entry(
            activity_definition=self.definition,
            minutes=1,
            started_at=timezone.now(),
        )

        self.assertEqual(XpEvent.objects.count(), 1)
        self.assertEqual(self.skill.get_level(), 2)
        unlocks = {
            unlock.achievement_id: unlock
            for unlock in AchievementUnlock.objects.order_by("achievement_id")
        }
        self.assertEqual(set(unlocks), {total_xp.id, skill_level.id})
        self.assertEqual(unlocks[total_xp.id].source_type, "activity")
        self.assertEqual(unlocks[total_xp.id].source_id, entry.id)
        self.assertEqual(unlocks[skill_level.id].source_type, "activity")
        self.assertEqual(unlocks[skill_level.id].source_id, entry.id)


class ProgressionApiTests(TestCase):
    def setUp(self) -> None:
        self.skill = Skill.objects.create(name="Fitness")
        self.goal = Goal.objects.create(
            title="Read 12 books",
            status=GoalStatus.ACTIVE,
            target_value=12,
        )
        self.challenge = Challenge.objects.create(
            title="30 Days No Sugar",
            status=ChallengeStatus.ACTIVE,
            target_value=30,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )
        ChallengeReward.objects.create(
            challenge=self.challenge,
            skill=self.skill,
            xp_amount=250,
        )
        self.achievement = Achievement.objects.create(
            code="first-goal",
            title="First Goal",
            trigger_type=AchievementTrigger.GOAL_COMPLETED,
            trigger_config={"goal_id": self.goal.id},
        )

    def test_goals_endpoint_lists_and_creates_goals(self) -> None:
        list_response = self.client.get(reverse("rpg:goals") + "?status=all")
        create_response = self.client.post(
            reverse("rpg:goals"),
            data=json.dumps({"title": "Save emergency fund", "status": "active"}),
            content_type="application/json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["goals"][0]["title"], "Read 12 books")
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["goal"]["status"], "active")

    def test_goal_progress_endpoint_uses_snake_case(self) -> None:
        response = self.client.post(
            reverse("rpg:goal_progress", args=[self.goal.id]),
            data=json.dumps({"progress_value": 5}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["goal"]["progress_value"], 5)
        self.assertEqual(payload["progress_entry"]["new_value"], 5)

    def test_challenge_toggle_and_complete_endpoints(self) -> None:
        toggle_response = self.client.post(
            reverse("rpg:challenge_toggle", args=[self.challenge.id]),
            data=json.dumps({"checked_on": "2026-06-10"}),
            content_type="application/json",
        )
        complete_response = self.client.post(
            reverse("rpg:challenge_complete", args=[self.challenge.id]),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(toggle_response.status_code, 200)
        self.assertTrue(toggle_response.json()["checked"])
        self.assertEqual(toggle_response.json()["xp_events"], [])
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.json()["xp_events"][0]["source_type"], "challenge")

    def test_challenge_fail_endpoint_closes_without_xp(self) -> None:
        response = self.client.post(
            reverse("rpg:challenge_fail", args=[self.challenge.id]),
            data=json.dumps({"note": "Missed a required day."}),
            content_type="application/json",
        )
        self.challenge.refresh_from_db()

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["challenge"]["status"], "failed")
        self.assertEqual(payload["xp_events"], [])
        self.assertEqual(payload["achievement_unlocks"], [])
        self.assertEqual(payload["journal_entry"]["source_type"], "challenge_failure")
        self.assertTrue(payload["dashboard_refresh_required"])
        self.assertEqual(self.challenge.status, ChallengeStatus.FAILED)
        self.assertEqual(XpEvent.objects.count(), 0)

    def test_achievements_endpoint_lists_and_evaluates(self) -> None:
        complete_goal(goal=self.goal)

        list_response = self.client.get(reverse("rpg:achievements"))
        evaluate_response = self.client.post(
            reverse("rpg:achievement_evaluate"),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["achievements"][0]["title"], "First Goal")
        self.assertEqual(evaluate_response.status_code, 200)
        self.assertEqual(AchievementUnlock.objects.count(), 1)


class JournalEntryModelTests(TestCase):
    def test_journal_entry_clean_rejects_empty_title(self) -> None:
        entry = JournalEntry(title="  ")

        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_system_journal_source_is_unique_when_source_id_is_set(self) -> None:
        JournalEntry.objects.create(
            title="Quest completed",
            entry_type=JournalEntryType.QUEST,
            source_type="quest_completion",
            source_id=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalEntry.objects.create(
                    title="Duplicate",
                    entry_type=JournalEntryType.QUEST,
                    source_type="quest_completion",
                    source_id=1,
                )

    def test_manual_entries_can_share_empty_source(self) -> None:
        JournalEntry.objects.create(title="First manual")
        JournalEntry.objects.create(title="Second manual")

        self.assertEqual(JournalEntry.objects.count(), 2)

    def test_journal_entry_normalizes_tags(self) -> None:
        entry = JournalEntry(title="Tagged", tags=["#Learning", "Deep Work", "learning"])
        entry.full_clean()

        self.assertEqual(entry.tags, ["learning", "deep-work"])

    def test_create_journal_entry_unlocks_journal_streak_achievement(self) -> None:
        today = timezone.localdate()
        achievement = Achievement.objects.create(
            code="two-day-journal",
            title="Two Day Journal",
            trigger_type=AchievementTrigger.JOURNAL_STREAK,
            trigger_config={"streak_days": 2},
        )

        create_journal_entry(
            title="Yesterday",
            entry_date=today - timedelta(days=1),
        )
        self.assertFalse(
            AchievementUnlock.objects.filter(achievement=achievement).exists()
        )

        entry = create_journal_entry(title="Today", entry_date=today)

        unlock = AchievementUnlock.objects.get(achievement=achievement)
        self.assertEqual(unlock.source_type, "journal_entry")
        self.assertEqual(unlock.source_id, entry.id)
        self.assertEqual(AchievementUnlock.objects.count(), 1)


class CharacterIdentityModelTests(TestCase):
    def test_character_identity_rejects_empty_title(self) -> None:
        identity = CharacterIdentity(title="  ")

        with self.assertRaises(ValidationError):
            identity.full_clean()

    def test_character_identity_end_date_cannot_be_before_start(self) -> None:
        identity = CharacterIdentity(
            title="Builder",
            started_on=date(2026, 6, 10),
            ended_on=date(2026, 6, 9),
        )

        with self.assertRaises(ValidationError):
            identity.full_clean()


class JournalEntryServiceTests(TestCase):
    def test_create_manual_journal_entry_uses_local_date_by_default(self) -> None:
        entry = create_journal_entry(
            title="Daily reflection",
            content="Today I completed every quest.",
            mood="focused",
            reflection_proud="I shipped the feature.",
            reflection_challenge="Keeping scope clear.",
            reflection_learned="Small journal entries matter.",
            reflection_improve="Plan earlier.",
            reflection_goal_action="I completed the important task.",
            tags=["#Learning", "discipline"],
        )

        self.assertEqual(entry.entry_type, JournalEntryType.MANUAL)
        self.assertEqual(entry.entry_date, timezone.localdate())
        self.assertEqual(entry.mood, "focused")
        self.assertEqual(entry.reflection_proud, "I shipped the feature.")
        self.assertEqual(entry.tags, ["learning", "discipline"])

    def test_create_system_journal_entry_is_idempotent(self) -> None:
        first = create_system_journal_entry(
            title="Quest completed",
            content="Read 20 minutes",
            entry_type=JournalEntryType.QUEST,
            source_type="quest_completion",
            source_id=42,
        )
        second = create_system_journal_entry(
            title="Quest completed again",
            content="Should reuse existing entry",
            entry_type=JournalEntryType.QUEST,
            source_type="quest_completion",
            source_id=42,
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_build_journal_entry_rows_filters_by_entry_date(self) -> None:
        JournalEntry.objects.create(
            title="Old",
            entry_date=date(2026, 6, 9),
        )
        today_entry = JournalEntry.objects.create(
            title="Today",
            content="Visible",
            entry_date=date(2026, 6, 10),
        )

        rows = build_journal_entry_rows(
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 10),
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], today_entry.id)
        self.assertEqual(rows[0]["content"], "Visible")
        self.assertEqual(rows[0]["body"], "Visible")

    def test_update_journal_entry_updates_reflection_and_tags(self) -> None:
        entry = create_journal_entry(title="Draft")

        updated = update_journal_entry(
            entry=entry,
            title="Daily Chronicle",
            reflection_learned="Consistency compounds.",
            tags=["#discipline"],
        )

        self.assertEqual(updated.title, "Daily Chronicle")
        self.assertEqual(updated.reflection_learned, "Consistency compounds.")
        self.assertEqual(updated.tags, ["discipline"])

    def test_build_journal_overview_contains_stats_and_timeline(self) -> None:
        area = LifeArea.objects.create(name="Mind")
        skill = Skill.objects.create(name="Learning", life_area=area)
        skill.add_xp(amount=25, source_type="manual", note="journal test")
        create_journal_entry(
            title="Daily Chronicle",
            content="I learned today.",
            entry_date=timezone.localdate(),
            tags=["learning"],
        )
        CharacterIdentity.objects.create(title="Builder")

        overview = build_journal_overview(selected_date=timezone.localdate())

        self.assertEqual(overview["stats"]["total_entries"], 1)
        self.assertEqual(overview["stats"]["xp_logged"], 25)
        self.assertEqual(overview["current_entry"]["title"], "Daily Chronicle")
        self.assertEqual(overview["identity"]["current"]["title"], "Builder")
        self.assertTrue(overview["chapters"])
        self.assertTrue(overview["insights"])


class JournalEntryApiTests(TestCase):
    def test_journal_endpoint_creates_manual_entry(self) -> None:
        response = self.client.post(
            reverse("rpg:journal_create"),
            data=json.dumps(
                {
                    "title": "Daily reflection",
                    "content": "Today I completed every quest.",
                    "mood": "focused",
                    "reflection_proud": "I completed the important task.",
                    "reflection_goal_action": "I moved closer to my goals.",
                    "tags": ["#learning", "discipline"],
                    "entry_date": "2026-06-10",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()["entry"]
        self.assertEqual(payload["title"], "Daily reflection")
        self.assertEqual(payload["content"], "Today I completed every quest.")
        self.assertEqual(payload["entry_type"], JournalEntryType.MANUAL)
        self.assertEqual(payload["mood"], "focused")
        self.assertEqual(
            payload["reflection"]["proud"],
            "I completed the important task.",
        )
        self.assertEqual(payload["tags"], ["learning", "discipline"])
        self.assertEqual(payload["entry_date"], "2026-06-10")
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_journal_endpoint_rejects_empty_title(self) -> None:
        response = self.client.post(
            reverse("rpg:journal_create"),
            data=json.dumps({"title": "  "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")

    def test_journal_endpoint_lists_overview(self) -> None:
        JournalEntry.objects.create(
            title="Today",
            content="Visible",
            mood=JournalMood.BALANCED,
            tags=["learning"],
            entry_date=timezone.localdate(),
        )

        response = self.client.get(reverse("rpg:journal_create"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["entries"][0]["title"], "Today")
        self.assertEqual(payload["current_entry"]["title"], "Today")
        self.assertEqual(payload["stats"]["total_entries"], 1)
        self.assertIn("mood_options", payload)

    def test_journal_detail_endpoint_updates_entry(self) -> None:
        entry = JournalEntry.objects.create(title="Draft")

        response = self.client.patch(
            reverse("rpg:journal_entry_detail", args=[entry.id]),
            data=json.dumps(
                {
                    "title": "Updated",
                    "reflection_learned": "Keep the journal specific.",
                    "tags": "learning, discipline",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["entry"]
        self.assertEqual(payload["title"], "Updated")
        self.assertEqual(payload["reflection"]["learned"], "Keep the journal specific.")
        self.assertEqual(payload["tags"], ["learning", "discipline"])

    def test_journal_endpoint_rejects_invalid_date(self) -> None:
        response = self.client.post(
            reverse("rpg:journal_create"),
            data=json.dumps({"title": "Daily reflection", "entry_date": "wrong"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "validation_error")


class QuestSeedTests(TestCase):
    def test_seed_creates_daily_quests_and_rewards_idempotently(self) -> None:
        call_command("seed_life_rpg")
        counts_after_first_run = {
            "quests": Quest.objects.count(),
            "rewards": QuestReward.objects.count(),
            "completions": QuestCompletion.objects.count(),
            "events": XpEvent.objects.count(),
            "journal_entries": JournalEntry.objects.count(),
        }

        call_command("seed_life_rpg")

        self.assertEqual(Quest.objects.count(), counts_after_first_run["quests"])
        self.assertEqual(
            QuestReward.objects.count(),
            counts_after_first_run["rewards"],
        )
        self.assertEqual(QuestCompletion.objects.count(), 0)
        self.assertEqual(
            QuestCompletion.objects.count(),
            counts_after_first_run["completions"],
        )
        self.assertEqual(XpEvent.objects.count(), counts_after_first_run["events"])
        self.assertEqual(
            JournalEntry.objects.count(),
            counts_after_first_run["journal_entries"],
        )

        read_quest = Quest.objects.get(title="Read 20 minutes")
        self.assertEqual(read_quest.target_unit, TargetUnit.MINUTES)
        self.assertEqual(read_quest.reward_xp_total(), 25)
        self.assertTrue(Quest.objects.filter(title="Plan tomorrow").exists())

    def test_existing_dashboard_api_still_works_after_seed(self) -> None:
        call_command("seed_life_rpg")

        response = self.client.get(reverse("dashboard:dashboard_api"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("daily_quests", response.json())
        self.assertIsNotNone(response.json()["active_challenge"])


class HabitSeedTests(TestCase):
    def test_seed_creates_habits_and_milestones_idempotently_without_checkins(self) -> None:
        call_command("seed_life_rpg")
        counts_after_first_run = {
            "habits": Habit.objects.count(),
            "milestones": HabitMilestone.objects.count(),
            "milestone_rewards": HabitMilestoneReward.objects.count(),
            "checkins": HabitCheckIn.objects.count(),
            "unlocks": HabitMilestoneUnlock.objects.count(),
        }

        call_command("seed_life_rpg")

        self.assertEqual(Habit.objects.count(), counts_after_first_run["habits"])
        self.assertEqual(
            HabitMilestone.objects.count(),
            counts_after_first_run["milestones"],
        )
        self.assertEqual(
            HabitMilestoneReward.objects.count(),
            counts_after_first_run["milestone_rewards"],
        )
        self.assertEqual(HabitCheckIn.objects.count(), 0)
        self.assertEqual(
            HabitCheckIn.objects.count(),
            counts_after_first_run["checkins"],
        )
        self.assertEqual(HabitMilestoneUnlock.objects.count(), 0)
        self.assertEqual(
            HabitMilestoneUnlock.objects.count(),
            counts_after_first_run["unlocks"],
        )
        self.assertEqual(
            set(Habit.objects.values_list("name", flat=True)),
            {
                "Train",
                "Read",
                "Learn",
                "Hydrate",
                "Sleep",
                "Journal",
                "Review finances",
            },
        )
        self.assertEqual(
            set(HabitMilestone.objects.values_list("streak_days", flat=True)),
            {7, 14, 30},
        )
        self.assertTrue(
            HabitMilestoneReward.objects.filter(
                milestone__title="7 Day Momentum",
                skill__name="Learning",
                xp_amount=50,
            ).exists()
        )


class ProgressionSeedTests(TestCase):
    def test_seed_creates_progression_definitions_without_history(self) -> None:
        call_command("seed_life_rpg")
        counts_after_first_run = {
            "goals": Goal.objects.count(),
            "challenges": Challenge.objects.count(),
            "challenge_rewards": ChallengeReward.objects.count(),
            "achievements": Achievement.objects.count(),
            "checkins": ChallengeCheckIn.objects.count(),
            "unlocks": AchievementUnlock.objects.count(),
        }

        call_command("seed_life_rpg")

        self.assertEqual(Goal.objects.count(), counts_after_first_run["goals"])
        self.assertEqual(Challenge.objects.count(), counts_after_first_run["challenges"])
        self.assertEqual(
            ChallengeReward.objects.count(),
            counts_after_first_run["challenge_rewards"],
        )
        self.assertEqual(
            Achievement.objects.count(),
            counts_after_first_run["achievements"],
        )
        self.assertEqual(ChallengeCheckIn.objects.count(), 0)
        self.assertEqual(ChallengeCheckIn.objects.count(), counts_after_first_run["checkins"])
        self.assertEqual(AchievementUnlock.objects.count(), 0)
        self.assertEqual(AchievementUnlock.objects.count(), counts_after_first_run["unlocks"])
        self.assertTrue(Goal.objects.filter(title="Build the Life RPG foundation").exists())
        self.assertTrue(Challenge.objects.filter(title="30 Days No Sugar").exists())
        self.assertTrue(Achievement.objects.filter(code="iron-discipline").exists())


class JournalSeedTests(TestCase):
    def test_seed_creates_journal_entries_idempotently(self) -> None:
        call_command("seed_life_rpg")
        first_count = JournalEntry.objects.count()
        first_identity_count = CharacterIdentity.objects.count()

        call_command("seed_life_rpg")

        self.assertEqual(JournalEntry.objects.count(), first_count)
        self.assertEqual(CharacterIdentity.objects.count(), first_identity_count)
        self.assertEqual(first_count, 2)
        self.assertEqual(first_identity_count, 1)
        self.assertTrue(JournalEntry.objects.filter(title="First Entry").exists())
        self.assertTrue(
            JournalEntry.objects.filter(title="Weekly Reflection").exists()
        )
        self.assertTrue(CharacterIdentity.objects.filter(title="Builder").exists())
