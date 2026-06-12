from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from skills.models import Skill, XpEvent

from .choices import (
    CampaignCreatedBy,
    CampaignDifficulty,
    CampaignNodeKind,
    CampaignQuestUnlockMode,
    CampaignStatus,
    CreationSource,
    JournalEntryType,
    QuestDifficulty,
    QuestStatus,
    QuestType,
    TargetUnit,
)
from .exceptions import RpgValidationError
from .models import (
    Campaign,
    CampaignQuest,
    CampaignQuestDependency,
    JournalEntry,
    Quest,
    QuestCompletion,
    QuestReward,
)


def build_campaign_rows(
    *,
    status: str = "all",
    created_by: str = "",
    active_only: bool = False,
) -> list[dict[str, Any]]:
    campaigns = _campaign_queryset()
    if active_only:
        campaigns = campaigns.filter(status=CampaignStatus.ACTIVE)
    elif status and status != "all":
        campaigns = campaigns.filter(status=status)
    if created_by:
        campaigns = campaigns.filter(created_by=created_by)
    return [serialize_campaign(campaign, include_map=False) for campaign in campaigns]


def get_campaign_detail(campaign: Campaign) -> dict[str, Any]:
    return serialize_campaign(_campaign_queryset().get(pk=campaign.pk), include_map=True)


def serialize_campaign_studio(campaign: Campaign) -> dict[str, Any]:
    selected_campaign = _campaign_queryset().get(pk=campaign.pk)
    nodes = list(_campaign_quest_queryset(selected_campaign))
    states = _campaign_quest_states(selected_campaign, nodes)
    return {
        "campaign": serialize_campaign(selected_campaign, include_map=False),
        "nodes": [
            serialize_campaign_studio_node(node, state=states.get(node.id, "locked"))
            for node in nodes
        ],
        "edges": [
            serialize_campaign_studio_edge(edge)
            for edge in _campaign_edge_queryset(selected_campaign)
        ],
        "validation": validate_campaign_studio(selected_campaign),
        "available_node_types": [
            {"value": choice.value, "label": choice.label}
            for choice in CampaignNodeKind
        ],
    }


def serialize_campaign_studio_node(
    node: CampaignQuest,
    *,
    state: str | None = None,
) -> dict[str, Any]:
    selected_state = state
    if selected_state is None:
        campaign_nodes = list(_campaign_quest_queryset(node.campaign))
        selected_state = _campaign_quest_states(node.campaign, campaign_nodes).get(
            node.id,
            "locked",
        )
    return {
        "id": node.id,
        "node_kind": node.node_kind,
        "quest_id": node.quest_id,
        "title": node.quest.title,
        "description": node.quest.description,
        "state": selected_state,
        "stage": node.stage,
        "order": node.order,
        "is_required": node.is_required,
        "unlock_mode": node.unlock_mode,
        "position": {
            "x": node.map_x,
            "y": node.map_y,
        },
        "map_x": node.map_x,
        "map_y": node.map_y,
        "reward_xp": node.quest.reward_xp_total(),
        "target_value": node.quest.target_value,
        "target_unit": node.quest.target_unit,
        "quest_type": node.quest.quest_type,
        "difficulty": node.quest.difficulty,
        "config": node.config or {},
    }


def serialize_campaign_studio_edge(edge: CampaignQuestDependency) -> dict[str, int]:
    return {
        "id": edge.id,
        "source_node_id": edge.depends_on_id,
        "target_node_id": edge.campaign_quest_id,
        "from": edge.depends_on_id,
        "to": edge.campaign_quest_id,
    }


def create_campaign(
    *,
    title: str,
    description: str = "",
    difficulty: str = CampaignDifficulty.NORMAL,
    status: str = CampaignStatus.DRAFT,
    starts_on: date | None = None,
    due_on: date | None = None,
    life_area_id: int | None = None,
    reward_xp: int = 0,
    reward_skill_id: int | None = None,
    reward_title: str = "",
    created_by: str = CampaignCreatedBy.USER,
    owner_id: int | None = None,
    ai_prompt: str = "",
    ai_provider: str = "",
    ai_model: str = "",
) -> Campaign:
    campaign = Campaign(
        title=title,
        description=description,
        status=status,
        created_by=created_by,
        difficulty=difficulty,
        starts_on=starts_on,
        due_on=due_on,
        life_area_id=life_area_id,
        reward_xp=reward_xp,
        reward_skill_id=reward_skill_id,
        reward_title=reward_title,
        owner_id=owner_id,
        ai_prompt=ai_prompt,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )
    _clean_or_raise(campaign)
    campaign.save()
    if created_by == CampaignCreatedBy.AI:
        _try_create_campaign_ai_draft_journal(campaign)
    return campaign


def update_campaign(
    *,
    campaign: Campaign,
    updates: dict[str, Any],
) -> Campaign:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if locked_campaign.status != CampaignStatus.DRAFT:
            raise RpgValidationError("Only draft campaigns can be edited.")

        allowed_fields = {
            "title",
            "description",
            "difficulty",
            "starts_on",
            "due_on",
            "life_area_id",
            "reward_xp",
            "reward_skill_id",
            "reward_title",
            "ai_prompt",
            "ai_provider",
            "ai_model",
        }
        update_fields: list[str] = []
        for field_name, value in updates.items():
            if field_name not in allowed_fields:
                continue
            setattr(locked_campaign, field_name, value)
            update_fields.append(field_name)
        if update_fields:
            update_fields.append("updated_at")
            _clean_or_raise(locked_campaign)
            locked_campaign.save(update_fields=update_fields)
    return Campaign.objects.get(pk=campaign.pk)


def add_quest_to_campaign(
    *,
    campaign: Campaign,
    quest: Quest | None = None,
    quest_id: int | None = None,
    quest_title: str = "",
    quest_description: str = "",
    target_value: int = 1,
    target_unit: str = TargetUnit.COUNT,
    quest_type: str = QuestType.ONE_TIME,
    quest_difficulty: str = QuestDifficulty.NORMAL,
    reward_skill_id: int | None = None,
    reward_xp: int = 0,
    stage: str = "",
    order: int = 0,
    is_required: bool = True,
    unlock_mode: str = CampaignQuestUnlockMode.AFTER_DEPENDENCIES,
    node_kind: str = CampaignNodeKind.QUEST,
    config: dict[str, Any] | None = None,
    map_x: int = 0,
    map_y: int = 0,
    depends_on_ids: list[int] | None = None,
) -> CampaignQuest:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        selected_quest = _resolve_or_create_quest(
            campaign=locked_campaign,
            quest=quest,
            quest_id=quest_id,
            title=quest_title,
            description=quest_description,
            target_value=target_value,
            target_unit=target_unit,
            quest_type=quest_type,
            difficulty=quest_difficulty,
            reward_skill_id=reward_skill_id,
            reward_xp=reward_xp,
        )
        campaign_quest, _ = CampaignQuest.objects.update_or_create(
            campaign=locked_campaign,
            quest=selected_quest,
            defaults={
                "stage": stage,
                "order": order,
                "is_required": is_required,
                "unlock_mode": unlock_mode,
                "node_kind": _normalize_node_kind(node_kind),
                "config": _normalize_config(config),
                "map_x": map_x,
                "map_y": map_y,
            },
        )
        _clean_or_raise(campaign_quest)

        if depends_on_ids:
            dependency_pairs = list(_current_dependency_pairs(locked_campaign))
            dependency_pairs.extend(
                {
                    "campaign_quest_id": campaign_quest.id,
                    "depends_on_id": depends_on_id,
                }
                for depends_on_id in depends_on_ids
            )
            set_campaign_dependencies(
                campaign=locked_campaign,
                dependencies=dependency_pairs,
            )
    return CampaignQuest.objects.select_related("campaign", "quest").get(
        pk=campaign_quest.pk
    )


def create_campaign_node(
    *,
    campaign: Campaign,
    node_kind: str = CampaignNodeKind.QUEST,
    quest_id: int | None = None,
    title: str = "",
    description: str = "",
    target_value: int = 1,
    target_unit: str = TargetUnit.CHECK,
    quest_type: str = QuestType.ONE_TIME,
    difficulty: str = QuestDifficulty.NORMAL,
    reward_skill_id: int | None = None,
    reward_xp: int = 0,
    stage: str = "",
    order: int = 0,
    is_required: bool = True,
    unlock_mode: str = CampaignQuestUnlockMode.AFTER_DEPENDENCIES,
    map_x: int = 0,
    map_y: int = 0,
    config: dict[str, Any] | None = None,
) -> CampaignQuest:
    clean_kind = _normalize_node_kind(node_kind)
    node_title = title.strip() if title else f"New {CampaignNodeKind(clean_kind).label}"
    return add_quest_to_campaign(
        campaign=campaign,
        quest_id=quest_id,
        quest_title=node_title,
        quest_description=description,
        target_value=target_value,
        target_unit=target_unit,
        quest_type=quest_type,
        quest_difficulty=difficulty,
        reward_skill_id=reward_skill_id,
        reward_xp=reward_xp,
        stage=stage,
        order=order,
        is_required=is_required,
        unlock_mode=unlock_mode,
        node_kind=clean_kind,
        config=config,
        map_x=map_x,
        map_y=map_y,
    )


def update_campaign_node(
    *,
    campaign: Campaign,
    node_id: int,
    updates: dict[str, Any],
) -> CampaignQuest:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        node = _get_campaign_node_for_update(
            campaign=locked_campaign,
            node_id=node_id,
        )

        node_update_fields: list[str] = []
        for field_name in (
            "stage",
            "order",
            "is_required",
            "unlock_mode",
            "map_x",
            "map_y",
        ):
            if field_name in updates:
                setattr(node, field_name, updates[field_name])
                node_update_fields.append(field_name)
        if "position" in updates:
            position = updates["position"]
            node.map_x = int(position["x"])
            node.map_y = int(position["y"])
            node_update_fields.extend(["map_x", "map_y"])
        if "node_kind" in updates:
            node.node_kind = _normalize_node_kind(str(updates["node_kind"]))
            node_update_fields.append("node_kind")
        if "config" in updates:
            node.config = _normalize_config(updates["config"])
            node_update_fields.append("config")
        if node_update_fields:
            node_update_fields.append("updated_at")
            _clean_or_raise(node)
            node.save(update_fields=sorted(set(node_update_fields)))

        quest = node.quest
        quest_update_fields: list[str] = []
        quest_field_map = {
            "title": "title",
            "description": "description",
            "target_value": "target_value",
            "target_unit": "target_unit",
            "quest_type": "quest_type",
            "difficulty": "difficulty",
        }
        for payload_key, model_field in quest_field_map.items():
            if payload_key in updates:
                setattr(quest, model_field, updates[payload_key])
                quest_update_fields.append(model_field)
        if quest_update_fields:
            quest_update_fields.append("updated_at")
            _clean_or_raise(quest)
            quest.save(update_fields=sorted(set(quest_update_fields)))

        if "reward_xp" in updates or "reward_skill_id" in updates:
            reward_xp = int(
                updates.get("reward_xp")
                if "reward_xp" in updates
                else quest.reward_xp_total()
            )
            _replace_quest_reward(
                quest=quest,
                reward_skill_id=updates.get("reward_skill_id"),
                reward_xp=reward_xp,
            )
    return CampaignQuest.objects.select_related("campaign", "quest").get(pk=node_id)


def delete_campaign_node(*, campaign: Campaign, node_id: int) -> None:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        node = _get_campaign_node_for_update(
            campaign=locked_campaign,
            node_id=node_id,
        )
        node.delete()


def bulk_update_campaign_node_positions(
    *,
    campaign: Campaign,
    positions: list[dict[str, int]],
) -> list[CampaignQuest]:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_position_editable(locked_campaign)
        nodes_by_id = {
            node.id: node
            for node in CampaignQuest.objects.select_for_update().filter(
                campaign=locked_campaign,
            )
        }
        updated_nodes: list[CampaignQuest] = []
        for position in positions:
            node_id = int(position.get("node_id") or position.get("id") or 0)
            node = nodes_by_id.get(node_id)
            if node is None:
                raise RpgValidationError("Campaign node does not exist.")
            if "position" in position:
                canvas_position = position["position"]
                node.map_x = int(canvas_position["x"])
                node.map_y = int(canvas_position["y"])
            else:
                node.map_x = int(position.get("map_x", position.get("x", node.map_x)))
                node.map_y = int(position.get("map_y", position.get("y", node.map_y)))
            node.updated_at = timezone.now()
            _clean_or_raise(node)
            updated_nodes.append(node)
        if updated_nodes:
            CampaignQuest.objects.bulk_update(updated_nodes, ["map_x", "map_y", "updated_at"])
    return list(_campaign_quest_queryset(campaign))


def create_campaign_edge(
    *,
    campaign: Campaign,
    source_node_id: int,
    target_node_id: int,
) -> CampaignQuestDependency:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        source = _get_campaign_node_for_update(
            campaign=locked_campaign,
            node_id=source_node_id,
        )
        target = _get_campaign_node_for_update(
            campaign=locked_campaign,
            node_id=target_node_id,
        )
        if source.id == target.id:
            raise RpgValidationError("Campaign quest cannot depend on itself.")
        current_edges = list(_current_edge_tuples(locked_campaign))
        candidate_edges = current_edges + [(source.id, target.id)]
        campaign_quest_ids = set(
            CampaignQuest.objects.filter(campaign=locked_campaign).values_list(
                "id",
                flat=True,
            )
        )
        _raise_if_cycle(campaign_quest_ids, candidate_edges)
        edge, _ = CampaignQuestDependency.objects.get_or_create(
            campaign_quest=target,
            depends_on=source,
        )
        _clean_or_raise(edge)
    return CampaignQuestDependency.objects.select_related(
        "campaign_quest",
        "depends_on",
    ).get(pk=edge.pk)


def delete_campaign_edge(*, campaign: Campaign, edge_id: int) -> None:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        deleted_count, _ = CampaignQuestDependency.objects.filter(
            pk=edge_id,
            campaign_quest__campaign=locked_campaign,
        ).delete()
        if deleted_count == 0:
            raise RpgValidationError("Campaign edge does not exist.")


def replace_campaign_edges(
    *,
    campaign: Campaign,
    edges: list[dict[str, int]],
) -> list[CampaignQuestDependency]:
    dependencies = [
        {
            "campaign_quest_id": int(edge.get("target_node_id") or edge.get("to") or 0),
            "depends_on_id": int(edge.get("source_node_id") or edge.get("from") or 0),
        }
        for edge in edges
    ]
    return set_campaign_dependencies(campaign=campaign, dependencies=dependencies)


def set_campaign_dependencies(
    *,
    campaign: Campaign,
    dependencies: list[dict[str, int]],
) -> list[CampaignQuestDependency]:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        _ensure_campaign_structural_editable(locked_campaign)
        campaign_quest_ids = set(
            CampaignQuest.objects.filter(campaign=locked_campaign).values_list(
                "id",
                flat=True,
            )
        )
        edges: list[tuple[int, int]] = []
        for dependency in dependencies:
            campaign_quest_id = int(dependency.get("campaign_quest_id", 0))
            depends_on_id = int(dependency.get("depends_on_id", 0))
            if campaign_quest_id == depends_on_id:
                raise RpgValidationError("Campaign quest cannot depend on itself.")
            if (
                campaign_quest_id not in campaign_quest_ids
                or depends_on_id not in campaign_quest_ids
            ):
                raise RpgValidationError(
                    "Campaign dependencies must use quests from the same campaign."
                )
            edges.append((depends_on_id, campaign_quest_id))

        _raise_if_cycle(campaign_quest_ids, edges)
        CampaignQuestDependency.objects.filter(
            campaign_quest__campaign=locked_campaign
        ).delete()

        created: list[CampaignQuestDependency] = []
        seen_edges: set[tuple[int, int]] = set()
        for depends_on_id, campaign_quest_id in edges:
            edge = (depends_on_id, campaign_quest_id)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            dependency = CampaignQuestDependency(
                campaign_quest_id=campaign_quest_id,
                depends_on_id=depends_on_id,
            )
            _clean_or_raise(dependency)
            dependency.save()
            created.append(dependency)
    return created


def validate_campaign_graph(campaign: Campaign) -> None:
    campaign_quest_ids = set(
        CampaignQuest.objects.filter(campaign=campaign).values_list("id", flat=True)
    )
    edges = [
        (dependency.depends_on_id, dependency.campaign_quest_id)
        for dependency in CampaignQuestDependency.objects.filter(
            campaign_quest__campaign=campaign
        )
    ]
    _raise_if_cycle(campaign_quest_ids, edges)


def validate_campaign_studio(campaign: Campaign) -> dict[str, Any]:
    nodes = list(CampaignQuest.objects.filter(campaign=campaign).select_related("quest"))
    node_ids = {node.id for node in nodes}
    dependencies = list(
        CampaignQuestDependency.objects.filter(campaign_quest__campaign=campaign)
        .select_related("campaign_quest", "depends_on")
        .order_by("depends_on_id", "campaign_quest_id", "id")
    )
    edges: list[tuple[int, int]] = []
    issues: list[dict[str, Any]] = []

    def add_issue(
        *,
        code: str,
        message: str,
        severity: str = "error",
        node_id: int | None = None,
        edge_id: int | None = None,
    ) -> None:
        issue: dict[str, Any] = {
            "code": code,
            "severity": severity,
            "message": message,
        }
        if node_id is not None:
            issue["node_id"] = node_id
        if edge_id is not None:
            issue["edge_id"] = edge_id
        issues.append(issue)

    for dependency in dependencies:
        if dependency.depends_on_id == dependency.campaign_quest_id:
            add_issue(
                code="self_edge",
                message="A campaign node cannot depend on itself.",
                node_id=dependency.campaign_quest_id,
                edge_id=dependency.id,
            )
            continue
        if (
            dependency.depends_on.campaign_id != campaign.id
            or dependency.campaign_quest.campaign_id != campaign.id
        ):
            add_issue(
                code="cross_campaign_edge",
                message="Campaign edges must connect nodes from the same campaign.",
                edge_id=dependency.id,
            )
            continue
        edges.append((dependency.depends_on_id, dependency.campaign_quest_id))

    has_nodes = bool(nodes)
    required_node_ids = {node.id for node in nodes if node.is_required}
    has_required_node = bool(required_node_ids)
    incoming_by_target: dict[int, set[int]] = {node_id: set() for node_id in node_ids}
    adjacency: dict[int, set[int]] = {node_id: set() for node_id in node_ids}
    for source_id, target_id in edges:
        incoming_by_target.setdefault(target_id, set()).add(source_id)
        adjacency.setdefault(source_id, set()).add(target_id)

    starting_node_ids = {
        node.id
        for node in nodes
        if not incoming_by_target.get(node.id)
        or node.unlock_mode == CampaignQuestUnlockMode.IMMEDIATE
    }
    has_starting_node = bool(starting_node_ids)

    has_no_cycles = True
    try:
        _raise_if_cycle(node_ids, edges)
    except RpgValidationError:
        has_no_cycles = False
        add_issue(
            code="cycle_detected",
            message="Campaign dependency graph cannot contain cycles.",
        )

    reachable_ids = _reachable_node_ids(
        starting_node_ids=starting_node_ids,
        adjacency=adjacency,
    )
    unreachable_required_ids = (
        sorted(required_node_ids - reachable_ids)
        if has_no_cycles and has_starting_node
        else sorted(required_node_ids)
    )

    if not has_nodes:
        add_issue(
            code="missing_nodes",
            message="Campaign needs at least one node.",
        )
    if not has_required_node:
        add_issue(
            code="missing_required_node",
            message="Campaign needs at least one required node.",
        )
    if not has_starting_node:
        add_issue(
            code="missing_starting_node",
            message="Campaign needs at least one starting node.",
        )
    if unreachable_required_ids:
        for node_id in unreachable_required_ids:
            add_issue(
                code="unreachable_required_node",
                message="Required node is not reachable from any starting node.",
                node_id=node_id,
            )

    checks = [
        {
            "code": "has_nodes",
            "passed": has_nodes,
            "message": "Campaign has at least one node.",
        },
        {
            "code": "has_required_node",
            "passed": has_required_node,
            "message": "Campaign has at least one required node.",
        },
        {
            "code": "has_starting_node",
            "passed": has_starting_node,
            "message": "Campaign has a starting node.",
        },
        {
            "code": "has_no_cycles",
            "passed": has_no_cycles,
            "message": "Campaign graph has no cycles.",
        },
        {
            "code": "all_required_nodes_reachable",
            "passed": not unreachable_required_ids,
            "message": "All required nodes are reachable from a starting node.",
        },
    ]
    return {
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "checks": checks,
        "issues": issues,
    }


def publish_campaign(*, campaign: Campaign) -> Campaign:
    validation = validate_campaign_studio(campaign)
    if not validation["valid"]:
        first_issue = validation["issues"][0]
        raise RpgValidationError(first_issue["message"])
    return activate_campaign(campaign=campaign)


def activate_campaign(*, campaign: Campaign) -> Campaign:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if locked_campaign.status == CampaignStatus.ACTIVE:
            return locked_campaign
        if locked_campaign.status != CampaignStatus.DRAFT:
            raise RpgValidationError("Only draft campaigns can be activated.")

        required_count = CampaignQuest.objects.filter(
            campaign=locked_campaign,
            is_required=True,
        ).count()
        if required_count == 0:
            raise RpgValidationError("Campaign needs at least one required quest.")

        validation = validate_campaign_studio(locked_campaign)
        if not validation["valid"]:
            first_issue = validation["issues"][0]
            raise RpgValidationError(first_issue["message"])
        locked_campaign.status = CampaignStatus.ACTIVE
        if locked_campaign.starts_on is None:
            locked_campaign.starts_on = timezone.localdate()
        _clean_or_raise(locked_campaign)
        locked_campaign.save(update_fields=["status", "starts_on", "updated_at"])

        for quest in Quest.objects.filter(campaign_links__campaign=locked_campaign):
            if quest.status == QuestStatus.DRAFT:
                quest.status = QuestStatus.ACTIVE
                _clean_or_raise(quest)
                quest.save(update_fields=["status", "updated_at"])

        if not _available_campaign_quest_ids(locked_campaign):
            raise RpgValidationError(
                "Campaign needs at least one available starting quest."
            )

    _try_create_campaign_activation_journal(locked_campaign)
    return Campaign.objects.get(pk=locked_campaign.pk)


def archive_campaign(*, campaign: Campaign) -> Campaign:
    with transaction.atomic():
        locked_campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        if locked_campaign.status != CampaignStatus.ARCHIVED:
            locked_campaign.status = CampaignStatus.ARCHIVED
            _clean_or_raise(locked_campaign)
            locked_campaign.save(update_fields=["status", "updated_at"])
    return locked_campaign


def complete_campaign_if_ready(*, campaign: Campaign) -> dict[str, Any]:
    completed_now = False
    achievement_unlocks: list[Any] = []
    with transaction.atomic():
        locked_campaign = (
            Campaign.objects.select_for_update().get(pk=campaign.pk)
        )
        if locked_campaign.status == CampaignStatus.COMPLETED:
            return {
                "campaign": locked_campaign,
                "completed": False,
                "xp_events": get_campaign_xp_events(locked_campaign),
                "achievement_unlocks": [],
            }
        if locked_campaign.status != CampaignStatus.ACTIVE:
            return {
                "campaign": locked_campaign,
                "completed": False,
                "xp_events": [],
                "achievement_unlocks": [],
            }
        if not _required_campaign_quests_completed(locked_campaign):
            return {
                "campaign": locked_campaign,
                "completed": False,
                "xp_events": [],
                "achievement_unlocks": [],
            }

        locked_campaign.status = CampaignStatus.COMPLETED
        locked_campaign.completed_at = timezone.now()
        xp_events = award_campaign_xp(locked_campaign)
        _clean_or_raise(locked_campaign)
        locked_campaign.save(
            update_fields=[
                "status",
                "completed_at",
                "xp_awarded_at",
                "updated_at",
            ]
        )
        completed_now = True

    if completed_now:
        _try_create_campaign_completion_journal(locked_campaign)
        from .services import evaluate_achievements

        achievement_unlocks = evaluate_achievements(
            source_type="campaign_completion",
            source_id=locked_campaign.id,
        )
    return {
        "campaign": locked_campaign,
        "completed": completed_now,
        "xp_events": xp_events,
        "achievement_unlocks": achievement_unlocks,
    }


def complete_campaigns_for_quest(*, quest: Quest) -> list[dict[str, Any]]:
    campaign_ids = (
        Campaign.objects.filter(
            status=CampaignStatus.ACTIVE,
            campaign_quests__quest=quest,
        )
        .distinct()
        .values_list("id", flat=True)
    )
    results: list[dict[str, Any]] = []
    for campaign_id in campaign_ids:
        results.append(
            complete_campaign_if_ready(campaign=Campaign.objects.get(pk=campaign_id))
        )
    return results


def award_campaign_xp(campaign: Campaign) -> list[XpEvent]:
    if campaign.xp_awarded_at is not None:
        return get_campaign_xp_events(campaign)
    if campaign.reward_xp <= 0 or campaign.reward_skill_id is None:
        return []

    event = campaign.reward_skill.add_xp(
        amount=campaign.reward_xp,
        source_type="campaign",
        note=_campaign_xp_note(campaign),
    )
    campaign.xp_awarded_at = timezone.now()
    return [event]


def get_campaign_xp_events(campaign: Campaign) -> list[XpEvent]:
    return list(
        XpEvent.objects.select_related("skill").filter(
            source_type="campaign",
            note__endswith=f"campaign_id={campaign.id}",
        )
    )


def generate_campaign_draft(
    *,
    goal: str,
    timeframe_days: int | None = None,
    available_minutes_per_day: int | None = None,
    difficulty: str = CampaignDifficulty.NORMAL,
    skill_ids: list[int] | None = None,
    notes: str = "",
    owner_id: int | None = None,
    ai_provider: str = "",
    ai_model: str = "",
) -> Campaign:
    clean_goal = goal.strip()
    if not clean_goal:
        raise RpgValidationError("goal is required.")

    selected_skills = list(Skill.objects.filter(id__in=skill_ids or []).order_by("name"))
    reward_skill = selected_skills[0] if selected_skills else Skill.objects.order_by("name").first()
    timeframe = timeframe_days or 30
    reward_xp = max(100, min(timeframe * 10, 1000)) if reward_skill else 0
    due_on = timezone.localdate() + timedelta(days=timeframe) if timeframe > 0 else None

    campaign = create_campaign(
        title=f"{clean_goal[:120]} Arc",
        description=_ai_draft_description(
            goal=clean_goal,
            timeframe_days=timeframe_days,
            available_minutes_per_day=available_minutes_per_day,
            notes=notes,
        ),
        difficulty=difficulty,
        due_on=due_on,
        reward_xp=reward_xp,
        reward_skill_id=reward_skill.id if reward_skill else None,
        reward_title="AI Designed Path",
        created_by=CampaignCreatedBy.AI,
        owner_id=owner_id,
        ai_prompt=clean_goal,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )

    quest_specs = (
        ("Clarify the target", "Define the exact outcome and success criteria.", 10, 20),
        ("Complete the first focused session", "Spend focused time moving the goal forward.", 50, 35),
        ("Review and adjust the path", "Reflect on progress and refine next actions.", 90, 20),
    )
    created_nodes: list[CampaignQuest] = []
    previous_id: int | None = None
    for index, (title, description, map_x, map_y) in enumerate(quest_specs, start=1):
        node = add_quest_to_campaign(
            campaign=campaign,
            quest_title=title,
            quest_description=description,
            target_value=1,
            target_unit=TargetUnit.CHECK,
            quest_type=QuestType.ONE_TIME,
            quest_difficulty=QuestDifficulty.NORMAL,
            reward_skill_id=reward_skill.id if reward_skill else None,
            reward_xp=25 if reward_skill else 0,
            stage="AI Draft",
            order=index * 10,
            unlock_mode=(
                CampaignQuestUnlockMode.IMMEDIATE
                if previous_id is None
                else CampaignQuestUnlockMode.AFTER_DEPENDENCIES
            ),
            map_x=map_x,
            map_y=map_y,
            depends_on_ids=[previous_id] if previous_id else [],
        )
        created_nodes.append(node)
        previous_id = node.id
    return campaign


def serialize_campaign(
    campaign: Campaign,
    *,
    include_map: bool = True,
) -> dict[str, Any]:
    progress = get_campaign_progress(campaign)
    row: dict[str, Any] = {
        "id": campaign.id,
        "title": campaign.title,
        "description": campaign.description,
        "status": campaign.status,
        "created_by": campaign.created_by,
        "difficulty": campaign.difficulty,
        "progress_percent": progress["progress_percent"],
        "completed_required_quests": progress["completed_required_quests"],
        "total_required_quests": progress["total_required_quests"],
        "available_quests": progress["available_quests"],
        "locked_quests": progress["locked_quests"],
        "reward_xp": campaign.reward_xp,
        "reward_title": campaign.reward_title,
        "reward_skill": (
            {"id": campaign.reward_skill_id, "name": campaign.reward_skill.name}
            if campaign.reward_skill_id
            else None
        ),
        "life_area": (
            {"id": campaign.life_area_id, "name": campaign.life_area.name}
            if campaign.life_area_id
            else None
        ),
        "starts_on": campaign.starts_on.isoformat() if campaign.starts_on else None,
        "due_on": campaign.due_on.isoformat() if campaign.due_on else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "xp_awarded_at": campaign.xp_awarded_at.isoformat() if campaign.xp_awarded_at else None,
        "ai_provider": campaign.ai_provider,
        "ai_model": campaign.ai_model,
        "created_at": campaign.created_at.isoformat(),
        "updated_at": campaign.updated_at.isoformat(),
    }
    if include_map:
        row["map"] = build_campaign_map(campaign)
        row["stages"] = build_campaign_stages(campaign)
    return row


def get_campaign_progress(campaign: Campaign) -> dict[str, int]:
    nodes = list(_campaign_quest_queryset(campaign))
    states = _campaign_quest_states(campaign, nodes)
    required_nodes = [node for node in nodes if node.is_required]
    completed_required = sum(
        1 for node in required_nodes if states.get(node.id) == "completed"
    )
    total_required = len(required_nodes)
    progress_percent = (
        int((completed_required / total_required) * 100) if total_required else 0
    )
    return {
        "completed_required_quests": completed_required,
        "total_required_quests": total_required,
        "available_quests": sum(1 for state in states.values() if state == "available"),
        "locked_quests": sum(1 for state in states.values() if state == "locked"),
        "progress_percent": min(100, progress_percent),
    }


def build_campaign_map(campaign: Campaign) -> dict[str, Any]:
    nodes = list(_campaign_quest_queryset(campaign))
    states = _campaign_quest_states(campaign, nodes)
    reward_totals = {
        node.quest_id: node.quest.reward_xp_total()
        for node in nodes
    }
    return {
        "nodes": [
            {
                "id": node.id,
                "quest_id": node.quest_id,
                "title": node.quest.title,
                "description": node.quest.description,
                "stage": node.stage,
                "state": states[node.id],
                "is_required": node.is_required,
                "unlock_mode": node.unlock_mode,
                "map_x": node.map_x,
                "map_y": node.map_y,
                "reward_xp": reward_totals.get(node.quest_id, 0),
                "target_value": node.quest.target_value,
                "target_unit": node.quest.target_unit,
                "difficulty": node.quest.difficulty,
            }
            for node in nodes
        ],
        "edges": [
            {
                "id": dependency.id,
                "from": dependency.depends_on_id,
                "to": dependency.campaign_quest_id,
            }
            for dependency in CampaignQuestDependency.objects.filter(
                campaign_quest__campaign=campaign
            ).order_by("depends_on__order", "campaign_quest__order", "id")
        ],
    }


def build_campaign_stages(campaign: Campaign) -> list[dict[str, Any]]:
    nodes = list(_campaign_quest_queryset(campaign))
    states = _campaign_quest_states(campaign, nodes)
    stages: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        stage = node.stage or "Campaign"
        stages.setdefault(stage, []).append(
            {
                "id": node.id,
                "quest_id": node.quest_id,
                "title": node.quest.title,
                "state": states[node.id],
                "is_required": node.is_required,
                "order": node.order,
            }
        )
    return [
        {"name": stage, "quests": stage_nodes}
        for stage, stage_nodes in stages.items()
    ]


def _campaign_queryset() -> QuerySet[Campaign]:
    return (
        Campaign.objects.select_related("life_area", "reward_skill", "owner")
        .prefetch_related(
            "campaign_quests__quest__rewards__skill",
            "campaign_quests__dependencies",
        )
        .order_by("status", "due_on", "title", "id")
    )


def _campaign_quest_queryset(campaign: Campaign) -> QuerySet[CampaignQuest]:
    return (
        CampaignQuest.objects.filter(campaign=campaign)
        .select_related("quest")
        .prefetch_related("quest__rewards__skill", "dependencies")
        .order_by("stage", "order", "id")
    )


def _campaign_edge_queryset(campaign: Campaign) -> QuerySet[CampaignQuestDependency]:
    return (
        CampaignQuestDependency.objects.filter(campaign_quest__campaign=campaign)
        .select_related("campaign_quest", "depends_on")
        .order_by("depends_on__order", "campaign_quest__order", "id")
    )


def _ensure_campaign_structural_editable(campaign: Campaign) -> None:
    if campaign.status != CampaignStatus.DRAFT:
        raise RpgValidationError("Campaign structure can be edited only while draft.")


def _ensure_campaign_position_editable(campaign: Campaign) -> None:
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.ACTIVE}:
        raise RpgValidationError(
            "Campaign node positions can be edited only while draft or active."
        )


def _normalize_node_kind(node_kind: str) -> str:
    clean_kind = (node_kind or CampaignNodeKind.QUEST).strip()
    valid_kinds = {choice.value for choice in CampaignNodeKind}
    if clean_kind not in valid_kinds:
        raise RpgValidationError("Unsupported campaign node kind.")
    return clean_kind


def _normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise RpgValidationError("Campaign node config must be an object.")
    return config


def _get_campaign_node_for_update(
    *,
    campaign: Campaign,
    node_id: int,
) -> CampaignQuest:
    node = (
        CampaignQuest.objects.select_for_update()
        .select_related("campaign", "quest")
        .filter(pk=node_id, campaign=campaign)
        .first()
    )
    if node is None:
        raise RpgValidationError("Campaign node does not exist.")
    return node


def _resolve_or_create_quest(
    *,
    campaign: Campaign,
    quest: Quest | None,
    quest_id: int | None,
    title: str,
    description: str,
    target_value: int,
    target_unit: str,
    quest_type: str,
    difficulty: str,
    reward_skill_id: int | None,
    reward_xp: int,
) -> Quest:
    if quest is not None:
        return quest
    if quest_id is not None:
        selected_quest = Quest.objects.filter(pk=quest_id).first()
        if selected_quest is None:
            raise RpgValidationError("Quest does not exist.")
        return selected_quest

    created_by = (
        CreationSource.AI
        if campaign.created_by == CampaignCreatedBy.AI
        else CreationSource.MANUAL
    )
    status = QuestStatus.DRAFT if created_by == CreationSource.AI else QuestStatus.ACTIVE
    selected_quest = Quest(
        title=title,
        description=description,
        quest_type=quest_type,
        status=status,
        difficulty=difficulty,
        target_value=target_value,
        target_unit=target_unit,
        created_by=created_by,
    )
    _clean_or_raise(selected_quest)
    selected_quest.save()

    if reward_skill_id and reward_xp > 0:
        reward = QuestReward(
            quest=selected_quest,
            skill_id=reward_skill_id,
            xp_amount=reward_xp,
        )
        _clean_or_raise(reward)
        reward.save()
    return selected_quest


def _current_dependency_pairs(campaign: Campaign) -> list[dict[str, int]]:
    return [
        {
            "campaign_quest_id": dependency.campaign_quest_id,
            "depends_on_id": dependency.depends_on_id,
        }
        for dependency in CampaignQuestDependency.objects.filter(
            campaign_quest__campaign=campaign
        )
    ]


def _current_edge_tuples(campaign: Campaign) -> list[tuple[int, int]]:
    return [
        (dependency.depends_on_id, dependency.campaign_quest_id)
        for dependency in CampaignQuestDependency.objects.filter(
            campaign_quest__campaign=campaign
        )
    ]


def _reachable_node_ids(
    *,
    starting_node_ids: set[int],
    adjacency: dict[int, set[int]],
) -> set[int]:
    reachable: set[int] = set()
    stack = list(starting_node_ids)
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(adjacency.get(node_id, set()) - reachable)
    return reachable


def _replace_quest_reward(
    *,
    quest: Quest,
    reward_skill_id: int | None,
    reward_xp: int,
) -> None:
    if reward_xp <= 0:
        QuestReward.objects.filter(quest=quest).delete()
        return
    selected_skill_id = reward_skill_id
    if selected_skill_id is None:
        existing_reward = QuestReward.objects.filter(quest=quest).first()
        selected_skill_id = existing_reward.skill_id if existing_reward else None
    if selected_skill_id is None:
        raise RpgValidationError("Reward XP requires a reward skill.")

    QuestReward.objects.filter(quest=quest).exclude(skill_id=selected_skill_id).delete()
    reward, _ = QuestReward.objects.update_or_create(
        quest=quest,
        skill_id=selected_skill_id,
        defaults={"xp_amount": reward_xp},
    )
    _clean_or_raise(reward)


def _raise_if_cycle(node_ids: set[int], edges: list[tuple[int, int]]) -> None:
    adjacency: dict[int, list[int]] = {node_id: [] for node_id in node_ids}
    for source_id, target_id in edges:
        adjacency.setdefault(source_id, []).append(target_id)

    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(node_id: int) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        for next_id in adjacency.get(node_id, []):
            if visit(next_id):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    if any(visit(node_id) for node_id in node_ids):
        raise RpgValidationError("Campaign dependency graph cannot contain cycles.")


def _completed_quest_ids(quest_ids: list[int]) -> set[int]:
    return set(
        QuestCompletion.objects.filter(
            quest_id__in=quest_ids,
            completed_at__isnull=False,
        ).values_list("quest_id", flat=True)
    )


def _campaign_quest_states(
    campaign: Campaign,
    nodes: list[CampaignQuest],
) -> dict[int, str]:
    completed_ids = _completed_quest_ids([node.quest_id for node in nodes])
    dependency_map: dict[int, list[CampaignQuestDependency]] = {
        node.id: list(node.dependencies.all())
        for node in nodes
    }
    states: dict[int, str] = {}
    for node in nodes:
        if node.quest_id in completed_ids:
            states[node.id] = "completed"
            continue
        if campaign.status != CampaignStatus.ACTIVE:
            states[node.id] = "locked"
            continue
        if node.unlock_mode == CampaignQuestUnlockMode.IMMEDIATE:
            states[node.id] = "available"
            continue
        if node.unlock_mode == CampaignQuestUnlockMode.MANUAL:
            states[node.id] = "locked"
            continue
        dependencies = dependency_map.get(node.id, [])
        states[node.id] = (
            "available"
            if all(dependency.depends_on.quest_id in completed_ids for dependency in dependencies)
            else "locked"
        )
    return states


def _available_campaign_quest_ids(campaign: Campaign) -> set[int]:
    nodes = list(_campaign_quest_queryset(campaign))
    states = _campaign_quest_states(campaign, nodes)
    return {node_id for node_id, state in states.items() if state == "available"}


def _required_campaign_quests_completed(campaign: Campaign) -> bool:
    required_quest_ids = list(
        CampaignQuest.objects.filter(
            campaign=campaign,
            is_required=True,
        ).values_list("quest_id", flat=True)
    )
    if not required_quest_ids:
        return False
    completed_ids = _completed_quest_ids(required_quest_ids)
    return set(required_quest_ids).issubset(completed_ids)


def _campaign_xp_note(campaign: Campaign) -> str:
    return f"Campaign completed: {campaign.title}; campaign_id={campaign.id}"


def _try_create_campaign_activation_journal(campaign: Campaign) -> None:
    _try_create_campaign_journal(
        campaign=campaign,
        title=f"Campaign activated: {campaign.title}",
        content=campaign.description,
        source_type="campaign_activation",
    )


def _try_create_campaign_completion_journal(campaign: Campaign) -> None:
    _try_create_campaign_journal(
        campaign=campaign,
        title=f"Campaign completed: {campaign.title}",
        content=campaign.reward_title,
        source_type="campaign",
    )


def _try_create_campaign_ai_draft_journal(campaign: Campaign) -> None:
    _try_create_campaign_journal(
        campaign=campaign,
        title=f"AI campaign draft: {campaign.title}",
        content=campaign.description,
        source_type="campaign_ai_draft",
    )


def _try_create_campaign_journal(
    *,
    campaign: Campaign,
    title: str,
    content: str,
    source_type: str,
) -> None:
    try:
        JournalEntry.objects.get_or_create(
            source_type=source_type,
            source_id=campaign.id,
            defaults={
                "title": title,
                "content": content,
                "entry_type": JournalEntryType.CAMPAIGN,
                "entry_date": timezone.localdate(),
            },
        )
    except Exception:
        return


def _ai_draft_description(
    *,
    goal: str,
    timeframe_days: int | None,
    available_minutes_per_day: int | None,
    notes: str,
) -> str:
    parts = [f"AI-generated draft campaign for: {goal}"]
    if timeframe_days:
        parts.append(f"Timeframe: {timeframe_days} days.")
    if available_minutes_per_day:
        parts.append(f"Daily capacity: {available_minutes_per_day} minutes.")
    if notes.strip():
        parts.append(f"Context: {notes.strip()}")
    return " ".join(parts)


def _clean_or_raise(instance: Any) -> None:
    try:
        instance.full_clean()
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            messages: list[str] = []
            for field_messages in exc.message_dict.values():
                messages.extend(str(message) for message in field_messages)
            message = " ".join(messages)
        else:
            message = " ".join(str(message) for message in exc.messages)
        raise RpgValidationError(message) from exc
