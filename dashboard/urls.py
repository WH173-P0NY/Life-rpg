from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.react_shell, name="react_shell"),
    path("legacy-dashboard/", views.index, name="index"),
    path("api/csrf/", views.csrf_api, name="csrf_api"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/app-settings/", views.app_settings_api, name="app_settings_api"),
    path(
        "api/app-settings/account/",
        views.account_settings_api,
        name="account_settings_api",
    ),
    path(
        "api/app-settings/llm/",
        views.llm_settings_api,
        name="llm_settings_api",
    ),
    path("api/skills/", views.skills_api, name="skills_api"),
    path(
        "api/activity-definitions/",
        views.activity_definitions_api,
        name="activity_definitions_api",
    ),
    path(
        "api/activities/manual/",
        views.manual_activity_api,
        name="manual_activity_api",
    ),
]
