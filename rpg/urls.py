from __future__ import annotations

from django.urls import URLPattern, path

from . import views

app_name = "rpg"
urlpatterns: list[URLPattern] = [
    path(
        "quests/<int:quest_id>/complete/",
        views.complete_quest_api,
        name="quest_complete",
    ),
    path(
        "quests/<int:quest_id>/progress/",
        views.update_quest_progress_api,
        name="quest_progress",
    ),
    path(
        "habits/<int:habit_id>/toggle/",
        views.toggle_habit_api,
        name="habit_toggle",
    ),
    path("goals/", views.goals_api, name="goals"),
    path("goals/<int:goal_id>/", views.goal_detail_api, name="goal_detail"),
    path(
        "goals/<int:goal_id>/progress/",
        views.goal_progress_api,
        name="goal_progress",
    ),
    path(
        "goals/<int:goal_id>/complete/",
        views.goal_complete_api,
        name="goal_complete",
    ),
    path(
        "goals/<int:goal_id>/archive/",
        views.goal_archive_api,
        name="goal_archive",
    ),
    path("challenges/", views.challenges_api, name="challenges"),
    path(
        "challenges/<int:challenge_id>/",
        views.challenge_detail_api,
        name="challenge_detail",
    ),
    path(
        "challenges/<int:challenge_id>/toggle/",
        views.challenge_toggle_api,
        name="challenge_toggle",
    ),
    path(
        "challenges/<int:challenge_id>/complete/",
        views.challenge_complete_api,
        name="challenge_complete",
    ),
    path(
        "challenges/<int:challenge_id>/fail/",
        views.challenge_fail_api,
        name="challenge_fail",
    ),
    path("achievements/", views.achievements_api, name="achievements"),
    path(
        "achievements/<int:achievement_id>/unlock/",
        views.achievement_unlock_api,
        name="achievement_unlock",
    ),
    path(
        "achievements/evaluate/",
        views.achievement_evaluate_api,
        name="achievement_evaluate",
    ),
    path(
        "journal/",
        views.journal_entries_api,
        name="journal_create",
    ),
    path(
        "journal/<int:entry_id>/",
        views.journal_entry_detail_api,
        name="journal_entry_detail",
    ),
]
