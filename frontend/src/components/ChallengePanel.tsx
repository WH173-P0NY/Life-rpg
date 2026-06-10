import { CheckCircle2, Flag, Medal, TimerReset } from "lucide-react";
import { useState } from "react";

import { completeChallenge, toggleChallengeCheckIn } from "../api/progression";
import type { ActiveChallenge } from "../types/dashboard";
import { ProgressBar } from "./ui/ProgressBar";

interface ChallengePanelProps {
  challenge: ActiveChallenge | null;
  isApiReady?: boolean;
  onChallengeChanged?: () => Promise<void>;
}

export function ChallengePanel({
  challenge,
  isApiReady = false,
  onChallengeChanged
}: ChallengePanelProps) {
  const [pendingAction, setPendingAction] = useState<"toggle" | "complete" | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function mutateChallenge(action: "toggle" | "complete") {
    if (!challenge || pendingAction) {
      return;
    }
    if (!isApiReady) {
      setErrorMessage("Challenge actions require the live Django API.");
      return;
    }

    setPendingAction(action);
    setFeedback(null);
    setErrorMessage(null);
    try {
      const response =
        action === "toggle"
          ? await toggleChallengeCheckIn(challenge.id)
          : await completeChallenge(challenge.id);
      if (action === "toggle") {
        setFeedback(response.checked ? "Challenge checked" : "Challenge unchecked");
      } else {
        const xpReward = response.xpEvents.reduce((total, event) => total + event.amount, 0);
        setFeedback(xpReward > 0 ? `Completed +${xpReward} XP` : "Challenge completed");
      }
      window.setTimeout(() => setFeedback(null), 1600);
      await onChallengeChanged?.();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Challenge API is not available");
    } finally {
      setPendingAction(null);
    }
  }

  if (!challenge) {
    return (
      <article className="panel challenge-panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Long game</p>
            <h2>Active Challenge</h2>
          </div>
          <span>Idle</span>
        </div>

        <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-base font-semibold text-zinc-50">No active challenge</p>
              <p className="mt-1 text-sm text-zinc-500">Long-term focus is clear.</p>
            </div>
            <div className="grid h-11 w-11 place-items-center rounded-lg border border-white/10 bg-white/[0.04] text-zinc-500">
              <TimerReset size={20} />
            </div>
          </div>

        <ProgressBar className="mt-5 h-2.5" value={0} />
      </div>
    </article>
    );
  }

  return (
    <article className="panel challenge-panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Long game</p>
          <h2>Active Challenge</h2>
        </div>
        <span>{Math.round(challenge.progressPercent)}%</span>
      </div>

      <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.035] p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-base font-semibold text-zinc-50">{challenge.title}</p>
            <p className="mt-1 text-sm text-zinc-500">
              {challenge.currentValue ?? challenge.day} / {challenge.targetValue ?? challenge.totalDays}{" "}
              {challenge.targetUnit ?? "days"}
            </p>
          </div>
          <div className="grid h-11 w-11 place-items-center rounded-lg border border-xp/30 bg-xp/10 text-xp">
            <TimerReset size={20} />
          </div>
        </div>

        <ProgressBar className="mt-5 h-2.5" value={challenge.progressPercent} />

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

        <div className="mt-5 flex items-center gap-3 rounded-lg border border-rare/30 bg-rare/10 p-3">
          <Medal className="text-rare" size={18} />
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Reward preview</p>
            <p className="text-sm font-semibold text-zinc-100">{challenge.rewardLabel}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-sm font-medium text-zinc-200 transition hover:border-xp/40 hover:text-xp disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!isApiReady || pendingAction !== null || challenge.status === "completed"}
            onClick={() => mutateChallenge("toggle")}
            type="button"
          >
            <Flag size={15} />
            {pendingAction === "toggle" ? "Saving..." : "Check in"}
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!isApiReady || pendingAction !== null || challenge.status === "completed"}
            onClick={() => mutateChallenge("complete")}
            type="button"
          >
            <CheckCircle2 size={15} />
            {pendingAction === "complete" ? "Saving..." : "Complete"}
          </button>
        </div>
      </div>
    </article>
  );
}
