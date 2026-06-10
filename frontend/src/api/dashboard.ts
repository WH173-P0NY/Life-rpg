import type {
  ActivityEntry,
  Achievement,
  DashboardRangeQuery,
  DashboardResponse,
  HabitMutationResponse,
  HabitTogglePayload,
  JournalEntry,
  JournalEntryMutationResponse,
  JournalEntryPayload,
  ManualActivityPayload,
  QuestCompletePayload,
  QuestMutationResponse,
  QuestProgressPayload,
  QuestRewardSkill,
  RankName
} from "../types/dashboard";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type RawRank = {
  label: string;
  threshold: string;
};

type RawDashboardResponse = {
  hero: {
    name: string;
    subtitle: string;
    level: number;
    total_xp: number;
    next_level_xp: number;
    progress_percent: number;
    rank: RawRank;
    main_skill: string;
  };
  resource_cards: Array<{
    name: string;
    value: number;
    max: number;
    progress: number;
  }>;
  attribute_rows: Array<{
    name: string;
    value: number;
    progress: number;
    growth: string;
  }>;
  daily_quests: Array<{
    id: number;
    completion_id: number | null;
    title: string;
    description?: string;
    quest_type?: string;
    difficulty?: string;
    reward_xp: number;
    reward_skills?: RawQuestRewardSkill[];
    rewards?: RawQuestRewardSkill[];
    progress_value?: number;
    target_value?: number;
    target_unit?: string;
    progress_percent?: number;
    completed_at?: string | null;
    current: number;
    target: number;
    unit: string;
    progress: number;
    completed: boolean;
  }>;
  active_challenge: {
    id?: number;
    title?: string;
    name?: string;
    status?: string;
    day: number;
    total?: number;
    total_days?: number;
    current_value?: number;
    target_value?: number;
    target_unit?: string;
    progress?: number;
    progress_percent?: number;
    reward?: string;
    reward_title?: string;
    reward_xp?: number;
    xp_reward?: number;
  } | null;
  habits: Array<{
    id: number;
    name?: string;
    label?: string;
    description?: string;
    frequency?: string;
    target_value?: number;
    target_unit?: string;
    checked?: boolean;
    completed_today?: boolean;
    completed?: boolean;
    check_in_id?: number | null;
    check_in?: RawHabitCheckIn | null;
    streak_days?: number;
    next_milestone?: RawHabitMilestonePreview | null;
  }>;
  habits_summary: {
    completed: number;
    total: number;
    streak_days: number;
  };
  weekly_progress: {
    bars: Array<{
      label: string;
      xp: number;
      height: number;
    }>;
    xp: number;
    quests: number;
    levels: number;
  };
  achievements: Array<{
    id?: number;
    achievement_id?: number;
    title: string;
    meta?: string;
    unlocked_at?: string;
    unlocked?: boolean;
    rarity: Achievement["rarity"];
  }>;
  journal_entries: Array<{
    id?: number;
    title: string;
    content?: string;
    body?: string;
    entry_type?: string;
    mood?: string;
    entry_date?: string;
    created_at?: string;
    meta?: string;
  }>;
  skill_rows: Array<{
    id: number;
    name: string;
    total_xp: number;
    level: number;
    progress: {
      percent: number;
    };
  }>;
  latest_statuses: Array<{
    definition: {
      id: number;
      name: string;
    };
    entry: {
      value: number;
    } | null;
  }>;
  activity_definitions: Array<{
    id: number;
    name: string;
  }>;
};

type RawActivityEntryResponse = {
  entry: {
    id: number;
    activity_definition: {
      id: number;
      name: string;
    };
    source: string;
    minutes: number;
    started_at: string;
    total_xp: number;
  };
};

type RawQuestRewardSkill = {
  id: number;
  name: string;
  xp?: number;
  xp_amount?: number;
};

type RawHabitCheckIn = {
  id: number;
  checked_on: string;
  value: number;
};

type RawHabitMilestonePreview = {
  id: number;
  title: string;
  streak_days: number;
  remaining_days?: number;
  days_remaining?: number;
  reward_xp: number;
};

type RawXpEventResponse = {
  id: number;
  skill: {
    id: number;
    name: string;
  };
  amount: number;
  source_type: string;
  note: string;
  earned_at: string;
};

type RawQuestMutationResponse = {
  quest: {
    id: number;
    title: string;
    completed: boolean;
    progress_value: number;
    target_value: number;
    target_unit: string;
    progress_percent: number;
    completion_id: number;
    reward_xp: number;
    reward_skills: RawQuestRewardSkill[];
  };
  completion: {
    id: number;
    completed_on: string;
    progress_value: number;
    completed_at: string | null;
    xp_awarded_at: string | null;
  };
  xp_events: RawXpEventResponse[];
};

type RawHabitMutationResponse = {
  habit: {
    id: number;
    name: string;
    description: string;
    frequency: string;
    target_value: number;
    target_unit: string;
    checked: boolean;
    completed_today: boolean;
    check_in_id: number | null;
    check_in: RawHabitCheckIn | null;
    streak_days: number;
    next_milestone: RawHabitMilestonePreview | null;
  };
  milestone_unlocks: Array<{
    id: number;
    milestone_id: number;
    title: string;
    habit_id: number;
    streak_days: number;
    unlocked_at: string;
    xp_awarded_at: string | null;
  }>;
  xp_events: RawXpEventResponse[];
  dashboard_refresh_required: boolean;
};

type RawJournalEntry = {
  id: number;
  title: string;
  content: string;
  entry_type: string;
  mood: string;
  source_type?: string;
  source_id?: number | null;
  entry_date: string;
  created_at: string;
  updated_at?: string;
  body?: string;
  meta?: string;
};

type RawJournalEntryMutationResponse = {
  entry: RawJournalEntry;
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

function toId(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function toNumber(value: string): number {
  const parsed = Number.parseInt(value.replace("+", ""), 10);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function toRankName(value: string): RankName {
  const ranks: RankName[] = [
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond",
    "Legendary"
  ];
  return ranks.includes(value as RankName) ? (value as RankName) : "Bronze";
}

function transformRewardSkill(raw: RawQuestRewardSkill): QuestRewardSkill {
  return {
    id: String(raw.id),
    name: raw.name,
    xp: raw.xp ?? raw.xp_amount ?? 0
  };
}

function transformHabitCheckIn(raw: RawHabitCheckIn | null | undefined) {
  if (!raw) {
    return null;
  }

  return {
    id: String(raw.id),
    checkedOn: raw.checked_on,
    value: raw.value
  };
}

function transformHabitMilestone(raw: RawHabitMilestonePreview | null | undefined) {
  if (!raw) {
    return null;
  }

  return {
    id: String(raw.id),
    title: raw.title,
    streakDays: raw.streak_days,
    remainingDays: raw.remaining_days ?? raw.days_remaining ?? 0,
    rewardXp: raw.reward_xp
  };
}

function transformXpEvent(raw: RawXpEventResponse) {
  return {
    id: String(raw.id),
    skill: {
      id: String(raw.skill.id),
      name: raw.skill.name
    },
    amount: raw.amount,
    sourceType: raw.source_type,
    note: raw.note,
    earnedAt: raw.earned_at
  };
}

function transformJournalEntry(raw: RawJournalEntry): JournalEntry {
  const content = raw.content ?? raw.body ?? "";
  const createdAtLabel = raw.meta ?? raw.entry_date;

  return {
    id: String(raw.id),
    title: raw.title,
    content,
    excerpt: content,
    entryType: raw.entry_type,
    mood: raw.mood,
    entryDate: raw.entry_date,
    createdAt: raw.created_at,
    createdAtLabel
  };
}

function transformQuestMutation(raw: RawQuestMutationResponse): QuestMutationResponse {
  return {
    quest: {
      id: String(raw.quest.id),
      title: raw.quest.title,
      completed: raw.quest.completed,
      progressValue: raw.quest.progress_value,
      targetValue: raw.quest.target_value,
      targetUnit: raw.quest.target_unit,
      progressPercent: raw.quest.progress_percent,
      completionId: String(raw.quest.completion_id),
      rewardXp: raw.quest.reward_xp,
      rewardSkills: raw.quest.reward_skills.map(transformRewardSkill)
    },
    completion: {
      id: String(raw.completion.id),
      completedOn: raw.completion.completed_on,
      progressValue: raw.completion.progress_value,
      completedAt: raw.completion.completed_at,
      xpAwardedAt: raw.completion.xp_awarded_at
    },
    xpEvents: raw.xp_events.map(transformXpEvent)
  };
}

function transformHabitMutation(raw: RawHabitMutationResponse): HabitMutationResponse {
  return {
    habit: {
      id: String(raw.habit.id),
      name: raw.habit.name,
      description: raw.habit.description,
      frequency: raw.habit.frequency,
      targetValue: raw.habit.target_value,
      targetUnit: raw.habit.target_unit,
      checked: raw.habit.checked,
      completedToday: raw.habit.completed_today,
      checkInId: raw.habit.check_in_id === null ? null : String(raw.habit.check_in_id),
      checkIn: transformHabitCheckIn(raw.habit.check_in),
      streakDays: raw.habit.streak_days,
      nextMilestone: transformHabitMilestone(raw.habit.next_milestone)
    },
    milestoneUnlocks: raw.milestone_unlocks.map((unlock) => ({
      id: String(unlock.id),
      milestoneId: String(unlock.milestone_id),
      title: unlock.title,
      habitId: String(unlock.habit_id),
      streakDays: unlock.streak_days,
      unlockedAt: unlock.unlocked_at,
      xpAwardedAt: unlock.xp_awarded_at
    })),
    xpEvents: raw.xp_events.map(transformXpEvent),
    dashboardRefreshRequired: raw.dashboard_refresh_required
  };
}

function transformDashboard(raw: RawDashboardResponse): DashboardResponse {
  return {
    hero: {
      name: raw.hero.name,
      title: raw.hero.subtitle,
      level: raw.hero.level,
      rank: toRankName(raw.hero.rank.label),
      totalXp: raw.hero.total_xp,
      currentLevelXp: raw.hero.total_xp,
      nextLevelXp: raw.hero.next_level_xp,
      progressPercent: raw.hero.progress_percent
    },
    resources: raw.resource_cards.map((resource) => ({
      id: toId(resource.name),
      name: resource.name,
      value: resource.value,
      maxValue: resource.max,
      progressPercent: resource.progress
    })),
    attributes: raw.attribute_rows.map((attribute) => ({
      id: toId(attribute.name),
      name: attribute.name,
      description: attribute.name,
      value: attribute.value,
      progressPercent: attribute.progress,
      growth: toNumber(attribute.growth)
    })),
    dailyQuests: raw.daily_quests.map((quest) => {
      const rewardSkills = (quest.reward_skills ?? quest.rewards ?? []).map(transformRewardSkill);
      const progressValue = quest.progress_value ?? quest.current;
      const targetValue = quest.target_value ?? quest.target;

      return {
        id: String(quest.id),
        completionId: quest.completion_id === null ? null : String(quest.completion_id),
        title: quest.title,
        description: quest.description,
        questType: quest.quest_type,
        difficulty: quest.difficulty,
        progressValue,
        targetValue,
        progressPercent: quest.progress_percent ?? quest.progress,
        unit: quest.target_unit ?? quest.unit,
        completed: quest.completed,
        completedAt: quest.completed_at,
        reward: {
          xp: quest.reward_xp,
          skillIds: rewardSkills.map((skill) => skill.id)
        },
        rewardSkills
      };
    }),
    habits: raw.habits.map((habit) => {
      const completedToday = habit.completed_today ?? habit.completed ?? habit.checked ?? false;

      return {
        id: String(habit.id),
        name: habit.name ?? habit.label ?? "Habit",
        description: habit.description,
        frequency: habit.frequency,
        targetValue: habit.target_value,
        targetUnit: habit.target_unit,
        checked: habit.checked ?? completedToday,
        completedToday,
        checkInId: habit.check_in_id === null || habit.check_in_id === undefined ? null : String(habit.check_in_id),
        checkIn: transformHabitCheckIn(habit.check_in),
        streakDays: habit.streak_days ?? (completedToday ? raw.habits_summary.streak_days : 0),
        nextMilestone: transformHabitMilestone(habit.next_milestone)
      };
    }),
    habitsSummary: {
      completed: raw.habits_summary.completed,
      total: raw.habits_summary.total,
      streakDays: raw.habits_summary.streak_days
    },
    activeChallenge: raw.active_challenge
      ? {
          id: raw.active_challenge.id
            ? String(raw.active_challenge.id)
            : toId(raw.active_challenge.title ?? raw.active_challenge.name ?? "challenge"),
          title: raw.active_challenge.title ?? raw.active_challenge.name ?? "Challenge",
          status: raw.active_challenge.status,
          day: raw.active_challenge.day,
          totalDays: raw.active_challenge.total_days ?? raw.active_challenge.total ?? 1,
          currentValue: raw.active_challenge.current_value,
          targetValue: raw.active_challenge.target_value,
          targetUnit: raw.active_challenge.target_unit,
          progressPercent: raw.active_challenge.progress_percent ?? raw.active_challenge.progress ?? 0,
          rewardLabel:
            raw.active_challenge.reward_title ??
            raw.active_challenge.reward ??
            "No reward configured",
          rewardXp: raw.active_challenge.reward_xp ?? raw.active_challenge.xp_reward ?? 0
        }
      : null,
    skills: raw.skill_rows.map((skill) => ({
      id: String(skill.id),
      name: skill.name,
      level: skill.level,
      xp: skill.total_xp,
      progressPercent: skill.progress.percent
    })),
    statuses: raw.latest_statuses.map((status) => ({
      id: String(status.definition.id),
      name: status.definition.name,
      value: status.entry?.value ?? 0,
      maxValue: 100,
      progressPercent: status.entry?.value ?? 0
    })),
    weeklyProgress: {
      xp: raw.weekly_progress.xp,
      quests: raw.weekly_progress.quests,
      levels: raw.weekly_progress.levels,
      points: raw.weekly_progress.bars.map((bar) => ({
        label: bar.label,
        xp: bar.xp,
        minutes: 0
      }))
    },
    achievements: raw.achievements.map((achievement, index) => ({
      id: achievement.id
        ? String(achievement.id)
        : achievement.achievement_id
          ? String(achievement.achievement_id)
          : `${toId(achievement.title)}-${index}`,
      title: achievement.title,
      rarity: achievement.rarity,
      unlockedAtLabel: achievement.meta ?? achievement.unlocked_at ?? "Unlocked"
    })),
    journalEntries: raw.journal_entries.map((entry, index) =>
      transformJournalEntry({
        id: entry.id ?? index,
        title: entry.title,
        content: entry.content ?? entry.body ?? "",
        entry_type: entry.entry_type ?? "manual",
        mood: entry.mood ?? "",
        entry_date: entry.entry_date ?? entry.meta ?? "",
        created_at: entry.created_at ?? "",
        body: entry.body,
        meta: entry.meta
      })
    ),
    activityDefinitions: raw.activity_definitions.map((definition) => ({
      id: String(definition.id),
      name: definition.name,
      defaultMinutes: 30
    }))
  };
}

function transformActivityEntry(raw: RawActivityEntryResponse): ActivityEntry {
  return {
    id: String(raw.entry.id),
    activityDefinitionId: String(raw.entry.activity_definition.id),
    minutes: raw.entry.minutes,
    xp: raw.entry.total_xp,
    startedAt: raw.entry.started_at
  };
}

export async function fetchDashboard(
  queryParams?: string | DashboardRangeQuery
): Promise<DashboardResponse> {
  const searchParams = new URLSearchParams();

  if (typeof queryParams === "string") {
    searchParams.set("range", queryParams);
  } else if (queryParams) {
    searchParams.set("range", queryParams.range);

    if (queryParams.start) {
      searchParams.set("start", queryParams.start);
    }

    if (queryParams.end) {
      searchParams.set("end", queryParams.end);
    }
  }

  const query = searchParams.toString();
  const raw = await requestJson<RawDashboardResponse>(
    `/api/dashboard/${query ? `?${query}` : ""}`
  );
  return transformDashboard(raw);
}

export async function createManualActivity(
  payload: ManualActivityPayload
): Promise<ActivityEntry> {
  const raw = await requestJson<RawActivityEntryResponse>("/api/activities/manual/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      activity_definition_id: payload.activityDefinitionId,
      minutes: payload.minutes,
      started_at: payload.startedAt,
      source: payload.source
    })
  });
  return transformActivityEntry(raw);
}

export async function completeQuest(
  questId: string,
  payload: QuestCompletePayload = {}
): Promise<QuestMutationResponse> {
  const raw = await requestJson<RawQuestMutationResponse>(`/api/quests/${questId}/complete/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      completed_on: payload.completedOn,
      note: payload.note
    })
  });
  return transformQuestMutation(raw);
}

export async function updateQuestProgress(
  questId: string,
  payload: QuestProgressPayload
): Promise<QuestMutationResponse> {
  const raw = await requestJson<RawQuestMutationResponse>(`/api/quests/${questId}/progress/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      progress_value: payload.progressValue,
      completed_on: payload.completedOn,
      note: payload.note
    })
  });
  return transformQuestMutation(raw);
}

export async function toggleHabit(
  habitId: string,
  payload: HabitTogglePayload = {}
): Promise<HabitMutationResponse> {
  const raw = await requestJson<RawHabitMutationResponse>(`/api/habits/${habitId}/toggle/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      checked_on: payload.checkedOn,
      value: payload.value,
      note: payload.note
    })
  });
  return transformHabitMutation(raw);
}

export async function createJournalEntry(
  payload: JournalEntryPayload
): Promise<JournalEntryMutationResponse> {
  const raw = await requestJson<RawJournalEntryMutationResponse>("/api/journal/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify({
      title: payload.title,
      content: payload.content,
      mood: payload.mood,
      entry_date: payload.entryDate
    })
  });
  return {
    entry: transformJournalEntry(raw.entry)
  };
}
