import type {
  AchievementEvaluationResponse,
  AchievementUnlock,
  AchievementUnlockResponse,
  AchievementsResponse,
  ChallengePayload,
  ChallengeCheckIn,
  ChallengeMutationResponse,
  ChallengeUpdatePayload,
  ChallengesResponse,
  GoalMutationResponse,
  GoalPayload,
  GoalProgressResponse,
  GoalUpdatePayload,
  GoalsResponse,
  ProgressionAchievement,
  ProgressionChallenge,
  ProgressionGoal
} from "../types/progression";
import type { XpEventResponse } from "../types/dashboard";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type RawGoal = {
  id: number;
  title: string;
  description: string;
  status: ProgressionGoal["status"];
  priority: ProgressionGoal["priority"];
  progress_value: number;
  target_value: number;
  target_unit: string;
  progress_percent: number;
  starts_on: string | null;
  due_on: string | null;
  linked_skills: Array<{ id: number; name: string; weight: number }>;
  completed_at: string | null;
  archived_at: string | null;
};

type RawChallenge = {
  id: number;
  title?: string;
  name?: string;
  description: string;
  status: ProgressionChallenge["status"];
  start_date: string;
  end_date: string;
  day: number;
  total_days?: number;
  total?: number;
  current_value: number;
  target_value: number;
  target_unit: string;
  progress_percent?: number;
  progress?: number;
  reward_title: string;
  reward_xp: number;
  reward_skills: Array<{ id: number; name: string; xp_amount: number }>;
  completed_at: string | null;
  failed_at: string | null;
  xp_awarded_at: string | null;
};

type RawAchievementUnlock = {
  id: number;
  achievement_id: number;
  title: string;
  rarity: AchievementUnlock["rarity"];
  unlocked_at: string;
  source_type: string;
  source_id: number | null;
  note: string;
};

type RawAchievement = {
  id: number;
  title: string;
  description: string;
  rarity: ProgressionAchievement["rarity"];
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  is_active: boolean;
  unlocked: boolean;
  unlock: RawAchievementUnlock | null;
  progress: {
    current: number;
    target: number;
    unit: string;
    progress_percent: number;
  };
};

type RawXpEvent = {
  id: number;
  skill: { id: number; name: string };
  amount: number;
  source_type: string;
  note: string;
  earned_at: string;
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
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<TResponse>;
}

function csrfHeaders() {
  return { "X-CSRFToken": getCookie("csrftoken") };
}

function transformGoal(raw: RawGoal): ProgressionGoal {
  return {
    id: String(raw.id),
    title: raw.title,
    description: raw.description,
    status: raw.status,
    priority: raw.priority,
    progressValue: raw.progress_value,
    targetValue: raw.target_value,
    targetUnit: raw.target_unit,
    progressPercent: raw.progress_percent,
    startsOn: raw.starts_on,
    dueOn: raw.due_on,
    linkedSkills: raw.linked_skills.map((skill) => ({
      id: String(skill.id),
      name: skill.name,
      weight: skill.weight
    })),
    completedAt: raw.completed_at,
    archivedAt: raw.archived_at
  };
}

function transformChallenge(raw: RawChallenge): ProgressionChallenge {
  return {
    id: String(raw.id),
    title: raw.title ?? raw.name ?? "Challenge",
    description: raw.description,
    status: raw.status,
    startDate: raw.start_date,
    endDate: raw.end_date,
    day: raw.day,
    totalDays: raw.total_days ?? raw.total ?? 1,
    currentValue: raw.current_value,
    targetValue: raw.target_value,
    targetUnit: raw.target_unit,
    progressPercent: raw.progress_percent ?? raw.progress ?? 0,
    rewardTitle: raw.reward_title,
    rewardXp: raw.reward_xp,
    rewardSkills: raw.reward_skills.map((skill) => ({
      id: String(skill.id),
      name: skill.name,
      xpAmount: skill.xp_amount
    })),
    completedAt: raw.completed_at,
    failedAt: raw.failed_at,
    xpAwardedAt: raw.xp_awarded_at
  };
}

function transformUnlock(raw: RawAchievementUnlock): AchievementUnlock {
  return {
    id: String(raw.id),
    achievementId: String(raw.achievement_id),
    title: raw.title,
    rarity: raw.rarity,
    unlockedAt: raw.unlocked_at,
    sourceType: raw.source_type,
    sourceId: raw.source_id === null ? null : String(raw.source_id),
    note: raw.note
  };
}

function transformAchievement(raw: RawAchievement): ProgressionAchievement {
  return {
    id: String(raw.id),
    title: raw.title,
    description: raw.description,
    rarity: raw.rarity,
    triggerType: raw.trigger_type,
    triggerConfig: raw.trigger_config,
    isActive: raw.is_active,
    unlocked: raw.unlocked,
    unlock: raw.unlock ? transformUnlock(raw.unlock) : null,
    progress: {
      current: raw.progress.current,
      target: raw.progress.target,
      unit: raw.progress.unit,
      progressPercent: raw.progress.progress_percent
    }
  };
}

function transformXpEvent(raw: RawXpEvent): XpEventResponse {
  return {
    id: String(raw.id),
    skill: { id: String(raw.skill.id), name: raw.skill.name },
    amount: raw.amount,
    sourceType: raw.source_type,
    note: raw.note,
    earnedAt: raw.earned_at
  };
}

function goalPayload(payload: GoalPayload | GoalUpdatePayload) {
  return {
    title: payload.title,
    description: payload.description,
    status: payload.status,
    priority: payload.priority,
    target_value: payload.targetValue,
    target_unit: payload.targetUnit,
    starts_on: payload.startsOn,
    due_on: payload.dueOn,
    skill_ids: payload.skillIds?.map((id) => Number(id))
  };
}

function challengePayload(payload: ChallengePayload | ChallengeUpdatePayload) {
  return {
    title: payload.title,
    description: payload.description,
    status: payload.status,
    target_value: payload.targetValue,
    target_unit: payload.targetUnit,
    start_date: payload.startDate,
    end_date: payload.endDate,
    reward_title: payload.rewardTitle,
    goal_id: payload.goalId ? Number(payload.goalId) : undefined,
    rewards: payload.rewards?.map((reward) => ({
      skill_id: Number(reward.skillId),
      xp_amount: reward.xpAmount
    }))
  };
}

export async function fetchGoals(status = "all"): Promise<GoalsResponse> {
  const raw = await requestJson<{ goals: RawGoal[] }>(`/api/goals/?status=${status}`);
  return { goals: raw.goals.map(transformGoal) };
}

export async function createGoal(payload: GoalPayload): Promise<GoalMutationResponse> {
  const raw = await requestJson<{ goal: RawGoal; dashboard_refresh_required: boolean }>(
    "/api/goals/",
    {
      method: "POST",
      headers: csrfHeaders(),
      body: JSON.stringify(goalPayload(payload))
    }
  );
  return {
    goal: transformGoal(raw.goal),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function updateGoal(
  goalId: string,
  payload: GoalUpdatePayload
): Promise<GoalMutationResponse> {
  const raw = await requestJson<{ goal: RawGoal; dashboard_refresh_required: boolean }>(
    `/api/goals/${goalId}/`,
    {
      method: "PATCH",
      headers: csrfHeaders(),
      body: JSON.stringify(goalPayload(payload))
    }
  );
  return {
    goal: transformGoal(raw.goal),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function updateGoalProgress(
  goalId: string,
  progressValue: number
): Promise<GoalProgressResponse> {
  const raw = await requestJson<{
    goal: RawGoal;
    progress_entry: {
      id: number;
      previous_value: number;
      new_value: number;
      delta: number;
    };
    dashboard_refresh_required: boolean;
  }>(`/api/goals/${goalId}/progress/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({ progress_value: progressValue })
  });
  return {
    goal: transformGoal(raw.goal),
    progressEntry: {
      id: String(raw.progress_entry.id),
      previousValue: raw.progress_entry.previous_value,
      newValue: raw.progress_entry.new_value,
      delta: raw.progress_entry.delta
    },
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function completeGoal(goalId: string): Promise<GoalMutationResponse> {
  const raw = await requestJson<{ goal: RawGoal; dashboard_refresh_required: boolean }>(
    `/api/goals/${goalId}/complete/`,
    { method: "POST", headers: csrfHeaders(), body: JSON.stringify({}) }
  );
  return {
    goal: transformGoal(raw.goal),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function archiveGoal(goalId: string): Promise<GoalMutationResponse> {
  const raw = await requestJson<{ goal: RawGoal; dashboard_refresh_required: boolean }>(
    `/api/goals/${goalId}/archive/`,
    { method: "POST", headers: csrfHeaders(), body: JSON.stringify({}) }
  );
  return {
    goal: transformGoal(raw.goal),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function fetchChallenges(status = "all"): Promise<ChallengesResponse> {
  const raw = await requestJson<{ challenges: RawChallenge[] }>(
    `/api/challenges/?status=${status}`
  );
  return { challenges: raw.challenges.map(transformChallenge) };
}

export async function createChallenge(
  payload: ChallengePayload
): Promise<ChallengeMutationResponse> {
  const raw = await requestJson<{
    challenge: RawChallenge;
    dashboard_refresh_required: boolean;
  }>("/api/challenges/", {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify(challengePayload(payload))
  });
  return {
    challenge: transformChallenge(raw.challenge),
    xpEvents: [],
    achievementUnlocks: [],
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function updateChallenge(
  challengeId: string,
  payload: ChallengeUpdatePayload
): Promise<ChallengeMutationResponse> {
  const raw = await requestJson<{
    challenge: RawChallenge;
    dashboard_refresh_required: boolean;
  }>(`/api/challenges/${challengeId}/`, {
    method: "PATCH",
    headers: csrfHeaders(),
    body: JSON.stringify(challengePayload(payload))
  });
  return {
    challenge: transformChallenge(raw.challenge),
    xpEvents: [],
    achievementUnlocks: [],
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function toggleChallengeCheckIn(
  challengeId: string
): Promise<ChallengeMutationResponse> {
  const raw = await requestJson<{
    challenge: RawChallenge;
    check_in: {
      id: number;
      checked_on: string;
      value: number;
      successful: boolean;
    } | null;
    checked: boolean;
    completion_ready: boolean;
    xp_events: RawXpEvent[];
    achievement_unlocks: RawAchievementUnlock[];
    dashboard_refresh_required: boolean;
  }>(`/api/challenges/${challengeId}/toggle/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  const checkIn: ChallengeCheckIn | null = raw.check_in
    ? {
        id: String(raw.check_in.id),
        checkedOn: raw.check_in.checked_on,
        value: raw.check_in.value,
        successful: raw.check_in.successful
      }
    : null;
  return {
    challenge: transformChallenge(raw.challenge),
    checkIn,
    checked: raw.checked,
    completionReady: raw.completion_ready,
    xpEvents: raw.xp_events.map(transformXpEvent),
    achievementUnlocks: raw.achievement_unlocks.map(transformUnlock),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function completeChallenge(
  challengeId: string
): Promise<ChallengeMutationResponse> {
  const raw = await requestJson<{
    challenge: RawChallenge;
    xp_events: RawXpEvent[];
    achievement_unlocks: RawAchievementUnlock[];
    dashboard_refresh_required: boolean;
  }>(`/api/challenges/${challengeId}/complete/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  return {
    challenge: transformChallenge(raw.challenge),
    xpEvents: raw.xp_events.map(transformXpEvent),
    achievementUnlocks: raw.achievement_unlocks.map(transformUnlock),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function failChallenge(
  challengeId: string,
  note = ""
): Promise<ChallengeMutationResponse> {
  const raw = await requestJson<{
    challenge: RawChallenge;
    xp_events: RawXpEvent[];
    achievement_unlocks: RawAchievementUnlock[];
    dashboard_refresh_required: boolean;
  }>(`/api/challenges/${challengeId}/fail/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify(note ? { note } : {})
  });
  return {
    challenge: transformChallenge(raw.challenge),
    xpEvents: raw.xp_events.map(transformXpEvent),
    achievementUnlocks: raw.achievement_unlocks.map(transformUnlock),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function fetchAchievements(status = "all"): Promise<AchievementsResponse> {
  const raw = await requestJson<{ achievements: RawAchievement[] }>(
    `/api/achievements/?status=${status}`
  );
  return { achievements: raw.achievements.map(transformAchievement) };
}

export async function unlockAchievement(
  achievementId: string
): Promise<AchievementUnlockResponse> {
  const raw = await requestJson<{
    unlock: RawAchievementUnlock;
    dashboard_refresh_required: boolean;
  }>(`/api/achievements/${achievementId}/unlock/`, {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  return {
    unlock: transformUnlock(raw.unlock),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

export async function evaluateAchievements(): Promise<AchievementEvaluationResponse> {
  const raw = await requestJson<{
    achievement_unlocks: RawAchievementUnlock[];
    dashboard_refresh_required: boolean;
  }>("/api/achievements/evaluate/", {
    method: "POST",
    headers: csrfHeaders(),
    body: JSON.stringify({})
  });
  return {
    achievementUnlocks: raw.achievement_unlocks.map(transformUnlock),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}
