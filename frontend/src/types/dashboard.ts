export type RankName =
  | "Bronze"
  | "Silver"
  | "Gold"
  | "Platinum"
  | "Diamond"
  | "Legendary";

export interface DashboardHero {
  name: string;
  title: string;
  level: number;
  rank: RankName;
  totalXp: number;
  currentLevelXp: number;
  nextLevelXp: number;
  progressPercent: number;
}

export interface ResourceCard {
  id: string;
  name: string;
  value: number;
  maxValue: number;
  progressPercent: number;
}

export interface AttributeRow {
  id: string;
  name: string;
  description: string;
  value: number;
  progressPercent: number;
  growth: number;
}

export interface QuestReward {
  xp: number;
  skillIds: string[];
}

export interface QuestRewardSkill {
  id: string;
  name: string;
  xp: number;
}

export interface DailyQuest {
  id: string;
  completionId?: string | null;
  title: string;
  description?: string;
  questType?: string;
  difficulty?: string;
  progressValue: number;
  targetValue: number;
  progressPercent: number;
  unit: string;
  completed: boolean;
  completedAt?: string | null;
  reward: QuestReward;
  rewardSkills: QuestRewardSkill[];
}

export interface HabitCheckIn {
  id: string;
  checkedOn: string;
  value: number;
}

export interface HabitMilestonePreview {
  id: string;
  title: string;
  streakDays: number;
  remainingDays: number;
  rewardXp: number;
}

export interface Habit {
  id: string;
  name: string;
  description?: string;
  frequency?: string;
  targetValue?: number;
  targetUnit?: string;
  checked: boolean;
  completedToday: boolean;
  checkInId?: string | null;
  checkIn?: HabitCheckIn | null;
  streakDays: number;
  nextMilestone?: HabitMilestonePreview | null;
}

export interface HabitsSummary {
  completed: number;
  total: number;
  streakDays: number;
}

export interface SkillRow {
  id: string;
  name: string;
  level: number;
  xp: number;
  progressPercent: number;
}

export interface StatusRow {
  id: string;
  name: string;
  value: number;
  maxValue: number;
  progressPercent: number;
}

export interface WeeklyProgressPoint {
  label: string;
  xp: number;
  minutes: number;
}

export interface WeeklyProgress {
  xp: number;
  quests: number;
  levels: number;
  points: WeeklyProgressPoint[];
}

export interface Achievement {
  id: string;
  title: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  unlockedAtLabel: string;
}

export interface JournalEntry {
  id: string;
  title: string;
  content: string;
  excerpt: string;
  entryType: string;
  mood: string;
  entryDate: string;
  createdAt: string;
  createdAtLabel: string;
}

export interface ActiveChallenge {
  id: string;
  title: string;
  status?: string;
  day: number;
  totalDays: number;
  currentValue?: number;
  targetValue?: number;
  targetUnit?: string;
  progressPercent: number;
  rewardLabel: string;
  rewardXp?: number;
}

export interface ActivityDefinitionOption {
  id: string;
  name: string;
  defaultMinutes: number;
}

export type DashboardRange = "today" | "week" | "month" | "custom";

export interface DashboardRangeQuery {
  range: DashboardRange;
  start?: string;
  end?: string;
}

export interface DashboardResponse {
  hero: DashboardHero;
  resources: ResourceCard[];
  attributes: AttributeRow[];
  dailyQuests: DailyQuest[];
  habits: Habit[];
  habitsSummary: HabitsSummary;
  activeChallenge: ActiveChallenge | null;
  skills: SkillRow[];
  statuses: StatusRow[];
  weeklyProgress: WeeklyProgress;
  achievements: Achievement[];
  journalEntries: JournalEntry[];
  activityDefinitions: ActivityDefinitionOption[];
}

export interface ManualActivityPayload {
  activityDefinitionId: string;
  minutes: number;
  startedAt?: string;
  source?: string;
}

export interface ActivityEntry {
  id: string;
  activityDefinitionId: string;
  minutes: number;
  xp: number;
  startedAt: string;
}

export interface JournalEntryPayload {
  title: string;
  content?: string;
  mood?: string;
  entryDate?: string;
}

export interface JournalEntryMutationResponse {
  entry: JournalEntry;
}

export interface QuestCompletePayload {
  completedOn?: string;
  note?: string;
}

export interface QuestProgressPayload {
  progressValue: number;
  completedOn?: string;
  note?: string;
}

export interface XpEventResponse {
  id: string;
  skill: {
    id: string;
    name: string;
  };
  amount: number;
  sourceType: string;
  note: string;
  earnedAt: string;
}

export interface QuestMutationResponse {
  quest: {
    id: string;
    title: string;
    completed: boolean;
    progressValue: number;
    targetValue: number;
    targetUnit: string;
    progressPercent: number;
    completionId: string;
    rewardXp: number;
    rewardSkills: QuestRewardSkill[];
  };
  completion: {
    id: string;
    completedOn: string;
    progressValue: number;
    completedAt: string | null;
    xpAwardedAt: string | null;
  };
  xpEvents: XpEventResponse[];
}

export interface HabitTogglePayload {
  checkedOn?: string;
  value?: number;
  note?: string;
}

export interface HabitMilestoneUnlock {
  id: string;
  milestoneId: string;
  title: string;
  habitId: string;
  streakDays: number;
  unlockedAt: string;
  xpAwardedAt: string | null;
}

export interface HabitMutationResponse {
  habit: Habit;
  milestoneUnlocks: HabitMilestoneUnlock[];
  xpEvents: XpEventResponse[];
  dashboardRefreshRequired: boolean;
}
