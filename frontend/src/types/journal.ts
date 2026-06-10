export interface HeroJournalReflection {
  proud: string;
  challenge: string;
  learned: string;
  improve: string;
  goalAction: string;
}

export interface HeroJournalEntry {
  id: string;
  title: string;
  content: string;
  entryType: string;
  mood: string;
  reflection: HeroJournalReflection;
  tags: string[];
  wordCount: number;
  sourceType: string;
  sourceId: string | null;
  entryDate: string;
  createdAt: string;
  updatedAt: string;
}

export interface JournalStats {
  totalEntries: number;
  currentStreak: number;
  wordsWritten: number;
  xpLogged: number;
  completedQuests: number;
  achievementsUnlocked: number;
}

export interface JournalTimelineEvent {
  id: string;
  occurredAt: string;
  timeLabel: string;
  title: string;
  description: string;
  sourceType: string;
  xp: number;
}

export interface StoryChapter {
  id: string;
  number: string;
  title: string;
  description: string;
  status: string;
  unlockedOn: string;
}

export interface CharacterIdentity {
  id: string;
  title: string;
  description: string;
  startedOn: string;
  endedOn: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CharacterIdentityState {
  current: CharacterIdentity | null;
  history: CharacterIdentity[];
}

export interface JournalInsight {
  title: string;
  body: string;
}

export interface JournalMoodOption {
  value: string;
  label: string;
}

export interface ReflectionQuestion {
  key: keyof JournalEntryPayload;
  question: string;
}

export interface JournalOverview {
  selectedDate: string;
  entries: HeroJournalEntry[];
  currentEntry: HeroJournalEntry | null;
  stats: JournalStats;
  activityTimeline: JournalTimelineEvent[];
  chapters: StoryChapter[];
  identity: CharacterIdentityState;
  insights: JournalInsight[];
  moodOptions: JournalMoodOption[];
  reflectionQuestions: ReflectionQuestion[];
  availableTags: string[];
}

export interface JournalEntryPayload {
  title: string;
  content?: string;
  mood?: string;
  reflectionProud?: string;
  reflectionChallenge?: string;
  reflectionLearned?: string;
  reflectionImprove?: string;
  reflectionGoalAction?: string;
  tags?: string[];
  entryDate?: string;
}
