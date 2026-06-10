import type { FormEvent } from "react";
import { useState } from "react";

import { createJournalEntry } from "../api/dashboard";
import type { JournalEntry } from "../types/dashboard";

interface JournalPanelProps {
  entries: JournalEntry[];
  isApiReady: boolean;
  onJournalCreated: () => Promise<void>;
}

export function JournalPanel({ entries, isApiReady, onJournalCreated }: JournalPanelProps) {
  const [journalTitle, setJournalTitle] = useState("");
  const [journalContent, setJournalContent] = useState("");
  const [journalMood, setJournalMood] = useState("");
  const [isSavingJournal, setIsSavingJournal] = useState(false);
  const [journalFeedback, setJournalFeedback] = useState<string | null>(null);
  const [journalError, setJournalError] = useState<string | null>(null);

  async function handleJournalSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!isApiReady) {
      setJournalError("Journal actions require the live Django API.");
      return;
    }
    if (!journalTitle.trim()) {
      setJournalError("Title is required.");
      return;
    }

    setIsSavingJournal(true);
    setJournalError(null);
    setJournalFeedback(null);

    try {
      await createJournalEntry({
        title: journalTitle.trim(),
        content: journalContent.trim(),
        mood: journalMood.trim()
      });
      setJournalTitle("");
      setJournalContent("");
      setJournalMood("");
      setJournalFeedback("Entry saved");
      window.setTimeout(() => setJournalFeedback(null), 1600);
      await onJournalCreated();
    } catch (error) {
      setJournalError(error instanceof Error ? error.message : "Journal API is not available");
    } finally {
      setIsSavingJournal(false);
    }
  }

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Reflection</p>
          <h2>Journal</h2>
        </div>
        <span>{entries.length}</span>
      </div>

      <form className="mt-4 space-y-3" onSubmit={handleJournalSubmit}>
        <input
          className="field-control mt-0"
          disabled={!isApiReady || isSavingJournal}
          onChange={(event) => setJournalTitle(event.target.value)}
          placeholder="Title"
          value={journalTitle}
        />
        <textarea
          className="field-control mt-0 min-h-24 resize-none leading-6"
          disabled={!isApiReady || isSavingJournal}
          onChange={(event) => setJournalContent(event.target.value)}
          placeholder="Reflection"
          value={journalContent}
        />
        <div className="flex gap-2">
          <input
            className="field-control mt-0 min-w-0 flex-1"
            disabled={!isApiReady || isSavingJournal}
            onChange={(event) => setJournalMood(event.target.value)}
            placeholder="Mood"
            value={journalMood}
          />
          <button
            className="rounded-lg border border-xp/40 bg-xp/10 px-4 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/[0.03] disabled:text-zinc-600"
            disabled={!isApiReady || isSavingJournal || !journalTitle.trim()}
            type="submit"
          >
            {isSavingJournal ? "Saving..." : "Save"}
          </button>
        </div>
      </form>

      {journalFeedback ? (
        <p className="mt-3 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
          {journalFeedback}
        </p>
      ) : null}
      {journalError ? (
        <p className="mt-3 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">
          {journalError}
        </p>
      ) : null}

      <div className="mt-4 space-y-3">
        {entries.map((entry) => (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3" key={entry.id}>
            <p className="text-sm font-semibold text-zinc-100">{entry.title}</p>
            {entry.excerpt ? (
              <p className="mt-2 text-sm leading-6 text-zinc-400">{entry.excerpt}</p>
            ) : null}
            <p className="mt-3 text-xs text-zinc-600">
              {entry.mood ? `${entry.mood} · ` : ""}
              {entry.createdAtLabel}
            </p>
          </div>
        ))}

        {entries.length === 0 ? (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-zinc-500">
            No journal entries in this range.
          </div>
        ) : null}
      </div>
    </article>
  );
}
