export type CampaignStatus = "draft" | "active" | "completed" | "archived";
export type CampaignCreatedBy = "user" | "ai" | "system";
export type CampaignDifficulty = "easy" | "normal" | "hard" | "epic" | "legendary";
export type CampaignQuestState = "locked" | "available" | "completed";
export type CampaignQuestUnlockMode = "immediate" | "after_dependencies" | "manual";
export type CampaignNodeKind =
  | "start"
  | "quest"
  | "milestone"
  | "reward"
  | "reflection"
  | "gate"
  | "end";
export type CampaignStudioMode = "builder" | "play";

export interface CampaignRewardSkill {
  id: string;
  name: string;
}

export interface CampaignMapNode {
  id: string;
  questId: string;
  title: string;
  description: string;
  stage: string;
  state: CampaignQuestState;
  isRequired: boolean;
  unlockMode: CampaignQuestUnlockMode;
  x: number;
  y: number;
  rewardXp: number;
  targetValue: number;
  targetUnit: string;
  difficulty: string;
}

export interface CampaignStudioNode extends CampaignMapNode {
  nodeKind: CampaignNodeKind;
  position: {
    x: number;
    y: number;
  };
  config: Record<string, unknown>;
  unlockDescription?: string;
  blockedByIds?: string[];
}

export interface CampaignMapEdge {
  id: string;
  from: string;
  to: string;
}

export interface CampaignStudioEdge {
  id: string;
  sourceNodeId: string;
  targetNodeId: string;
}

export interface CampaignValidationCheck {
  code: string;
  label?: string;
  passed: boolean;
  message?: string;
}

export interface CampaignValidationIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  nodeId?: string;
  edgeId?: string;
}

export interface CampaignValidationReport {
  valid: boolean;
  checks: CampaignValidationCheck[];
  issues: CampaignValidationIssue[];
}

export interface CampaignStage {
  name: string;
  quests: Array<{
    id: string;
    questId: string;
    title: string;
    state: CampaignQuestState;
    isRequired: boolean;
    order: number;
  }>;
}

export interface Campaign {
  id: string;
  title: string;
  description: string;
  status: CampaignStatus;
  createdBy: CampaignCreatedBy;
  difficulty: CampaignDifficulty;
  progressPercent: number;
  completedRequiredQuests: number;
  totalRequiredQuests: number;
  availableQuests: number;
  lockedQuests: number;
  rewardXp: number;
  rewardTitle: string;
  rewardSkill: CampaignRewardSkill | null;
  startsOn: string | null;
  dueOn: string | null;
  completedAt: string | null;
  xpAwardedAt: string | null;
  aiProvider: string;
  aiModel: string;
  map: {
    nodes: CampaignMapNode[];
    edges: CampaignMapEdge[];
  };
  stages: CampaignStage[];
}

export interface CampaignSummary extends Omit<Campaign, "map" | "stages"> {
  map?: Campaign["map"];
  stages?: Campaign["stages"];
}

export interface CampaignsResponse {
  campaigns: CampaignSummary[];
}

export interface CampaignMutationResponse {
  campaign: Campaign;
  dashboardRefreshRequired: boolean;
}

export interface CampaignStudioResponse {
  campaign: Campaign;
  nodes: CampaignStudioNode[];
  edges: CampaignStudioEdge[];
  validation: CampaignValidationReport;
  availableNodeTypes: CampaignNodeKind[];
}

export interface CampaignStudioMutationResponse {
  campaign?: Campaign;
  node?: CampaignStudioNode;
  edge?: CampaignStudioEdge;
  studio?: CampaignStudioResponse;
  validation?: CampaignValidationReport;
  dashboardRefreshRequired: boolean;
}

export interface CampaignPayload {
  title: string;
  description?: string;
  difficulty?: CampaignDifficulty;
  rewardXp?: number;
  rewardSkillId?: string;
  rewardTitle?: string;
  dueOn?: string;
}

export interface CampaignQuestPayload {
  title: string;
  description?: string;
  stage?: string;
  order?: number;
  isRequired?: boolean;
  unlockMode?: CampaignQuestUnlockMode;
  mapX?: number;
  mapY?: number;
  rewardSkillId?: string;
  rewardXp?: number;
  dependsOnIds?: string[];
}

export interface CampaignNodePayload {
  nodeKind?: CampaignNodeKind;
  title: string;
  description?: string;
  stage?: string;
  isRequired?: boolean;
  unlockMode?: CampaignQuestUnlockMode;
  position?: {
    x: number;
    y: number;
  };
  targetValue?: number;
  targetUnit?: string;
  difficulty?: string;
  rewardSkillId?: string;
  rewardXp?: number;
  config?: Record<string, unknown>;
}

export interface CampaignNodeUpdatePayload
  extends Partial<Omit<CampaignNodePayload, "position">> {
  position?: {
    x: number;
    y: number;
  };
}

export interface CampaignNodePositionPayload {
  nodeId: string;
  x: number;
  y: number;
}

export interface CampaignEdgePayload {
  sourceNodeId: string;
  targetNodeId: string;
}

export interface AiCampaignDraftPayload {
  goal: string;
  timeframeDays?: number;
  availableMinutesPerDay?: number;
  difficulty?: CampaignDifficulty;
  skillIds?: string[];
  notes?: string;
}
