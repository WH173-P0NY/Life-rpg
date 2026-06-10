import type {
  CharacterIdentity,
  HeroJournalEntry,
  JournalEntryPayload,
  JournalOverview,
  ReflectionQuestion
} from "../types/journal";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

type RawJournalReflection = {
  proud: string;
  challenge: string;
  learned: string;
  improve: string;
  goal_action: string;
};

type RawJournalEntry = {
  id: number;
  title: string;
  content: string;
  entry_type: string;
  mood: string;
  reflection: RawJournalReflection;
  tags: string[];
  word_count: number;
  source_type: string;
  source_id: number | null;
  entry_date: string;
  created_at: string;
  updated_at: string;
};

type RawJournalStats = {
  total_entries: number;
  current_streak: number;
  words_written: number;
  xp_logged: number;
  completed_quests: number;
  achievements_unlocked: number;
};

type RawTimelineEvent = {
  id: string;
  occurred_at: string;
  time_label: string;
  title: string;
  description: string;
  source_type: string;
  xp: number;
};

type RawStoryChapter = {
  id: string;
  number: string;
  title: string;
  description: string;
  status: string;
  unlocked_on: string;
};

type RawCharacterIdentity = {
  id: number;
  title: string;
  description: string;
  started_on: string;
  ended_on: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

type RawJournalOverview = {
  selected_date: string;
  entries: RawJournalEntry[];
  current_entry: RawJournalEntry | null;
  stats: RawJournalStats;
  activity_timeline: RawTimelineEvent[];
  chapters: RawStoryChapter[];
  identity: {
    current: RawCharacterIdentity | null;
    history: RawCharacterIdentity[];
  };
  insights: Array<{
    title: string;
    body: string;
  }>;
  mood_options: Array<{
    value: string;
    label: string;
  }>;
  reflection_questions: Array<{
    key: string;
    question: string;
  }>;
  available_tags: string[];
};

type RawJournalEntryMutationResponse = {
  entry: RawJournalEntry;
};

interface JournalOverviewQuery {
  day?: string;
  query?: string;
  tag?: string;
  limit?: number;
}

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

function transformJournalEntry(raw: RawJournalEntry): HeroJournalEntry {
  return {
    id: String(raw.id),
    title: raw.title,
    content: raw.content,
    entryType: raw.entry_type,
    mood: raw.mood,
    reflection: {
      proud: raw.reflection.proud,
      challenge: raw.reflection.challenge,
      learned: raw.reflection.learned,
      improve: raw.reflection.improve,
      goalAction: raw.reflection.goal_action
    },
    tags: raw.tags,
    wordCount: raw.word_count,
    sourceType: raw.source_type,
    sourceId: raw.source_id === null ? null : String(raw.source_id),
    entryDate: raw.entry_date,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at
  };
}

function transformIdentity(raw: RawCharacterIdentity): CharacterIdentity {
  return {
    id: String(raw.id),
    title: raw.title,
    description: raw.description,
    startedOn: raw.started_on,
    endedOn: raw.ended_on,
    isActive: raw.is_active,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at
  };
}

function transformQuestionKey(key: string): ReflectionQuestion["key"] {
  const map: Record<string, ReflectionQuestion["key"]> = {
    reflection_proud: "reflectionProud",
    reflection_challenge: "reflectionChallenge",
    reflection_learned: "reflectionLearned",
    reflection_improve: "reflectionImprove",
    reflection_goal_action: "reflectionGoalAction"
  };
  return map[key] ?? "reflectionProud";
}

function transformJournalOverview(raw: RawJournalOverview): JournalOverview {
  return {
    selectedDate: raw.selected_date,
    entries: raw.entries.map(transformJournalEntry),
    currentEntry: raw.current_entry ? transformJournalEntry(raw.current_entry) : null,
    stats: {
      totalEntries: raw.stats.total_entries,
      currentStreak: raw.stats.current_streak,
      wordsWritten: raw.stats.words_written,
      xpLogged: raw.stats.xp_logged,
      completedQuests: raw.stats.completed_quests,
      achievementsUnlocked: raw.stats.achievements_unlocked
    },
    activityTimeline: raw.activity_timeline.map((event) => ({
      id: event.id,
      occurredAt: event.occurred_at,
      timeLabel: event.time_label,
      title: event.title,
      description: event.description,
      sourceType: event.source_type,
      xp: event.xp
    })),
    chapters: raw.chapters.map((chapter) => ({
      id: chapter.id,
      number: chapter.number,
      title: chapter.title,
      description: chapter.description,
      status: chapter.status,
      unlockedOn: chapter.unlocked_on
    })),
    identity: {
      current: raw.identity.current ? transformIdentity(raw.identity.current) : null,
      history: raw.identity.history.map(transformIdentity)
    },
    insights: raw.insights,
    moodOptions: raw.mood_options,
    reflectionQuestions: raw.reflection_questions.map((question) => ({
      key: transformQuestionKey(question.key),
      question: question.question
    })),
    availableTags: raw.available_tags
  };
}

function serializePayload(payload: JournalEntryPayload) {
  return {
    title: payload.title,
    content: payload.content,
    mood: payload.mood,
    reflection_proud: payload.reflectionProud,
    reflection_challenge: payload.reflectionChallenge,
    reflection_learned: payload.reflectionLearned,
    reflection_improve: payload.reflectionImprove,
    reflection_goal_action: payload.reflectionGoalAction,
    tags: payload.tags,
    entry_date: payload.entryDate
  };
}

export async function fetchJournalOverview(
  query: JournalOverviewQuery = {}
): Promise<JournalOverview> {
  const searchParams = new URLSearchParams();
  if (query.day) {
    searchParams.set("day", query.day);
  }
  if (query.query) {
    searchParams.set("query", query.query);
  }
  if (query.tag) {
    searchParams.set("tag", query.tag);
  }
  if (query.limit) {
    searchParams.set("limit", String(query.limit));
  }

  const raw = await requestJson<RawJournalOverview>(
    `/api/journal/${searchParams.toString() ? `?${searchParams.toString()}` : ""}`
  );
  return transformJournalOverview(raw);
}

export async function createHeroJournalEntry(
  payload: JournalEntryPayload
): Promise<HeroJournalEntry> {
  const raw = await requestJson<RawJournalEntryMutationResponse>("/api/journal/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify(serializePayload(payload))
  });
  return transformJournalEntry(raw.entry);
}

export async function updateHeroJournalEntry(
  entryId: string,
  payload: JournalEntryPayload
): Promise<HeroJournalEntry> {
  const raw = await requestJson<RawJournalEntryMutationResponse>(`/api/journal/${entryId}/`, {
    method: "PATCH",
    headers: {
      "X-CSRFToken": getCookie("csrftoken")
    },
    body: JSON.stringify(serializePayload(payload))
  });
  return transformJournalEntry(raw.entry);
}
