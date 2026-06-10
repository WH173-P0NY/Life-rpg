from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from activities.models import ActivityDefinition, ActivityEntry, ActivityReward
from activities.services import create_activity_entry
from skills.models import LifeArea, Skill

from .forms import ManualActivityForm
from .models import LlmProvider, LlmProviderConfig
from .services import DEFAULT_HERO_NAME, build_dashboard_context


def react_shell(request: HttpRequest) -> HttpResponse:
    index_path = Path(settings.REACT_BUILD_DIR) / "index.html"
    if not index_path.exists():
        return HttpResponse(
            "React build not found. Run `cd frontend && npm run build` "
            "or use the Vite dev server at http://127.0.0.1:5173/.",
            status=503,
            content_type="text/plain",
        )

    html = index_path.read_text(encoding="utf-8")
    html = _rewrite_vite_asset_paths(html)
    return HttpResponse(html, content_type="text/html")


def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ManualActivityForm(request.POST)
        if form.is_valid():
            create_activity_entry(
                activity_definition=form.cleaned_data["activity_definition"],
                minutes=form.cleaned_data["minutes"],
                started_at=form.cleaned_data["started_at"],
                source=form.cleaned_data["source"],
            )
            messages.success(request, "Activity added and XP awarded.")
            return redirect("dashboard:index")
    else:
        form = ManualActivityForm()

    context = build_dashboard_context(request.GET, hero_name=_dashboard_username(request))
    context["activity_form"] = form
    return render(request, "dashboard/index.html", context)


def _rewrite_vite_asset_paths(html: str) -> str:
    asset_prefix = static("frontend/assets/")
    return html.replace('"/assets/', f'"{asset_prefix}').replace(
        "'/assets/",
        f"'{asset_prefix}",
    )


@require_GET
@ensure_csrf_cookie
def dashboard_api(request: HttpRequest) -> JsonResponse:
    context = build_dashboard_context(request.GET, hero_name=_dashboard_username(request))
    return JsonResponse(_serialize_dashboard_context(context))


@require_GET
@ensure_csrf_cookie
def csrf_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


@require_POST
def manual_activity_api(request: HttpRequest) -> JsonResponse:
    form = ManualActivityForm(_manual_activity_payload(request))
    if not form.is_valid():
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    entry = create_activity_entry(
        activity_definition=form.cleaned_data["activity_definition"],
        minutes=form.cleaned_data["minutes"],
        started_at=form.cleaned_data["started_at"],
        source=form.cleaned_data["source"],
    )
    entry = (
        ActivityEntry.objects.select_related("activity_definition")
        .prefetch_related("xp_events__skill")
        .get(pk=entry.pk)
    )

    return JsonResponse({"entry": _serialize_activity_entry(entry)}, status=201)


@require_GET
@ensure_csrf_cookie
def app_settings_api(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "account": _serialize_account(_settings_user(request)),
            "llm_providers": _serialize_llm_provider_configs(),
            "skills": _serialize_skill_options(),
            "life_areas": _serialize_life_area_options(),
            "activity_definitions": _serialize_activity_definitions(),
        }
    )


@require_POST
def account_settings_api(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_payload(request)
        user = _settings_user(request)
        username = _optional_string(payload.get("username")).strip()
        password = _optional_string(payload.get("password"))

        if username:
            user.username = username
        if password:
            if len(password) < 8:
                raise ValueError("Password must contain at least 8 characters.")
            user.set_password(password)
        user.full_clean()
        user.save()
        if password and getattr(request, "user", None) == user:
            update_session_auth_hash(request, user)
    except (IntegrityError, ValidationError, ValueError) as exc:
        return _validation_error_response(str(exc))

    return JsonResponse({"account": _serialize_account(user)})


@require_POST
def llm_settings_api(request: HttpRequest) -> JsonResponse:
    try:
        payload = _json_payload(request)
        providers = payload.get("providers", [])
        if not isinstance(providers, list):
            raise ValueError("providers must be a list.")

        with transaction.atomic():
            for item in providers:
                if not isinstance(item, dict):
                    raise ValueError("providers must contain objects.")
                provider = _required_string(item.get("provider"), field_name="provider")
                if provider not in LlmProvider.values:
                    raise ValueError("provider must be chatgpt, claude or gemini.")
                config, _ = LlmProviderConfig.objects.get_or_create(provider=provider)
                if "model_name" in item:
                    config.model_name = _optional_string(item.get("model_name"))
                if "api_key" in item:
                    config.api_key = _optional_string(item.get("api_key"))
                if "is_enabled" in item:
                    config.is_enabled = _optional_bool(item.get("is_enabled"))
                config.full_clean()
                config.save()
    except (ValidationError, ValueError) as exc:
        return _validation_error_response(str(exc))

    return JsonResponse({"llm_providers": _serialize_llm_provider_configs()})


@require_http_methods(["GET", "POST"])
def skills_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(
            {
                "skills": _serialize_skill_options(),
                "life_areas": _serialize_life_area_options(),
            }
        )

    try:
        payload = _json_payload(request)
        skill = Skill(
            name=_required_string(payload.get("name"), field_name="name"),
            life_area_id=_optional_int(payload.get("life_area_id"), field_name="life_area_id"),
        )
        skill.full_clean()
        skill.save()
    except (IntegrityError, ValidationError, ValueError) as exc:
        return _validation_error_response(str(exc))

    return JsonResponse({"skill": _serialize_skill_option(skill)}, status=201)


@require_http_methods(["GET", "POST"])
def activity_definitions_api(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return JsonResponse(
            {
                "activity_definitions": _serialize_activity_definitions(),
                "skills": _serialize_skill_options(),
                "life_areas": _serialize_life_area_options(),
            }
        )

    try:
        payload = _json_payload(request)
        rewards_payload = payload.get("rewards", [])
        if not isinstance(rewards_payload, list):
            raise ValueError("rewards must be a list.")

        with transaction.atomic():
            definition = ActivityDefinition(
                name=_required_string(payload.get("name"), field_name="name"),
                description=_optional_string(payload.get("description")),
                life_area_id=_optional_int(
                    payload.get("life_area_id"),
                    field_name="life_area_id",
                ),
            )
            definition.full_clean()
            definition.save()

            for reward_payload in rewards_payload:
                if not isinstance(reward_payload, dict):
                    raise ValueError("rewards must contain objects.")
                reward = ActivityReward(
                    activity_definition=definition,
                    skill_id=_required_int(
                        reward_payload.get("skill_id"),
                        field_name="skill_id",
                    ),
                    xp_per_minute=_required_int(
                        reward_payload.get("xp_per_minute"),
                        field_name="xp_per_minute",
                    ),
                )
                reward.full_clean()
                reward.save()
    except (IntegrityError, ValidationError, ValueError) as exc:
        return _validation_error_response(str(exc))

    return JsonResponse(
        {
            "activity_definition": _serialize_activity_definition(
                ActivityDefinition.objects.select_related("life_area")
                .prefetch_related("rewards__skill")
                .get(pk=definition.pk)
            )
        },
        status=201,
    )


def _manual_activity_payload(request: HttpRequest) -> dict[str, Any]:
    content_type = (request.content_type or "").split(";", maxsplit=1)[0]
    if content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        data = dict(payload)
    else:
        data = request.POST.dict()

    if "activity_definition_id" in data and "activity_definition" not in data:
        data["activity_definition"] = data["activity_definition_id"]
    if "activityDefinitionId" in data and "activity_definition" not in data:
        data["activity_definition"] = data["activityDefinitionId"]
    if "startedAt" in data and "started_at" not in data:
        data["started_at"] = data["startedAt"]
    if not data.get("started_at"):
        now = timezone.localtime(timezone.now()).replace(second=0, microsecond=0)
        data["started_at"] = now.strftime("%Y-%m-%dT%H:%M")

    return data


def _json_payload(request: HttpRequest) -> dict[str, Any]:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON payload.") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object.")
    return payload


def _settings_user(request: HttpRequest):
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user

    User = get_user_model()
    existing_user = User.objects.order_by("id").first()
    if existing_user:
        return existing_user
    return User.objects.create_user(username=DEFAULT_HERO_NAME)


def _display_username(user) -> str:
    username = user.get_username().strip()
    if not username or username.casefold() == "wojownik":
        return DEFAULT_HERO_NAME
    return username


def _dashboard_username(request: HttpRequest) -> str:
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return _display_username(user)

    User = get_user_model()
    existing_user = User.objects.order_by("id").first()
    if existing_user:
        return _display_username(existing_user)

    return DEFAULT_HERO_NAME


def _required_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required.")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    clean = value.strip()
    if not clean:
        raise ValueError(f"{field_name} cannot be empty.")
    return clean


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Text fields must be strings.")
    return value


def _required_int(value: Any, *, field_name: str) -> int:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")
    return parsed


def _optional_int(value: Any, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    return _required_int(value, field_name=field_name)


def _optional_bool(value: Any) -> bool:
    if value in (None, ""):
        return False
    if isinstance(value, bool):
        return value
    raise ValueError("Boolean fields must be booleans.")


def _validation_error_response(message: str) -> JsonResponse:
    return JsonResponse(
        {
            "error": {
                "code": "validation_error",
                "message": message,
            }
        },
        status=400,
    )


def _serialize_dashboard_context(context: dict[str, Any]) -> dict[str, Any]:
    selected_range = context["selected_range"]
    return {
        "selected_range": {
            "key": selected_range.key,
            "label": selected_range.label,
            "start_date": selected_range.start_date.isoformat(),
            "end_date": selected_range.end_date.isoformat(),
            "start_at": selected_range.start_at.isoformat(),
            "end_at": selected_range.end_at.isoformat(),
        },
        "range_options": [
            {"key": key, "label": label} for key, label in context["range_options"]
        ],
        "stats": context["stats"],
        "hero": context["hero"],
        "resource_cards": context["resource_cards"],
        "attribute_rows": context["attribute_rows"],
        "daily_quests": context["daily_quests"],
        "active_challenge": context["active_challenge"],
        "habits": context["habits"],
        "habits_summary": context["habits_summary"],
        "weekly_progress": context["weekly_progress"],
        "achievements": context["achievements"],
        "journal_entries": context["journal_entries"],
        "skill_rows": [
            _serialize_skill_row(row) for row in context["skill_rows"]
        ],
        "latest_statuses": [
            _serialize_status_row(row) for row in context["latest_statuses"]
        ],
        "activity_definitions": _serialize_activity_definitions(),
        "xp_chart": context["xp_chart"],
        "time_chart": context["time_chart"],
    }


def _serialize_skill_row(row: dict[str, Any]) -> dict[str, Any]:
    skill = row["skill"]
    return {
        "id": skill.id,
        "name": skill.name,
        "life_area": (
            {"id": skill.life_area.id, "name": skill.life_area.name}
            if skill.life_area
            else None
        ),
        "total_xp": row["total_xp"],
        "level": row["level"],
        "progress": row["progress"],
        "range_xp": row["range_xp"],
        "range_minutes": row["range_minutes"],
    }


def _serialize_status_row(row: dict[str, Any]) -> dict[str, Any]:
    definition = row["definition"]
    entry = row["entry"]
    return {
        "definition": {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
        },
        "entry": (
            {
                "id": entry.id,
                "value": entry.value,
                "note": entry.note,
                "recorded_at": entry.recorded_at.isoformat(),
                "created_at": entry.created_at.isoformat(),
            }
            if entry
            else None
        ),
    }


def _serialize_activity_definitions() -> list[dict[str, Any]]:
    definitions = (
        ActivityDefinition.objects.select_related("life_area")
        .prefetch_related("rewards__skill")
        .order_by("name")
    )
    return [_serialize_activity_definition(definition) for definition in definitions]


def _serialize_activity_definition(definition: ActivityDefinition) -> dict[str, Any]:
    return {
        "id": definition.id,
        "name": definition.name,
        "description": definition.description,
        "life_area": (
            {"id": definition.life_area.id, "name": definition.life_area.name}
            if definition.life_area
            else None
        ),
        "rewards": [
            {
                "skill": {
                    "id": reward.skill.id,
                    "name": reward.skill.name,
                },
                "xp_per_minute": reward.xp_per_minute,
            }
            for reward in definition.rewards.all()
        ],
    }


def _serialize_skill_options() -> list[dict[str, Any]]:
    return [_serialize_skill_option(skill) for skill in Skill.objects.select_related("life_area")]


def _serialize_skill_option(skill: Skill) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "life_area": (
            {"id": skill.life_area.id, "name": skill.life_area.name}
            if skill.life_area
            else None
        ),
    }


def _serialize_life_area_options() -> list[dict[str, Any]]:
    return [
        {"id": area.id, "name": area.name, "description": area.description}
        for area in LifeArea.objects.order_by("name")
    ]


def _serialize_account(user) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": _display_username(user),
        "is_authenticated": user.is_authenticated,
    }


def _serialize_llm_provider_configs() -> list[dict[str, Any]]:
    configs = {
        config.provider: config
        for config in LlmProviderConfig.objects.filter(provider__in=LlmProvider.values)
    }
    rows = []
    for provider in LlmProvider.values:
        config = configs.get(provider)
        rows.append(
            {
                "provider": provider,
                "label": LlmProvider(provider).label,
                "model_name": config.model_name if config else "",
                "is_enabled": config.is_enabled if config else False,
                "api_key_set": bool(config and config.api_key),
                "api_key_preview": _mask_api_key(config.api_key if config else ""),
            }
        )
    return rows


def _mask_api_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}...{value[-4:]}"


def _serialize_activity_entry(entry: ActivityEntry) -> dict[str, Any]:
    xp_events = [
        {
            "id": event.id,
            "skill": {
                "id": event.skill.id,
                "name": event.skill.name,
            },
            "amount": event.amount,
            "source_type": event.source_type,
            "note": event.note,
            "earned_at": event.earned_at.isoformat(),
        }
        for event in entry.xp_events.all()
    ]
    return {
        "id": entry.id,
        "activity_definition": {
            "id": entry.activity_definition.id,
            "name": entry.activity_definition.name,
        },
        "source": entry.source,
        "minutes": entry.minutes,
        "started_at": entry.started_at.isoformat(),
        "created_at": entry.created_at.isoformat(),
        "total_xp": sum(event["amount"] for event in xp_events),
        "xp_events": xp_events,
    }
