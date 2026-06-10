import type { XpEventResponse } from "./dashboard";

export interface LinkedSkill {
  id: string;
  name: string;
  weight: number;
}

export interface ProgressionGoal {
  id: string;
  title: string;
  description: string;
  status: "draft" | "active" | "paused" | "completed" | "archived";
  priority: "low" | "normal" | "high" | "legendary";
  progressValue: number;
  targetValue: number;
  targetUnit: string;
  progressPercent: number;
  startsOn: string | null;
  dueOn: string | null;
  linkedSkills: LinkedSkill[];
  completedAt: string | null;
  archivedAt: string | null;
}

export interface ProgressionChallenge {
  id: string;
  title: string;
  description: string;
  status: "draft" | "active" | "completed" | "failed" | "archived";
  startDate: string;
  endDate: string;
  day: number;
  totalDays: number;
  currentValue: number;
  targetValue: number;
  targetUnit: string;
  progressPercent: number;
  rewardTitle: string;
  rewardXp: number;
  rewardSkills: Array<{ id: string; name: string; xpAmount: number }>;
  completedAt: string | null;
  failedAt: string | null;
  xpAwardedAt: string | null;
}

export interface AchievementUnlock {
  id: string;
  achievementId: string;
  title: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  unlockedAt: string;
  sourceType: string;
  sourceId: string | null;
  note: string;
}

export interface ProgressionAchievement {
  id: string;
  title: string;
  description: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  isActive: boolean;
  unlocked: boolean;
  unlock: AchievementUnlock | null;
  progress: {
    current: number;
    target: number;
    unit: string;
    progressPercent: number;
  };
}

export interface GoalsResponse {
  goals: ProgressionGoal[];
}

export interface ChallengesResponse {
  challenges: ProgressionChallenge[];
}

export interface AchievementsResponse {
  achievements: ProgressionAchievement[];
}

export interface GoalPayload {
  title: string;
  description?: string;
  status?: ProgressionGoal["status"];
  priority?: ProgressionGoal["priority"];
  targetValue?: number;
  targetUnit?: string;
  startsOn?: string;
  dueOn?: string;
  skillIds?: string[];
}

export type GoalUpdatePayload = Partial<GoalPayload>;

export interface GoalMutationResponse {
  goal: ProgressionGoal;
  dashboardRefreshRequired: boolean;
}

export interface GoalProgressResponse extends GoalMutationResponse {
  progressEntry: {
    id: string;
    previousValue: number;
    newValue: number;
    delta: number;
  };
}

export interface ChallengeCheckIn {
  id: string;
  checkedOn: string;
  value: number;
  successful: boolean;
}

export interface ChallengeMutationResponse {
  challenge: ProgressionChallenge;
  checkIn?: ChallengeCheckIn | null;
  checked?: boolean;
  completionReady?: boolean;
  xpEvents: XpEventResponse[];
  achievementUnlocks: AchievementUnlock[];
  dashboardRefreshRequired: boolean;
}

export interface ChallengeRewardPayload {
  skillId: string;
  xpAmount: number;
}

export interface ChallengePayload {
  title: string;
  description?: string;
  status?: ProgressionChallenge["status"];
  targetValue?: number;
  targetUnit?: string;
  startDate: string;
  endDate: string;
  rewardTitle?: string;
  goalId?: string;
  rewards?: ChallengeRewardPayload[];
}

export type ChallengeUpdatePayload = Partial<ChallengePayload>;

export interface AchievementUnlockResponse {
  unlock: AchievementUnlock;
  dashboardRefreshRequired: boolean;
}

export interface AchievementEvaluationResponse {
  achievementUnlocks: AchievementUnlock[];
  dashboardRefreshRequired: boolean;
}
