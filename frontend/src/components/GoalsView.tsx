import {
  Archive,
  CheckCircle2,
  Flag,
  Pencil,
  Plus,
  Save,
  Target,
  TimerReset,
  X
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import {
  archiveGoal,
  completeChallenge,
  completeGoal,
  createChallenge,
  createGoal,
  fetchChallenges,
  fetchGoals,
  toggleChallengeCheckIn,
  updateGoal,
  updateGoalProgress
} from "../api/progression";
import type { ProgressionChallenge, ProgressionGoal } from "../types/progression";
import { ProgressBar } from "./ui/ProgressBar";

interface GoalsViewProps {
  isApiReady: boolean;
  onProgressionChanged: () => Promise<void>;
}

type EditableGoalStatus = "draft" | "active" | "paused";

interface GoalFormState {
  title: string;
  description: string;
  status: EditableGoalStatus;
  priority: ProgressionGoal["priority"];
  targetValue: string;
  dueOn: string;
}

interface ChallengeFormState {
  title: string;
  targetValue: string;
  startDate: string;
  endDate: string;
  rewardTitle: string;
}

const fieldClassName =
  "w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-xp/50";

const editableGoalStatuses: EditableGoalStatus[] = ["draft", "active", "paused"];
const goalPriorities: ProgressionGoal["priority"][] = ["low", "normal", "high", "legendary"];

export function GoalsView({ isApiReady, onProgressionChanged }: GoalsViewProps) {
  const [goals, setGoals] = useState<ProgressionGoal[]>([]);
  const [challenges, setChallenges] = useState<ProgressionChallenge[]>([]);
  const [newGoalTitle, setNewGoalTitle] = useState("");
  const [editingGoalId, setEditingGoalId] = useState<string | null>(null);
  const [goalForm, setGoalForm] = useState<GoalFormState | null>(null);
  const [challengeForm, setChallengeForm] = useState<ChallengeFormState>(() =>
    defaultChallengeForm()
  );
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeChallenge = useMemo(
    () => challenges.find((challenge) => challenge.status === "active") ?? null,
    [challenges]
  );

  const refreshProgression = useCallback(async () => {
    if (!isApiReady) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [goalsResponse, challengesResponse] = await Promise.all([
        fetchGoals("all"),
        fetchChallenges("all")
      ]);
      setGoals(goalsResponse.goals);
      setChallenges(challengesResponse.challenges);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Progression API is not available");
    } finally {
      setIsLoading(false);
    }
  }, [isApiReady]);

  useEffect(() => {
    void refreshProgression();
  }, [refreshProgression]);

  async function handleCreateGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newGoalTitle.trim() || !isApiReady) {
      return;
    }

    setPendingId("create-goal");
    setErrorMessage(null);
    try {
      await createGoal({
        title: newGoalTitle,
        status: "active",
        priority: "normal",
        targetValue: 100,
        targetUnit: "count"
      });
      setNewGoalTitle("");
      await refreshProgression();
      await onProgressionChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create goal");
    } finally {
      setPendingId(null);
    }
  }

  function startGoalEdit(goal: ProgressionGoal) {
    if (goal.status === "completed" || goal.status === "archived") {
      return;
    }
    setEditingGoalId(goal.id);
    setGoalForm({
      title: goal.title,
      description: goal.description,
      status: normalizeEditableGoalStatus(goal.status),
      priority: goal.priority,
      targetValue: String(goal.targetValue),
      dueOn: goal.dueOn ?? ""
    });
    setErrorMessage(null);
  }

  function updateGoalForm<K extends keyof GoalFormState>(field: K, value: GoalFormState[K]) {
    setGoalForm((current) => (current ? { ...current, [field]: value } : current));
  }

  async function handleUpdateGoal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingGoalId || !goalForm || !isApiReady || pendingId) {
      return;
    }

    const targetValue = Number(goalForm.targetValue);
    if (!goalForm.title.trim()) {
      setErrorMessage("Goal title is required");
      return;
    }
    if (!Number.isFinite(targetValue) || targetValue <= 0) {
      setErrorMessage("Goal target must be greater than zero");
      return;
    }

    setPendingId(`edit-${editingGoalId}`);
    setErrorMessage(null);
    try {
      await updateGoal(editingGoalId, {
        title: goalForm.title.trim(),
        description: goalForm.description.trim(),
        status: goalForm.status,
        priority: goalForm.priority,
        targetValue,
        dueOn: goalForm.dueOn || undefined
      });
      setEditingGoalId(null);
      setGoalForm(null);
      await refreshProgression();
      await onProgressionChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not update goal");
    } finally {
      setPendingId(null);
    }
  }

  async function mutateGoal(goal: ProgressionGoal, action: "advance" | "complete" | "archive") {
    if (!isApiReady || pendingId) {
      return;
    }
    setPendingId(`${action}-${goal.id}`);
    setErrorMessage(null);
    try {
      if (action === "advance") {
        await updateGoalProgress(goal.id, Math.min(goal.progressValue + 1, goal.targetValue));
      } else if (action === "complete") {
        await completeGoal(goal.id);
      } else {
        await archiveGoal(goal.id);
      }
      await refreshProgression();
      await onProgressionChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Goal mutation failed");
    } finally {
      setPendingId(null);
    }
  }

  function updateChallengeForm<K extends keyof ChallengeFormState>(
    field: K,
    value: ChallengeFormState[K]
  ) {
    setChallengeForm((current) => ({ ...current, [field]: value }));
  }

  async function handleCreateChallenge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isApiReady || pendingId) {
      return;
    }

    const targetValue = Number(challengeForm.targetValue);
    if (!challengeForm.title.trim()) {
      setErrorMessage("Challenge title is required");
      return;
    }
    if (!Number.isFinite(targetValue) || targetValue <= 0) {
      setErrorMessage("Challenge target must be greater than zero");
      return;
    }
    if (!challengeForm.startDate || !challengeForm.endDate) {
      setErrorMessage("Challenge start and end dates are required");
      return;
    }
    if (challengeForm.endDate < challengeForm.startDate) {
      setErrorMessage("Challenge end date cannot be before start date");
      return;
    }

    setPendingId("create-challenge");
    setErrorMessage(null);
    try {
      await createChallenge({
        title: challengeForm.title.trim(),
        status: "active",
        targetValue,
        targetUnit: "check",
        startDate: challengeForm.startDate,
        endDate: challengeForm.endDate,
        rewardTitle: challengeForm.rewardTitle.trim()
      });
      setChallengeForm(defaultChallengeForm());
      await refreshProgression();
      await onProgressionChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Could not create challenge");
    } finally {
      setPendingId(null);
    }
  }

  async function mutateChallenge(action: "toggle" | "complete") {
    if (!activeChallenge || !isApiReady || pendingId) {
      return;
    }
    setPendingId(`${action}-${activeChallenge.id}`);
    setErrorMessage(null);
    try {
      if (action === "toggle") {
        await toggleChallengeCheckIn(activeChallenge.id);
      } else {
        await completeChallenge(activeChallenge.id);
      }
      await refreshProgression();
      await onProgressionChanged();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Challenge mutation failed");
    } finally {
      setPendingId(null);
    }
  }

  if (!isApiReady) {
    return (
      <article className="panel p-4">
        <p className="eyebrow">Progression</p>
        <h2 className="mt-1 text-xl font-semibold text-zinc-50">Goals require live API</h2>
        <p className="mt-2 text-sm text-zinc-500">Connect Django to manage long-term goals.</p>
      </article>
    );
  }

  return (
    <section className="grid gap-4 xl:grid-cols-[1fr_0.85fr]">
      <div className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Direction</p>
              <h2>Long-Term Goals</h2>
            </div>
            <span>{goals.filter((goal) => goal.status === "active").length} active</span>
          </div>

          <form className="mt-4 flex gap-3" onSubmit={handleCreateGoal}>
            <input
              className="min-w-0 flex-1 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-xp/50"
              onChange={(event) => setNewGoalTitle(event.target.value)}
              placeholder="New goal"
              value={newGoalTitle}
            />
            <button
              className="inline-flex items-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pendingId !== null || !newGoalTitle.trim()}
              type="submit"
            >
              <Plus size={16} />
              Add
            </button>
          </form>

          {errorMessage ? (
            <p className="mt-4 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm text-epic">
              {errorMessage}
            </p>
          ) : null}
        </article>

        {isLoading ? (
          <article className="panel p-4 text-sm text-zinc-500">Loading goals...</article>
        ) : null}

        {goals.map((goal) => (
          <article className="panel p-4" key={goal.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Target className="text-xp" size={17} />
                  <p className="font-semibold text-zinc-50">{goal.title}</p>
                </div>
                <p className="mt-2 text-sm text-zinc-500">{goal.description || "No description"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs capitalize text-zinc-400">
                  {goal.status}
                </span>
                <span className="rounded-full border border-xp/20 bg-xp/5 px-2.5 py-1 text-xs capitalize text-xp">
                  {goal.priority}
                </span>
              </div>
            </div>

            {editingGoalId === goal.id && goalForm ? (
              <form className="mt-4 rounded-lg border border-white/10 bg-white/[0.025] p-3" onSubmit={handleUpdateGoal}>
                <div className="grid gap-3 md:grid-cols-2">
                  <FormField label="Title">
                    <input
                      className={fieldClassName}
                      onChange={(event) => updateGoalForm("title", event.target.value)}
                      value={goalForm.title}
                    />
                  </FormField>
                  <FormField label="Target">
                    <input
                      className={fieldClassName}
                      min={1}
                      onChange={(event) => updateGoalForm("targetValue", event.target.value)}
                      type="number"
                      value={goalForm.targetValue}
                    />
                  </FormField>
                  <FormField label="Status">
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        updateGoalForm("status", event.target.value as EditableGoalStatus)
                      }
                      value={goalForm.status}
                    >
                      {editableGoalStatuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Priority">
                    <select
                      className={fieldClassName}
                      onChange={(event) =>
                        updateGoalForm(
                          "priority",
                          event.target.value as ProgressionGoal["priority"]
                        )
                      }
                      value={goalForm.priority}
                    >
                      {goalPriorities.map((priority) => (
                        <option key={priority} value={priority}>
                          {priority}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Due date">
                    <input
                      className={fieldClassName}
                      onChange={(event) => updateGoalForm("dueOn", event.target.value)}
                      type="date"
                      value={goalForm.dueOn}
                    />
                  </FormField>
                  <FormField label="Description">
                    <textarea
                      className={`${fieldClassName} min-h-20 resize-none`}
                      onChange={(event) => updateGoalForm("description", event.target.value)}
                      value={goalForm.description}
                    />
                  </FormField>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="inline-flex items-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={pendingId !== null}
                    type="submit"
                  >
                    <Save size={15} />
                    Save
                  </button>
                  <button
                    className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-sm font-medium text-zinc-200 transition hover:border-white/20 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={pendingId !== null}
                    onClick={() => {
                      setEditingGoalId(null);
                      setGoalForm(null);
                    }}
                    type="button"
                  >
                    <X size={15} />
                    Cancel
                  </button>
                </div>
              </form>
            ) : null}

            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between text-xs text-zinc-500">
                <span>
                  {goal.progressValue} / {goal.targetValue} {goal.targetUnit}
                </span>
                <span>{goal.progressPercent}%</span>
              </div>
              <ProgressBar value={goal.progressPercent} />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {goal.linkedSkills.map((skill) => (
                <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-zinc-400" key={skill.id}>
                  {skill.name}
                </span>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <ActionButton
                disabled={
                  goal.status === "completed" || goal.status === "archived" || pendingId !== null
                }
                icon={<Pencil size={15} />}
                label="Edit"
                onClick={() => startGoalEdit(goal)}
              />
              <ActionButton
                disabled={goal.status !== "active" || pendingId !== null}
                icon={<Plus size={15} />}
                label="Advance"
                onClick={() => mutateGoal(goal, "advance")}
              />
              <ActionButton
                disabled={goal.status === "completed" || goal.status === "archived" || pendingId !== null}
                icon={<CheckCircle2 size={15} />}
                label="Complete"
                onClick={() => mutateGoal(goal, "complete")}
              />
              <ActionButton
                disabled={goal.status === "archived" || pendingId !== null}
                icon={<Archive size={15} />}
                label="Archive"
                onClick={() => mutateGoal(goal, "archive")}
              />
            </div>
          </article>
        ))}

        {!isLoading && goals.length === 0 ? (
          <article className="panel p-4 text-sm text-zinc-500">No long-term goals defined yet.</article>
        ) : null}
      </div>

      <aside className="space-y-4">
        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Long game</p>
              <h2>Active Challenge</h2>
            </div>
            <span>{activeChallenge ? `${activeChallenge.progressPercent}%` : "Idle"}</span>
          </div>

          {activeChallenge ? (
            <div className="mt-4">
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg border border-xp/30 bg-xp/10 text-xp">
                  <TimerReset size={18} />
                </div>
                <div>
                  <p className="font-semibold text-zinc-50">{activeChallenge.title}</p>
                  <p className="mt-1 text-sm text-zinc-500">
                    {activeChallenge.currentValue} / {activeChallenge.targetValue} {activeChallenge.targetUnit}
                  </p>
                </div>
              </div>
              <ProgressBar className="mt-4" value={activeChallenge.progressPercent} />
              <p className="mt-4 rounded-lg border border-rare/30 bg-rare/10 px-3 py-2 text-sm text-rare">
                {activeChallenge.rewardTitle || `+${activeChallenge.rewardXp} XP`}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <ActionButton
                  disabled={pendingId !== null}
                  icon={<Flag size={15} />}
                  label="Check in"
                  onClick={() => mutateChallenge("toggle")}
                />
                <ActionButton
                  disabled={pendingId !== null}
                  icon={<CheckCircle2 size={15} />}
                  label="Complete"
                  onClick={() => mutateChallenge("complete")}
                />
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-zinc-500">No active challenge.</p>
          )}
        </article>

        <article className="panel p-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Contract</p>
              <h2>Create Challenge</h2>
            </div>
            <span>Active</span>
          </div>

          <form className="mt-4 grid gap-3" onSubmit={handleCreateChallenge}>
            <FormField label="Title">
              <input
                className={fieldClassName}
                onChange={(event) => updateChallengeForm("title", event.target.value)}
                placeholder="30 Days No Sugar"
                value={challengeForm.title}
              />
            </FormField>
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField label="Target">
                <input
                  className={fieldClassName}
                  min={1}
                  onChange={(event) => updateChallengeForm("targetValue", event.target.value)}
                  type="number"
                  value={challengeForm.targetValue}
                />
              </FormField>
              <FormField label="Reward">
                <input
                  className={fieldClassName}
                  onChange={(event) => updateChallengeForm("rewardTitle", event.target.value)}
                  placeholder="Epic Willpower Badge"
                  value={challengeForm.rewardTitle}
                />
              </FormField>
              <FormField label="Start">
                <input
                  className={fieldClassName}
                  onChange={(event) => updateChallengeForm("startDate", event.target.value)}
                  type="date"
                  value={challengeForm.startDate}
                />
              </FormField>
              <FormField label="End">
                <input
                  className={fieldClassName}
                  onChange={(event) => updateChallengeForm("endDate", event.target.value)}
                  type="date"
                  value={challengeForm.endDate}
                />
              </FormField>
            </div>

            <button
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-xp/40 bg-xp/10 px-3 py-2 text-sm font-semibold text-xp transition hover:bg-xp/15 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={
                pendingId !== null ||
                !challengeForm.title.trim() ||
                !challengeForm.startDate ||
                !challengeForm.endDate
              }
              type="submit"
            >
              <Plus size={16} />
              Create Challenge
            </button>
          </form>
        </article>
      </aside>
    </section>
  );
}

interface ActionButtonProps {
  disabled: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}

function ActionButton({ disabled, icon, label, onClick }: ActionButtonProps) {
  return (
    <button
      className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-sm font-medium text-zinc-200 transition hover:border-xp/40 hover:text-xp disabled:cursor-not-allowed disabled:opacity-50"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {icon}
      {label}
    </button>
  );
}

interface FormFieldProps {
  children: ReactNode;
  label: string;
}

function FormField({ children, label }: FormFieldProps) {
  return (
    <label className="grid gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">
      <span>{label}</span>
      {children}
    </label>
  );
}

function normalizeEditableGoalStatus(status: ProgressionGoal["status"]): EditableGoalStatus {
  return editableGoalStatuses.includes(status as EditableGoalStatus)
    ? (status as EditableGoalStatus)
    : "active";
}

function defaultChallengeForm(): ChallengeFormState {
  const startDate = new Date();
  const endDate = addDays(startDate, 29);
  return {
    title: "",
    targetValue: "30",
    startDate: dateInputValue(startDate),
    endDate: dateInputValue(endDate),
    rewardTitle: ""
  };
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function dateInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
