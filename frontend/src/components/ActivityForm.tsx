import { Pause, Play, RotateCcw, Save } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { createManualActivity } from "../api/dashboard";
import { useI18n } from "../i18n";
import type { ActivityDefinitionOption } from "../types/dashboard";

interface ActivityFormProps {
  activityDefinitions: ActivityDefinitionOption[];
  onActivityCreated: () => Promise<void>;
}

interface StoredActivityTimer {
  activityDefinitionId: string;
  source: string;
  timerStartedAt: string | null;
  accumulatedSeconds: number;
  isTimerRunning: boolean;
  lastTickAt: number | null;
}

const timerStorageKey = "life-rpg-active-activity-timer";

function loadStoredTimer(): StoredActivityTimer | null {
  try {
    const rawValue = window.localStorage.getItem(timerStorageKey);
    if (!rawValue) {
      return null;
    }
    const parsed = JSON.parse(rawValue) as Partial<StoredActivityTimer>;
    return {
      activityDefinitionId: parsed.activityDefinitionId ?? "",
      source: parsed.source ?? "React dashboard",
      timerStartedAt: parsed.timerStartedAt ?? null,
      accumulatedSeconds: parsed.accumulatedSeconds ?? 0,
      isTimerRunning: parsed.isTimerRunning ?? false,
      lastTickAt: parsed.lastTickAt ?? null
    };
  } catch {
    return null;
  }
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

function toLocalMinuteValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function ActivityForm({ activityDefinitions, onActivityCreated }: ActivityFormProps) {
  const { t } = useI18n();
  const storedTimer = useMemo(() => loadStoredTimer(), []);
  const firstActivityId = activityDefinitions[0]?.id ?? "";
  const [activityDefinitionId, setActivityDefinitionId] = useState(
    storedTimer?.activityDefinitionId || firstActivityId
  );
  const [minutes, setMinutes] = useState(activityDefinitions[0]?.defaultMinutes ?? 30);
  const [source, setSource] = useState(storedTimer?.source ?? "React dashboard");
  const [timerStartedAt, setTimerStartedAt] = useState<string | null>(
    storedTimer?.timerStartedAt ?? null
  );
  const [accumulatedSeconds, setAccumulatedSeconds] = useState(
    storedTimer?.accumulatedSeconds ?? 0
  );
  const [isTimerRunning, setIsTimerRunning] = useState(
    storedTimer?.isTimerRunning ?? false
  );
  const [lastTickAt, setLastTickAt] = useState<number | null>(
    storedTimer?.lastTickAt ?? null
  );
  const [nowMs, setNowMs] = useState(Date.now());
  const [status, setStatus] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const elapsedSeconds = useMemo(() => {
    if (!isTimerRunning || !lastTickAt) {
      return accumulatedSeconds;
    }
    return accumulatedSeconds + Math.max(0, Math.floor((nowMs - lastTickAt) / 1000));
  }, [accumulatedSeconds, isTimerRunning, lastTickAt, nowMs]);
  const countedMinutes = Math.max(1, Math.ceil(elapsedSeconds / 60));
  const hasActiveTimer = Boolean(timerStartedAt || elapsedSeconds > 0);

  const selectedActivity = useMemo(
    () => activityDefinitions.find((activity) => activity.id === activityDefinitionId),
    [activityDefinitionId, activityDefinitions]
  );

  useEffect(() => {
    if (activityDefinitions.length === 0) {
      setActivityDefinitionId("");
      return;
    }

    if (!activityDefinitions.some((activity) => activity.id === activityDefinitionId)) {
      setActivityDefinitionId(activityDefinitions[0].id);
      setMinutes(activityDefinitions[0].defaultMinutes);
    }
  }, [activityDefinitionId, activityDefinitions]);

  useEffect(() => {
    if (!isTimerRunning) {
      return;
    }
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [isTimerRunning]);

  useEffect(() => {
    if (!hasActiveTimer) {
      window.localStorage.removeItem(timerStorageKey);
      return;
    }

    window.localStorage.setItem(
      timerStorageKey,
      JSON.stringify({
        activityDefinitionId,
        source,
        timerStartedAt,
        accumulatedSeconds,
        isTimerRunning,
        lastTickAt
      } satisfies StoredActivityTimer)
    );
  }, [
    activityDefinitionId,
    source,
    timerStartedAt,
    accumulatedSeconds,
    isTimerRunning,
    lastTickAt,
    hasActiveTimer
  ]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus(null);

    try {
      await createManualActivity({
        activityDefinitionId,
        minutes,
        source,
        startedAt: new Date().toISOString().slice(0, 16)
      });
      await onActivityCreated();
      setStatus(t("panel.activitySaved"));
    } catch {
      setStatus(t("panel.manualActivityApiUnavailable"));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleStartTimer() {
    if (!activityDefinitionId) {
      setStatus(t("panel.timerNeedsActivity"));
      return;
    }

    const now = Date.now();
    setTimerStartedAt((current) => current ?? new Date(now).toISOString());
    setLastTickAt(now);
    setNowMs(now);
    setIsTimerRunning(true);
    setStatus(null);
  }

  function handlePauseTimer() {
    setAccumulatedSeconds(elapsedSeconds);
    setLastTickAt(null);
    setIsTimerRunning(false);
  }

  function handleResetTimer() {
    setTimerStartedAt(null);
    setAccumulatedSeconds(0);
    setLastTickAt(null);
    setNowMs(Date.now());
    setIsTimerRunning(false);
  }

  async function handleSaveTimer() {
    if (!activityDefinitionId || elapsedSeconds <= 0) {
      return;
    }

    setIsSubmitting(true);
    setStatus(null);
    setAccumulatedSeconds(elapsedSeconds);
    setLastTickAt(null);
    setIsTimerRunning(false);

    try {
      await createManualActivity({
        activityDefinitionId,
        minutes: countedMinutes,
        source,
        startedAt: timerStartedAt
          ? toLocalMinuteValue(new Date(timerStartedAt))
          : toLocalMinuteValue(new Date())
      });
      setMinutes(countedMinutes);
      handleResetTimer();
      await onActivityCreated();
      setStatus(t("panel.timerSaved"));
    } catch {
      setStatus(t("panel.manualActivityApiUnavailable"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.manualInput")}</p>
          <h2>{t("panel.addActivity")}</h2>
        </div>
        <span>{selectedActivity?.name ?? t("panel.activity")}</span>
      </div>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="field-label">
          {t("panel.activity")}
          <select
            className="field-control"
            disabled={hasActiveTimer || isSubmitting}
            value={activityDefinitionId}
            onChange={(event) => {
              const nextId = event.target.value;
              const nextActivity = activityDefinitions.find((activity) => activity.id === nextId);
              setActivityDefinitionId(nextId);
              setMinutes(nextActivity?.defaultMinutes ?? minutes);
            }}
          >
            {activityDefinitions.map((activity) => (
              <option key={activity.id} value={activity.id}>
                {activity.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field-label">
          {t("panel.minutes")}
          <input
            className="field-control"
            min={1}
            type="number"
            value={minutes}
            onChange={(event) => setMinutes(Number(event.target.value))}
          />
        </label>

        <label className="field-label">
          {t("panel.source")}
          <input
            className="field-control"
            disabled={hasActiveTimer || isSubmitting}
            maxLength={240}
            type="text"
            value={source}
            onChange={(event) => setSource(event.target.value)}
          />
        </label>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="eyebrow">{t("panel.timer")}</p>
              <p className="text-xs text-zinc-500">
                {isTimerRunning
                  ? t("panel.timerRunning")
                  : hasActiveTimer
                    ? t("panel.timerPaused")
                    : t("panel.timerIdle")}
              </p>
            </div>
            <span className="rounded-md border border-white/10 px-2 py-1 text-xs text-zinc-500">
              {t("panel.countedMinutes")}: {countedMinutes}
            </span>
          </div>
          <p className="mt-3 font-mono text-4xl font-semibold tabular-nums text-zinc-50">
            {formatDuration(elapsedSeconds)}
          </p>
          <p className="mt-1 text-xs text-zinc-500">{t("panel.elapsed")}</p>

          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting || !activityDefinitionId}
              onClick={isTimerRunning ? handlePauseTimer : handleStartTimer}
              type="button"
            >
              {isTimerRunning ? <Pause size={15} /> : <Play size={15} />}
              {isTimerRunning
                ? t("panel.pauseTimer")
                : hasActiveTimer
                  ? t("panel.resumeTimer")
                  : t("panel.startTimer")}
            </button>
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-xp/40 hover:text-xp disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting || !hasActiveTimer}
              onClick={handleResetTimer}
              type="button"
            >
              <RotateCcw size={15} />
              {t("panel.resetTimer")}
            </button>
            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm font-semibold text-success transition hover:bg-success/15 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting || elapsedSeconds <= 0 || !activityDefinitionId}
              onClick={handleSaveTimer}
              type="button"
            >
              <Save size={15} />
              {t("panel.saveTimer")}
            </button>
          </div>
        </div>

        <button className="primary-button" disabled={isSubmitting || !activityDefinitionId} type="submit">
          {isSubmitting ? t("common.saving") : t("panel.addActivity")}
        </button>
      </form>

      {status ? <p className="mt-4 text-sm text-zinc-500">{status}</p> : null}
    </article>
  );
}
