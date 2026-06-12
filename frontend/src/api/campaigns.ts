import type {
  AiCampaignDraftPayload,
  Campaign,
  CampaignEdgePayload,
  CampaignMapEdge,
  CampaignMapNode,
  CampaignMutationResponse,
  CampaignNodeKind,
  CampaignNodePayload,
  CampaignNodePositionPayload,
  CampaignNodeUpdatePayload,
  CampaignPayload,
  CampaignQuestPayload,
  CampaignStudioEdge,
  CampaignStudioMutationResponse,
  CampaignStudioNode,
  CampaignStudioResponse,
  CampaignValidationReport,
  CampaignsResponse,
  CampaignStage,
  CampaignSummary
} from "../types/campaigns";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type RawCampaign = {
  id: number;
  title: string;
  description: string;
  status: Campaign["status"];
  created_by: Campaign["createdBy"];
  difficulty: Campaign["difficulty"];
  progress_percent: number;
  completed_required_quests: number;
  total_required_quests: number;
  available_quests: number;
  locked_quests: number;
  reward_xp: number;
  reward_title: string;
  reward_skill: { id: number; name: string } | null;
  starts_on: string | null;
  due_on: string | null;
  completed_at: string | null;
  xp_awarded_at: string | null;
  ai_provider: string;
  ai_model: string;
  map?: {
    nodes: RawCampaignMapNode[];
    edges: RawCampaignMapEdge[];
  };
  stages?: RawCampaignStage[];
};

type RawCampaignMapNode = {
  id: number;
  quest_id?: number | null;
  node_type?: CampaignNodeKind;
  node_kind?: CampaignNodeKind;
  title: string;
  description: string;
  stage: string;
  state: CampaignMapNode["state"];
  is_required: boolean;
  unlock_mode: CampaignMapNode["unlockMode"];
  map_x: number;
  map_y: number;
  reward_xp: number;
  target_value: number;
  target_unit: string;
  difficulty: string;
  position?: {
    x: number;
    y: number;
  };
  config?: Record<string, unknown>;
  unlock_description?: string;
  blocked_by_ids?: number[];
};

type RawCampaignMapEdge = {
  id: number;
  from?: number;
  to?: number;
  source_node_id?: number;
  target_node_id?: number;
};

type RawCampaignStage = {
  name: string;
  quests: Array<{
    id: number;
    quest_id: number;
    title: string;
    state: CampaignMapNode["state"];
    is_required: boolean;
    order: number;
  }>;
};

type RawCampaignValidationReport = {
  valid: boolean;
  checks?: Array<{
    code: string;
    label?: string;
    passed: boolean;
    message?: string;
  }>;
  issues?: Array<{
    code: string;
    severity: "info" | "warning" | "error";
    message: string;
    node_id?: number | null;
    edge_id?: number | null;
  }>;
};

type RawAvailableNodeType =
  | CampaignNodeKind
  | {
      value: CampaignNodeKind;
      label?: string;
    };

type RawCampaignStudioResponse = {
  campaign: RawCampaign;
  nodes?: RawCampaignMapNode[];
  edges?: RawCampaignMapEdge[];
  validation?: RawCampaignValidationReport;
  available_node_types?: RawAvailableNodeType[];
};

type RawCampaignValidationResponse =
  | RawCampaignValidationReport
  | {
      validation?: RawCampaignValidationReport;
    };

type RawCampaignStudioMutationResponse = {
  campaign?: RawCampaign;
  node?: RawCampaignMapNode;
  edge?: RawCampaignMapEdge;
  studio?: RawCampaignStudioResponse;
  validation?: RawCampaignValidationReport;
  dashboard_refresh_required?: boolean;
};

function getCookie(name: string): string {
  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1] ?? "") : "";
}

async function requestJson<TResponse>(
  path: string,
  init: RequestInit = {}
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers
    },
    ...init
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      message = payload.error?.message ?? message;
    } catch {
      // Keep the generic response message when the body is not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return response.json() as Promise<TResponse>;
}

function csrfHeaders() {
  return { "X-CSRFToken": getCookie("csrftoken") };
}

function transformMapNode(raw: RawCampaignMapNode): CampaignMapNode {
  const x = raw.position?.x ?? raw.map_x;
  const y = raw.position?.y ?? raw.map_y;

  return {
    id: String(raw.id),
    questId: raw.quest_id ? String(raw.quest_id) : "",
    title: raw.title,
    description: raw.description,
    stage: raw.stage,
    state: raw.state,
    isRequired: raw.is_required,
    unlockMode: raw.unlock_mode,
    x,
    y,
    rewardXp: raw.reward_xp,
    targetValue: raw.target_value,
    targetUnit: raw.target_unit,
    difficulty: raw.difficulty
  };
}

function transformMapEdge(raw: RawCampaignMapEdge): CampaignMapEdge {
  const from = raw.from ?? raw.source_node_id ?? 0;
  const to = raw.to ?? raw.target_node_id ?? 0;

  return {
    id: String(raw.id),
    from: String(from),
    to: String(to)
  };
}

function transformStudioNode(raw: RawCampaignMapNode): CampaignStudioNode {
  const baseNode = transformMapNode(raw);

  return {
    ...baseNode,
    nodeKind: raw.node_kind ?? raw.node_type ?? "quest",
    position: {
      x: baseNode.x,
      y: baseNode.y
    },
    config: raw.config ?? {},
    unlockDescription: raw.unlock_description,
    blockedByIds: raw.blocked_by_ids?.map(String) ?? []
  };
}

function transformStudioEdge(raw: RawCampaignMapEdge): CampaignStudioEdge {
  const edge = transformMapEdge(raw);

  return {
    id: edge.id,
    sourceNodeId: edge.from,
    targetNodeId: edge.to
  };
}

function transformValidationReport(
  raw: RawCampaignValidationReport | undefined
): CampaignValidationReport {
  return {
    valid: raw?.valid ?? true,
    checks:
      raw?.checks?.map((check) => ({
        code: check.code,
        label: check.label,
        passed: check.passed,
        message: check.message
      })) ?? [],
    issues:
      raw?.issues?.map((issue) => ({
        code: issue.code,
        severity: issue.severity,
        message: issue.message,
        nodeId: issue.node_id ? String(issue.node_id) : undefined,
        edgeId: issue.edge_id ? String(issue.edge_id) : undefined
      })) ?? []
  };
}

function transformStage(raw: RawCampaignStage): CampaignStage {
  return {
    name: raw.name,
    quests: raw.quests.map((quest) => ({
      id: String(quest.id),
      questId: String(quest.quest_id),
      title: quest.title,
      state: quest.state,
      isRequired: quest.is_required,
      order: quest.order
    }))
  };
}

function transformCampaign(raw: RawCampaign): Campaign {
  return {
    id: String(raw.id),
    title: raw.title,
    description: raw.description,
    status: raw.status,
    createdBy: raw.created_by,
    difficulty: raw.difficulty,
    progressPercent: raw.progress_percent,
    completedRequiredQuests: raw.completed_required_quests,
    totalRequiredQuests: raw.total_required_quests,
    availableQuests: raw.available_quests,
    lockedQuests: raw.locked_quests,
    rewardXp: raw.reward_xp,
    rewardTitle: raw.reward_title,
    rewardSkill: raw.reward_skill
      ? { id: String(raw.reward_skill.id), name: raw.reward_skill.name }
      : null,
    startsOn: raw.starts_on,
    dueOn: raw.due_on,
    completedAt: raw.completed_at,
    xpAwardedAt: raw.xp_awarded_at,
    aiProvider: raw.ai_provider,
    aiModel: raw.ai_model,
    map: {
      nodes: raw.map?.nodes.map(transformMapNode) ?? [],
      edges: raw.map?.edges.map(transformMapEdge) ?? []
    },
    stages: raw.stages?.map(transformStage) ?? []
  };
}

function campaignPayload(payload: CampaignPayload) {
  return {
    title: payload.title,
    description: payload.description,
    difficulty: payload.difficulty,
    reward_xp: payload.rewardXp,
    reward_skill_id: payload.rewardSkillId ? Number(payload.rewardSkillId) : undefined,
    reward_title: payload.rewardTitle,
    due_on: payload.dueOn || undefined
  };
}

function campaignQuestPayload(payload: CampaignQuestPayload) {
  return {
    title: payload.title,
    description: payload.description,
    stage: payload.stage,
    order: payload.order,
    is_required: payload.isRequired,
    unlock_mode: payload.unlockMode,
    map_x: payload.mapX,
    map_y: payload.mapY,
    reward_skill_id: payload.rewardSkillId ? Number(payload.rewardSkillId) : undefined,
    reward_xp: payload.rewardXp,
    depends_on_ids: payload.dependsOnIds?.map((id) => Number(id))
  };
}

function campaignNodePayload(payload: CampaignNodePayload | CampaignNodeUpdatePayload) {
  return {
    node_kind: payload.nodeKind,
    node_type: payload.nodeKind,
    title: payload.title,
    description: payload.description,
    stage: payload.stage,
    order: undefined,
    is_required: payload.isRequired,
    unlock_mode: payload.unlockMode,
    position: payload.position,
    map_x: payload.position ? Math.round(payload.position.x) : undefined,
    map_y: payload.position ? Math.round(payload.position.y) : undefined,
    target_value: payload.targetValue,
    target_unit: payload.targetUnit,
    difficulty: payload.difficulty,
    reward_skill_id: payload.rewardSkillId ? Number(payload.rewardSkillId) : undefined,
    reward_xp: payload.rewardXp,
    config: payload.config
  };
}

function transformStudio(raw: RawCampaignStudioResponse): CampaignStudioResponse {
  const campaign = transformCampaign(raw.campaign);
  const rawNodes = raw.nodes ?? raw.campaign.map?.nodes ?? [];
  const rawEdges = raw.edges ?? raw.campaign.map?.edges ?? [];

  return {
    campaign,
    nodes: rawNodes.map(transformStudioNode),
    edges: rawEdges.map(transformStudioEdge),
    validation: transformValidationReport(raw.validation),
    availableNodeTypes: transformAvailableNodeTypes(raw.available_node_types)
  };
}

function transformAvailableNodeTypes(
  rawTypes: RawAvailableNodeType[] | undefined
): CampaignNodeKind[] {
  const fallback: CampaignNodeKind[] = [
    "quest",
    "milestone",
    "reward",
    "reflection",
    "gate"
  ];

  if (!rawTypes?.length) {
    return fallback;
  }

  return rawTypes
    .map((nodeType) => (typeof nodeType === "string" ? nodeType : nodeType.value))
    .filter((nodeType): nodeType is CampaignNodeKind => Boolean(nodeType));
}

function transformStudioMutation(
  raw: RawCampaignStudioMutationResponse
): CampaignStudioMutationResponse {
  return {
    campaign: raw.campaign ? transformCampaign(raw.campaign) : undefined,
    node: raw.node ? transformStudioNode(raw.node) : undefined,
    edge: raw.edge ? transformStudioEdge(raw.edge) : undefined,
    studio: raw.studio ? transformStudio(raw.studio) : undefined,
    validation: raw.validation ? transformValidationReport(raw.validation) : undefined,
    dashboardRefreshRequired: raw.dashboard_refresh_required ?? false
  };
}

export async function fetchCampaigns(status = "all"): Promise<CampaignsResponse> {
  const raw = await requestJson<{ campaigns: RawCampaign[] }>(
    `/api/campaigns/?status=${status}`
  );
  return { campaigns: raw.campaigns.map(transformCampaign) as CampaignSummary[] };
}

export async function fetchCampaign(campaignId: string): Promise<Campaign> {
  const raw = await requestJson<{ campaign: RawCampaign }>(
    `/api/campaigns/${campaignId}/`
  );
  return transformCampaign(raw.campaign);
}

export async function fetchCampaignStudio(
  campaignId: string
): Promise<CampaignStudioResponse> {
  const raw = await requestJson<RawCampaignStudioResponse>(
    `/api/campaigns/${campaignId}/studio/`
  );
  return transformStudio(raw);
}

export async function createCampaign(
  payload: CampaignPayload
): Promise<CampaignMutationResponse> {
  const raw = await requestJson<{
    campaign: RawCampaign;
    dashboard_refresh_required: boolean;
  }>("/api/campaigns/", {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify(campaignPayload(payload))
  });
  return {
    campaign: transformCampaign(raw.campaign),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function activateCampaign(
  campaignId: string
): Promise<CampaignMutationResponse> {
  const raw = await requestJson<{
    campaign: RawCampaign;
    dashboard_refresh_required: boolean;
  }>(`/api/campaigns/${campaignId}/activate/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  return {
    campaign: transformCampaign(raw.campaign),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function archiveCampaign(
  campaignId: string
): Promise<CampaignMutationResponse> {
  const raw = await requestJson<{
    campaign: RawCampaign;
    dashboard_refresh_required: boolean;
  }>(`/api/campaigns/${campaignId}/archive/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  return {
    campaign: transformCampaign(raw.campaign),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function addCampaignQuest(
  campaignId: string,
  payload: CampaignQuestPayload
): Promise<CampaignMutationResponse> {
  const raw = await requestJson<{
    campaign: RawCampaign;
    dashboard_refresh_required: boolean;
  }>(`/api/campaigns/${campaignId}/quests/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify(campaignQuestPayload(payload))
  });
  return {
    campaign: transformCampaign(raw.campaign),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function createCampaignNode(
  campaignId: string,
  payload: CampaignNodePayload
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/nodes/`,
    {
      method: "POST",
      headers: csrfHeaders(),
      body: JSON.stringify(campaignNodePayload(payload))
    }
  );
  return transformStudioMutation(raw);
}

export async function updateCampaignNode(
  campaignId: string,
  nodeId: string,
  payload: CampaignNodeUpdatePayload
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/nodes/${nodeId}/`,
    {
      method: "PATCH",
      headers: csrfHeaders(),
      body: JSON.stringify(campaignNodePayload(payload))
    }
  );
  return transformStudioMutation(raw);
}

export async function deleteCampaignNode(
  campaignId: string,
  nodeId: string
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/nodes/${nodeId}/`,
    {
      method: "DELETE",
      headers: csrfHeaders()
    }
  );
  return transformStudioMutation(raw ?? {});
}

export async function updateCampaignNodePositions(
  campaignId: string,
  positions: CampaignNodePositionPayload[]
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/nodes/positions/`,
    {
      method: "PATCH",
      headers: csrfHeaders(),
      body: JSON.stringify({
        positions: positions.map((position) => ({
          node_id: Number(position.nodeId),
          x: Math.round(position.x),
          y: Math.round(position.y),
          position: {
            x: Math.round(position.x),
            y: Math.round(position.y)
          },
          map_x: Math.round(position.x),
          map_y: Math.round(position.y)
        }))
      })
    }
  );
  return transformStudioMutation(raw);
}

export async function createCampaignEdge(
  campaignId: string,
  payload: CampaignEdgePayload
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/edges/`,
    {
      method: "POST",
      headers: csrfHeaders(),
      body: JSON.stringify({
        source_node_id: Number(payload.sourceNodeId),
        target_node_id: Number(payload.targetNodeId)
      })
    }
  );
  return transformStudioMutation(raw);
}

export async function deleteCampaignEdge(
  campaignId: string,
  edgeId: string
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/edges/${edgeId}/`,
    {
      method: "DELETE",
      headers: csrfHeaders()
    }
  );
  return transformStudioMutation(raw ?? {});
}

export async function replaceCampaignEdges(
  campaignId: string,
  edges: CampaignEdgePayload[]
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/edges/`,
    {
      method: "PUT",
      headers: csrfHeaders(),
      body: JSON.stringify({
        edges: edges.map((edge) => ({
          source_node_id: Number(edge.sourceNodeId),
          target_node_id: Number(edge.targetNodeId)
        }))
      })
    }
  );
  return transformStudioMutation(raw);
}

export async function validateCampaign(
  campaignId: string
): Promise<CampaignValidationReport> {
  const raw = await requestJson<RawCampaignValidationResponse>(
    `/api/campaigns/${campaignId}/validate/`
  );
  return transformValidationReport("valid" in raw ? raw : raw.validation);
}

export async function publishCampaign(
  campaignId: string
): Promise<CampaignStudioMutationResponse> {
  const raw = await requestJson<RawCampaignStudioMutationResponse>(
    `/api/campaigns/${campaignId}/publish/`,
    {
      method: "POST",
      headers: csrfHeaders(),
      body: JSON.stringify({})
    }
  );
  return transformStudioMutation(raw);
}

export async function generateAiCampaignDraft(
  payload: AiCampaignDraftPayload
): Promise<CampaignMutationResponse> {
  const raw = await requestJson<{
    campaign: RawCampaign;
    dashboard_refresh_required: boolean;
  }>("/api/campaigns/ai-drafts/", {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({
      goal: payload.goal,
      timeframe_days: payload.timeframeDays,
      available_minutes_per_day: payload.availableMinutesPerDay,
      difficulty: payload.difficulty,
      skill_ids: payload.skillIds?.map((id) => Number(id)),
      notes: payload.notes
    })
  });
  return {
    campaign: transformCampaign(raw.campaign),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}
