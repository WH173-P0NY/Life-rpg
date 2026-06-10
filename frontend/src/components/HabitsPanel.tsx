import { Check } from "lucide-react";
import { useState } from "react";

import { toggleHabit as toggleHabitRequest } from "../api/dashboard";
import { useI18n } from "../i18n";
import type { Habit, HabitsSummary } from "../types/dashboard";

interface HabitsPanelProps {
  habits: Habit[];
  summary: HabitsSummary;
  isApiReady: boolean;
  onHabitChanged: () => Promise<void>;
}

export function HabitsPanel({ habits, summary, isApiReady, onHabitChanged }: HabitsPanelProps) {
  const { t } = useI18n();
  const [pendingHabitId, setPendingHabitId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleHabitClick(habit: Habit) {
    if (pendingHabitId) {
      return;
    }
    if (!isApiReady) {
      setErrorMessage(t("panel.habitApiRequired"));
      return;
    }

    setPendingHabitId(habit.id);
    setFeedback(null);
    setErrorMessage(null);

    try {
      const response = await toggleHabitRequest(habit.id);
      const xpReward = response.xpEvents.reduce((total, event) => total + event.amount, 0);
      const milestoneTitle = response.milestoneUnlocks[0]?.title;

      if (response.habit.completedToday) {
        const rewardText = xpReward > 0 ? ` +${xpReward} XP` : "";
        const milestoneText = milestoneTitle ? ` - ${milestoneTitle}` : "";
        setFeedback(`${t("panel.checked")}${rewardText}${milestoneText}`);
      } else {
        setFeedback(t("panel.unchecked"));
      }

      window.setTimeout(() => setFeedback(null), 1600);
      await onHabitChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("panel.habitApiUnavailable"));
    } finally {
      setPendingHabitId(null);
    }
  }

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.dailyRhythm")}</p>
          <h2>{t("panel.habits")}</h2>
        </div>
        <span>{summary.streakDays} {t("panel.dayStreak")}</span>
      </div>

      <div className="mt-5">
        <p className="text-3xl font-semibold text-zinc-50">
          {summary.completed}/{summary.total}
        </p>
        <p className="text-sm text-zinc-500">{t("panel.completedToday")}</p>
      </div>

      {feedback ? <p className="mt-4 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">{feedback}</p> : null}
      {errorMessage ? <p className="mt-4 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">{errorMessage}</p> : null}

      <div className="mt-5 flex gap-2">
        {habits.map((habit) => (
          <span
            aria-label={habit.name}
            className={`habit-orb ${habit.completedToday ? "habit-orb-complete" : ""}`}
            key={`orb-${habit.id}`}
            title={habit.name}
          >
            {habit.completedToday ? <Check size={13} /> : null}
          </span>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        {habits.map((habit) => (
          <button
            className={`rounded-lg border p-3 text-left transition ${
              habit.completedToday
                ? "border-success/40 bg-success/10"
                : !isApiReady
                  ? "cursor-not-allowed border-white/10 bg-white/[0.025] opacity-70"
                : "border-white/10 bg-white/[0.03] hover:border-xp/40"
            }`}
            disabled={pendingHabitId !== null || !isApiReady}
            key={habit.id}
            onClick={() => handleHabitClick(habit)}
            type="button"
          >
            <span className={`mb-3 block h-3 w-3 rounded-full ${habit.completedToday ? "bg-success" : "bg-zinc-700"}`} />
            <p className="text-sm font-medium text-zinc-100">{habit.name}</p>
            <p className="mt-1 text-xs text-zinc-500">
              {pendingHabitId === habit.id ? t("common.saving") : `${habit.streakDays} ${t("panel.dayStreak")}`}
            </p>
            {habit.nextMilestone ? (
              <p className="mt-2 text-xs text-xp">
                {habit.nextMilestone.remainingDays} {t("panel.daysTo")} {habit.nextMilestone.title}
              </p>
            ) : null}
          </button>
        ))}
      </div>
    </article>
  );
}
