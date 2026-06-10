import { Check } from "lucide-react";
import { useState } from "react";

import { completeQuest } from "../api/dashboard";
import { useI18n } from "../i18n";
import type { DailyQuest } from "../types/dashboard";
import { ProgressBar } from "./ui/ProgressBar";

interface QuestsPanelProps {
  quests: DailyQuest[];
  isApiReady: boolean;
  onQuestChanged: () => Promise<void>;
}

export function QuestsPanel({ quests, isApiReady, onQuestChanged }: QuestsPanelProps) {
  const { t } = useI18n();
  const [pendingQuestId, setPendingQuestId] = useState<string | null>(null);
  const [lastReward, setLastReward] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleQuestClick(quest: DailyQuest) {
    if (quest.completed || pendingQuestId) {
      return;
    }
    if (!isApiReady) {
      setErrorMessage(t("panel.questApiRequired"));
      return;
    }

    setPendingQuestId(quest.id);
    setErrorMessage(null);
    setLastReward(null);

    try {
      const response = await completeQuest(quest.id);
      const xpReward =
        response.xpEvents.reduce((total, event) => total + event.amount, 0) ||
        response.quest.rewardXp ||
        quest.reward.xp;
      setLastReward(`+${xpReward} XP`);
      window.setTimeout(() => setLastReward(null), 1200);
      await onQuestChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("panel.questApiUnavailable"));
    } finally {
      setPendingQuestId(null);
    }
  }

  return (
    <article className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("panel.retention")}</p>
          <h2>{t("panel.todayQuests")}</h2>
        </div>
        <span>{quests.filter((quest) => quest.completed).length}/{quests.length}</span>
      </div>

      <div className="relative mt-4 space-y-3">
        {lastReward ? <div className="reward-float">{lastReward}</div> : null}
        {errorMessage ? <p className="rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">{errorMessage}</p> : null}

        {quests.map((quest) => (
          <button
            className={`quest-row w-full rounded-lg border p-3 text-left transition ${
              quest.completed
                ? "cursor-default border-success/40 bg-success/10"
                : !isApiReady
                  ? "cursor-not-allowed border-white/10 bg-white/[0.025] opacity-70"
                : "border-white/10 bg-white/[0.03] hover:border-xp/40 hover:bg-xp/5"
            }`}
            disabled={quest.completed || pendingQuestId !== null || !isApiReady}
            key={quest.id}
            onClick={() => handleQuestClick(quest)}
            type="button"
          >
            <div className="flex items-center gap-3">
              <span
                className={`grid h-6 w-6 place-items-center rounded-md border ${
                  quest.completed ? "border-success bg-success text-background" : "border-white/20"
                }`}
              >
                {quest.completed ? <Check size={15} /> : null}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium text-zinc-100">{quest.title}</p>
                  <span className="shrink-0 text-sm font-semibold text-xp">
                    {pendingQuestId === quest.id ? t("common.saving") : `+${quest.reward.xp} XP`}
                  </span>
                </div>
                <p className="mt-1 text-xs text-zinc-500">
                  {quest.progressValue} / {quest.targetValue} {quest.unit}
                </p>
              </div>
            </div>
            <ProgressBar className="mt-3 h-2" value={quest.progressPercent} />
          </button>
        ))}
      </div>
    </article>
  );
}
