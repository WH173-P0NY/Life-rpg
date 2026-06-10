import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Compass,
  Search,
  Sparkles,
  Tags,
  UserRound
} from "lucide-react";

import {
  createHeroJournalEntry,
  fetchJournalOverview,
  updateHeroJournalEntry
} from "../api/journal";
import type { HeroJournalEntry, JournalEntryPayload, JournalOverview } from "../types/journal";

interface HeroJournalViewProps {
  isApiReady: boolean;
  onJournalChanged: () => Promise<void>;
}

type JournalSection = "entries" | "quests" | "achievements" | "journey" | "reflections" | "insights";

interface JournalFormState {
  title: string;
  content: string;
  mood: string;
  entryDate: string;
  reflectionProud: string;
  reflectionChallenge: string;
  reflectionLearned: string;
  reflectionImprove: string;
  reflectionGoalAction: string;
  tagText: string;
}

const sections: Array<{ id: JournalSection; label: string }> = [
  { id: "entries", label: "Entries" },
  { id: "quests", label: "Quests" },
  { id: "achievements", label: "Achievements" },
  { id: "journey", label: "Journey" },
  { id: "reflections", label: "Reflections" },
  { id: "insights", label: "Insights" }
];

function localDateInputValue(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function blankForm(entryDate: string): JournalFormState {
  return {
    title: "",
    content: "",
    mood: "",
    entryDate,
    reflectionProud: "",
    reflectionChallenge: "",
    reflectionLearned: "",
    reflectionImprove: "",
    reflectionGoalAction: "",
    tagText: ""
  };
}

function formFromEntry(entry: HeroJournalEntry): JournalFormState {
  return {
    title: entry.title,
    content: entry.content,
    mood: entry.mood,
    entryDate: entry.entryDate,
    reflectionProud: entry.reflection.proud,
    reflectionChallenge: entry.reflection.challenge,
    reflectionLearned: entry.reflection.learned,
    reflectionImprove: entry.reflection.improve,
    reflectionGoalAction: entry.reflection.goalAction,
    tagText: entry.tags.join(", ")
  };
}

function numberLabel(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function readableDate(value: string): string {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}

function tagsFromText(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function HeroJournalView({ isApiReady, onJournalChanged }: HeroJournalViewProps) {
  const [overview, setOverview] = useState<JournalOverview | null>(null);
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(localDateInputValue);
  const [activeSection, setActiveSection] = useState<JournalSection>("entries");
  const [searchQuery, setSearchQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState("");
  const [form, setForm] = useState<JournalFormState>(() => blankForm(selectedDate));
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    if (!isApiReady) {
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchJournalOverview({
        day: selectedDate,
        query: appliedQuery,
        tag: selectedTag,
        limit: 50
      });
      setOverview(response);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Journal API is not available");
    } finally {
      setIsLoading(false);
    }
  }, [appliedQuery, isApiReady, selectedDate, selectedTag]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (!overview) {
      return;
    }

    setSelectedEntryId((current) => {
      if (current && overview.entries.some((entry) => entry.id === current)) {
        return current;
      }
      return overview.currentEntry?.id ?? overview.entries[0]?.id ?? null;
    });
  }, [overview]);

  const selectedEntry = useMemo(() => {
    if (!overview || !selectedEntryId) {
      return null;
    }
    return overview.entries.find((entry) => entry.id === selectedEntryId) ?? null;
  }, [overview, selectedEntryId]);

  useEffect(() => {
    if (selectedEntry) {
      setForm(formFromEntry(selectedEntry));
    } else {
      setForm(blankForm(selectedDate));
    }
  }, [selectedDate, selectedEntry]);

  function updateForm<K extends keyof JournalFormState>(key: K, value: JournalFormState[K]) {
    setForm((current) => ({
      ...current,
      [key]: value
    }));
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedQuery(searchQuery.trim());
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady) {
      setError("Journal actions require the live Django API.");
      return;
    }
    if (!form.title.trim()) {
      setError("Title is required.");
      return;
    }

    const payload: JournalEntryPayload = {
      title: form.title.trim(),
      content: form.content.trim(),
      mood: form.mood,
      reflectionProud: form.reflectionProud.trim(),
      reflectionChallenge: form.reflectionChallenge.trim(),
      reflectionLearned: form.reflectionLearned.trim(),
      reflectionImprove: form.reflectionImprove.trim(),
      reflectionGoalAction: form.reflectionGoalAction.trim(),
      tags: tagsFromText(form.tagText),
      entryDate: form.entryDate
    };

    setIsSaving(true);
    setError(null);
    setFeedback(null);
    try {
      const savedEntry = selectedEntry
        ? await updateHeroJournalEntry(selectedEntry.id, payload)
        : await createHeroJournalEntry(payload);
      setSelectedEntryId(savedEntry.id);
      setFeedback(selectedEntry ? "Entry updated" : "Entry saved");
      window.setTimeout(() => setFeedback(null), 1800);
      await loadOverview();
      await onJournalChanged();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Journal API is not available");
    } finally {
      setIsSaving(false);
    }
  }

  if (!isApiReady) {
    return (
      <article className="panel p-5">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Hero Journal</p>
            <h2>Chronicle unavailable</h2>
          </div>
          <span>Offline</span>
        </div>
        <p className="mt-4 text-sm leading-6 text-zinc-500">
          The full journal needs the live Django API because entries, activity timeline and identity history are stored
          on the backend.
        </p>
      </article>
    );
  }

  const stats = overview?.stats;

  return (
    <section className="grid gap-4 2xl:grid-cols-[320px_1fr]">
      <aside className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Chronicle</p>
              <h2>Hero Journal</h2>
            </div>
            <span>{isLoading ? "Syncing" : `${overview?.entries.length ?? 0} entries`}</span>
          </div>

          <nav className="mt-4 space-y-2">
            {sections.map((section) => (
              <button
                className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition ${
                  activeSection === section.id
                    ? "border-xp/50 bg-xp/10 text-xp"
                    : "border-white/10 bg-white/[0.03] text-zinc-400 hover:border-xp/30 hover:text-zinc-100"
                }`}
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                type="button"
              >
                {section.label}
                <Compass size={14} />
              </button>
            ))}
          </nav>
        </article>

        <article className="panel p-4">
          <form onSubmit={handleSearch}>
            <label className="field-label" htmlFor="journal-search">
              Search
            </label>
            <div className="mt-2 flex gap-2">
              <input
                className="field-control mt-0"
                id="journal-search"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Quest, mood, chapter..."
                value={searchQuery}
              />
              <button className="icon-button shrink-0" type="submit">
                <Search size={17} />
              </button>
            </div>
          </form>

          <div className="mt-4">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">
              <Tags size={13} />
              Tags
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className={`rounded-lg border px-3 py-1.5 text-xs transition ${
                  selectedTag === "" ? "border-xp/50 bg-xp/10 text-xp" : "border-white/10 text-zinc-500"
                }`}
                onClick={() => setSelectedTag("")}
                type="button"
              >
                all
              </button>
              {(overview?.availableTags ?? []).map((tag) => (
                <button
                  className={`rounded-lg border px-3 py-1.5 text-xs transition ${
                    selectedTag === tag ? "border-xp/50 bg-xp/10 text-xp" : "border-white/10 text-zinc-500"
                  }`}
                  key={tag}
                  onClick={() => setSelectedTag(tag)}
                  type="button"
                >
                  #{tag}
                </button>
              ))}
            </div>
          </div>
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Timeline</p>
              <h2>Entries</h2>
            </div>
            <button
              className="rounded-lg border border-xp/40 bg-xp/10 px-3 py-1.5 text-xs font-semibold text-xp transition hover:bg-xp/15"
              onClick={() => setSelectedEntryId(null)}
              type="button"
            >
              New
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {(overview?.entries ?? []).map((entry) => (
              <button
                className={`w-full rounded-lg border p-3 text-left transition ${
                  selectedEntryId === entry.id
                    ? "border-xp/50 bg-xp/10"
                    : "border-white/10 bg-white/[0.03] hover:border-xp/30"
                }`}
                key={entry.id}
                onClick={() => setSelectedEntryId(entry.id)}
                type="button"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-zinc-100">{entry.title}</p>
                  <span className="shrink-0 text-xs text-zinc-600">{entry.wordCount}w</span>
                </div>
                <p className="mt-1 text-xs text-zinc-500">{readableDate(entry.entryDate)}</p>
                {entry.tags.length ? (
                  <p className="mt-2 truncate text-xs text-xp">{entry.tags.map((tag) => `#${tag}`).join(" ")}</p>
                ) : null}
              </button>
            ))}
            {overview && overview.entries.length === 0 ? (
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-zinc-500">
                No entries match the current filters.
              </div>
            ) : null}
          </div>
        </article>
      </aside>

      <div className="space-y-4">
        <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Entries" value={stats ? numberLabel(stats.totalEntries) : "..."} />
          <StatCard label="Streak" value={stats ? `${stats.currentStreak}d` : "..."} />
          <StatCard label="Words" value={stats ? numberLabel(stats.wordsWritten) : "..."} />
          <StatCard label="XP Logged" value={stats ? numberLabel(stats.xpLogged) : "..."} />
          <StatCard label="Quests" value={stats ? numberLabel(stats.completedQuests) : "..."} />
          <StatCard label="Achievements" value={stats ? numberLabel(stats.achievementsUnlocked) : "..."} />
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
          <article className="panel p-4">
            <form onSubmit={handleSave}>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Daily Reflection</p>
                  <h2>{selectedEntry ? "Edit Chronicle" : "New Chronicle"}</h2>
                </div>
                <span>{form.entryDate ? readableDate(form.entryDate) : "Draft"}</span>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_170px]">
                <label>
                  <span className="field-label">Title</span>
                  <input
                    className="field-control"
                    disabled={isSaving}
                    onChange={(event) => updateForm("title", event.target.value)}
                    placeholder="Daily Chronicle"
                    value={form.title}
                  />
                </label>
                <label>
                  <span className="field-label">Mood</span>
                  <select
                    className="field-control"
                    disabled={isSaving}
                    onChange={(event) => updateForm("mood", event.target.value)}
                    value={form.mood}
                  >
                    <option value="">No mood</option>
                    {(overview?.moodOptions ?? []).map((mood) => (
                      <option key={mood.value} value={mood.value}>
                        {mood.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Date</span>
                  <input
                    className="field-control"
                    disabled={isSaving}
                    onChange={(event) => updateForm("entryDate", event.target.value)}
                    type="date"
                    value={form.entryDate}
                  />
                </label>
              </div>

              <label className="mt-3 block">
                <span className="field-label">What happened today?</span>
                <textarea
                  className="field-control min-h-40 resize-y leading-6"
                  disabled={isSaving}
                  onChange={(event) => updateForm("content", event.target.value)}
                  placeholder="Write in Markdown or plain text."
                  value={form.content}
                />
              </label>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <ReflectionField
                  label="What am I proud of today?"
                  onChange={(value) => updateForm("reflectionProud", value)}
                  value={form.reflectionProud}
                />
                <ReflectionField
                  label="What challenged me?"
                  onChange={(value) => updateForm("reflectionChallenge", value)}
                  value={form.reflectionChallenge}
                />
                <ReflectionField
                  label="What did I learn?"
                  onChange={(value) => updateForm("reflectionLearned", value)}
                  value={form.reflectionLearned}
                />
                <ReflectionField
                  label="What should I improve tomorrow?"
                  onChange={(value) => updateForm("reflectionImprove", value)}
                  value={form.reflectionImprove}
                />
              </div>

              <label className="mt-3 block">
                <span className="field-label">What action moved me closer to my goals?</span>
                <textarea
                  className="field-control min-h-20 resize-y leading-6"
                  disabled={isSaving}
                  onChange={(event) => updateForm("reflectionGoalAction", event.target.value)}
                  value={form.reflectionGoalAction}
                />
              </label>

              <label className="mt-3 block">
                <span className="field-label">Tags</span>
                <input
                  className="field-control"
                  disabled={isSaving}
                  onChange={(event) => updateForm("tagText", event.target.value)}
                  placeholder="learning, discipline, health"
                  value={form.tagText}
                />
              </label>

              {feedback ? (
                <p className="mt-3 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
                  {feedback}
                </p>
              ) : null}
              {error ? (
                <p className="mt-3 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">
                  {error}
                </p>
              ) : null}

              <div className="mt-4 flex flex-wrap gap-2">
                <button className="primary-button w-auto min-w-36" disabled={isSaving || !form.title.trim()} type="submit">
                  {isSaving ? "Saving..." : selectedEntry ? "Update Entry" : "Save Entry"}
                </button>
                <button
                  className="rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-zinc-400 transition hover:border-xp/40 hover:text-xp"
                  disabled={isSaving}
                  onClick={() => setSelectedEntryId(null)}
                  type="button"
                >
                  New Entry
                </button>
              </div>
            </form>
          </article>

          <article className="panel p-4">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Activity Timeline</p>
                <h2>{readableDate(selectedDate)}</h2>
              </div>
              <label className="flex items-center gap-2 text-xs text-zinc-500">
                <CalendarDays size={14} />
                <input
                  className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-xs text-zinc-300 outline-none"
                  onChange={(event) => setSelectedDate(event.target.value)}
                  type="date"
                  value={selectedDate}
                />
              </label>
            </div>

            <div className="mt-5 space-y-3">
              {(overview?.activityTimeline ?? []).map((event) => (
                <div className="grid grid-cols-[58px_1fr] gap-3" key={event.id}>
                  <div className="flex items-start gap-2 text-xs font-medium text-xp">
                    <Clock3 size={13} />
                    {event.timeLabel}
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold text-zinc-100">{event.title}</p>
                      {event.xp > 0 ? <span className="text-xs font-semibold text-xp">+{event.xp} XP</span> : null}
                    </div>
                    {event.description ? (
                      <p className="mt-1 text-sm leading-6 text-zinc-500">{event.description}</p>
                    ) : null}
                    <p className="mt-2 text-xs uppercase tracking-[0.16em] text-zinc-600">{event.sourceType}</p>
                  </div>
                </div>
              ))}
              {overview && overview.activityTimeline.length === 0 ? (
                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-zinc-500">
                  No activity was recorded for this day yet.
                </div>
              ) : null}
            </div>
          </article>
        </section>

        <section className="grid gap-4 xl:grid-cols-3">
          <article className="panel p-4">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Identity</p>
                <h2>Who am I becoming?</h2>
              </div>
              <UserRound className="text-xp" size={18} />
            </div>
            {overview?.identity.current ? (
              <div className="mt-4">
                <p className="text-2xl font-semibold text-zinc-50">{overview.identity.current.title}</p>
                <p className="mt-2 text-sm leading-6 text-zinc-500">{overview.identity.current.description}</p>
                <p className="mt-3 text-xs text-zinc-600">Since {readableDate(overview.identity.current.startedOn)}</p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-zinc-500">No active identity has been defined yet.</p>
            )}
          </article>

          <article className="panel p-4">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Journey</p>
                <h2>Story Chapters</h2>
              </div>
              <BookOpen className="text-xp" size={18} />
            </div>
            <div className="mt-4 space-y-3">
              {(overview?.chapters ?? []).map((chapter) => (
                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={chapter.id}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-xp">{chapter.number}</p>
                    <span className="text-xs capitalize text-zinc-600">{chapter.status}</span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-zinc-100">{chapter.title}</p>
                  <p className="mt-1 text-sm leading-6 text-zinc-500">{chapter.description}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="panel p-4">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Insights</p>
                <h2>AI Companion</h2>
              </div>
              <Sparkles className="text-xp" size={18} />
            </div>
            <div className="mt-4 space-y-3">
              {(overview?.insights ?? []).map((insight) => (
                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={insight.title}>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="text-success" size={15} />
                    <p className="text-sm font-semibold text-zinc-100">{insight.title}</p>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">{insight.body}</p>
                </div>
              ))}
            </div>
          </article>
        </section>
      </div>
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="panel p-4">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-zinc-50">{value}</p>
    </article>
  );
}

function ReflectionField({
  label,
  onChange,
  value
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label className="block">
      <span className="field-label">{label}</span>
      <textarea
        className="field-control min-h-24 resize-y leading-6"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}
