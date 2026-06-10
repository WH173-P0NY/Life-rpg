import { Award, CheckCircle2, Lock, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  evaluateAchievements,
  fetchAchievements,
  unlockAchievement
} from "../api/progression";
import type { ProgressionAchievement } from "../types/progression";
import { ProgressBar } from "./ui/ProgressBar";

interface AchievementsViewProps {
  isApiReady: boolean;
  onAchievementsChanged: () => Promise<void>;
}

const rarityClass: Record<ProgressionAchievement["rarity"], string> = {
  common: "border-white/10 bg-white/[0.035] text-zinc-300",
  rare: "border-rare/30 bg-rare/10 text-rare",
  epic: "border-epic/30 bg-epic/10 text-epic",
  legendary: "border-xp/40 bg-xp/10 text-xp"
};

export function AchievementsView({
  isApiReady,
  onAchievementsChanged
}: AchievementsViewProps) {
  const [achievements, setAchievements] = useState<ProgressionAchievement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refreshAchievements = useCallback(async () => {
    if (!isApiReady) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchAchievements("all");
      setAchievements(response.achievements);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Achievements API is not available");
    } finally {
      setIsLoading(false);
    }
  }, [isApiReady]);

  useEffect(() => {
    void refreshAchievements();
  }, [refreshAchievements]);

  async function handleEvaluate() {
    if (!isApiReady || pendingId) {
      return;
    }
    setPendingId("evaluate");
    setFeedback(null);
    setErrorMessage(null);
    try {
      const response = await evaluateAchievements();
      setFeedback(
        response.achievementUnlocks.length
          ? `${response.achievementUnlocks.length} achievement unlocked`
          : "No new achievements"
      );
      await refreshAchievements();
      await onAchievementsChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Achievement evaluation failed");
    } finally {
      setPendingId(null);
    }
  }

  async function handleUnlock(achievement: ProgressionAchievement) {
    if (!isApiReady || pendingId || achievement.unlocked) {
      return;
    }
    setPendingId(achievement.id);
    setFeedback(null);
    setErrorMessage(null);
    try {
      await unlockAchievement(achievement.id);
      setFeedback(`${achievement.title} unlocked`);
      await refreshAchievements();
      await onAchievementsChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Achievement unlock failed");
    } finally {
      setPendingId(null);
    }
  }

  if (!isApiReady) {
    return (
      <article className="panel p-4">
        <p className="eyebrow">Achievements</p>
        <h2 className="mt-1 text-xl font-semibold text-zinc-50">Live API required</h2>
        <p className="mt-2 text-sm text-zinc-500">Connect Django to browse the achievement archive.</p>
      </article>
    );
  }

  return (
    <section className="space-y-4">
      <article className="panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Archive</p>
            <h2>Achievements</h2>
          </div>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={pendingId !== null}
            onClick={handleEvaluate}
            type="button"
          >
            <RefreshCw size={15} />
            Evaluate
          </button>
        </div>
        {feedback ? (
          <p className="mt-4 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success">
            {feedback}
          </p>
        ) : null}
        {errorMessage ? (
          <p className="mt-4 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">
            {errorMessage}
          </p>
        ) : null}
      </article>

      {isLoading ? (
        <article className="panel p-4 text-sm text-zinc-500">Loading achievements...</article>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {achievements.map((achievement) => (
          <article className="panel p-4" key={achievement.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-xp">
                {achievement.unlocked ? <Award size={20} /> : <Lock size={20} />}
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-xs capitalize ${rarityClass[achievement.rarity]}`}>
                {achievement.rarity}
              </span>
            </div>

            <div className="mt-4">
              <div className="flex items-center gap-2">
                <p className="font-semibold text-zinc-50">{achievement.title}</p>
                {achievement.unlocked ? <CheckCircle2 className="text-success" size={16} /> : null}
              </div>
              <p className="mt-2 text-sm leading-6 text-zinc-500">{achievement.description}</p>
            </div>

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between text-xs text-zinc-500">
                <span>
                  {achievement.progress.current} / {achievement.progress.target} {achievement.progress.unit}
                </span>
                <span>{achievement.progress.progressPercent}%</span>
              </div>
              <ProgressBar value={achievement.unlocked ? 100 : achievement.progress.progressPercent} />
            </div>

            <button
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-sm font-medium text-zinc-200 transition hover:border-xp/40 hover:text-xp disabled:cursor-not-allowed disabled:opacity-50"
              disabled={achievement.unlocked || pendingId !== null}
              onClick={() => handleUnlock(achievement)}
              type="button"
            >
              <Sparkles size={15} />
              {achievement.unlocked ? "Unlocked" : "Manual unlock"}
            </button>
          </article>
        ))}
      </div>

      {!isLoading && achievements.length === 0 ? (
        <article className="panel p-4 text-sm text-zinc-500">No achievement definitions yet.</article>
      ) : null}
    </section>
  );
}
