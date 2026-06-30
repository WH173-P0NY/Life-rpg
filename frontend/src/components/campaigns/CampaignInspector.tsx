import type { ReactNode } from "react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link2Off, RotateCcw, Save, Trash2, X } from "lucide-react";

import { useI18n } from "../../i18n";
import type { SettingsSkill } from "../../api/settings";
import type {
  CampaignNodeUpdatePayload,
  CampaignQuestUnlockMode,
  CampaignStudioEdge,
  CampaignStudioMode,
  CampaignStudioNode
} from "../../types/campaigns";
import { CampaignReadinessPanel } from "./CampaignReadinessPanel";
import type { CampaignValidationReport } from "../../types/campaigns";

interface CampaignInspectorProps {
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  nodes: CampaignStudioNode[];
  edges: CampaignStudioEdge[];
  mode: CampaignStudioMode;
  skills: SettingsSkill[];
  validation: CampaignValidationReport;
  disabled: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
  onDeleteEdge: (edgeId: string) => Promise<void>;
  onDeleteNode: (nodeId: string) => Promise<void>;
  onRequestClose?: () => void;
  onUpdateNode: (nodeId: string, payload: CampaignNodeUpdatePayload) => Promise<void>;
}

interface NodeFormState {
  title: string;
  description: string;
  stage: string;
  rewardXp: string;
  rewardSkillId: string;
  isRequired: boolean;
  unlockMode: CampaignQuestUnlockMode;
}

const unlockModes: CampaignQuestUnlockMode[] = [
  "immediate",
  "after_dependencies",
  "manual"
];

export function CampaignInspector({
  selectedNodeId,
  selectedEdgeId,
  nodes,
  edges,
  mode,
  skills,
  validation,
  disabled,
  onDirtyChange,
  onDeleteEdge,
  onDeleteNode,
  onRequestClose,
  onUpdateNode
}: CampaignInspectorProps) {
  const { t } = useI18n();
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;

  if (selectedNode) {
    return (
      <NodeInspectorDrawer
        disabled={disabled}
        edges={edges}
        mode={mode}
        node={selectedNode}
        nodes={nodes}
        onDirtyChange={onDirtyChange}
        onDeleteNode={onDeleteNode}
        onRequestClose={onRequestClose}
        onUpdateNode={onUpdateNode}
        skills={skills}
      />
    );
  }

  if (selectedEdge) {
    return (
      <EdgeInspectorDrawer
        disabled={disabled}
        edge={selectedEdge}
        mode={mode}
        nodes={nodes}
        onDeleteEdge={onDeleteEdge}
        onRequestClose={onRequestClose}
      />
    );
  }

  return <ValidationInspectorDrawer validation={validation} />;
}

export function NodeInspectorDrawer({
  disabled,
  edges,
  mode,
  node,
  nodes,
  onDirtyChange,
  onDeleteNode,
  onRequestClose,
  onUpdateNode,
  skills,
}: {
  disabled: boolean;
  edges: CampaignStudioEdge[];
  mode: CampaignStudioMode;
  node: CampaignStudioNode;
  nodes: CampaignStudioNode[];
  onDirtyChange?: (isDirty: boolean) => void;
  onDeleteNode: (nodeId: string) => Promise<void>;
  onRequestClose?: () => void;
  onUpdateNode: (nodeId: string, payload: CampaignNodeUpdatePayload) => Promise<void>;
  skills: SettingsSkill[];
}) {
  const { t } = useI18n();
  const nodeFormSnapshot = useMemo(() => formFromNode(node), [
    node.description,
    node.id,
    node.isRequired,
    node.rewardXp,
    node.rewardSkill?.id,
    node.stage,
    node.title,
    node.unlockMode
  ]);
  const [form, setForm] = useState<NodeFormState>(() => nodeFormSnapshot);
  const [savedForm, setSavedForm] = useState<NodeFormState>(() => nodeFormSnapshot);
  const isBuilder = mode === "builder";
  const canEditReward = isBuilder && skills.length > 0;
  const rewardXpValue = Number(form.rewardXp) || 0;
  const hasInvalidReward = rewardXpValue > 0 && !form.rewardSkillId;
  const isDirty = !nodeFormsEqual(form, savedForm);

  useEffect(() => {
    setForm(nodeFormSnapshot);
    setSavedForm(nodeFormSnapshot);
  }, [nodeFormSnapshot]);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => {
      onDirtyChange?.(false);
    };
  }, [isDirty, onDirtyChange]);

  const incomingNodes = useMemo(
    () =>
      edges
        .filter((edge) => edge.targetNodeId === node.id)
        .map((edge) => nodes.find((candidate) => candidate.id === edge.sourceNodeId))
        .filter((candidate): candidate is CampaignStudioNode => Boolean(candidate)),
    [edges, node.id, nodes]
  );
  const outgoingNodes = useMemo(
    () =>
      edges
        .filter((edge) => edge.sourceNodeId === node.id)
        .map((edge) => nodes.find((candidate) => candidate.id === edge.targetNodeId))
        .filter((candidate): candidate is CampaignStudioNode => Boolean(candidate)),
    [edges, node.id, nodes]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextSavedForm = normalizeNodeForm(form);
    await onUpdateNode(node.id, {
      title: nextSavedForm.title,
      description: nextSavedForm.description,
      stage: nextSavedForm.stage,
      rewardXp: Number(nextSavedForm.rewardXp),
      rewardSkillId: nextSavedForm.rewardSkillId || undefined,
      isRequired: nextSavedForm.isRequired,
      unlockMode: nextSavedForm.unlockMode
    });
    setForm(nextSavedForm);
    setSavedForm(nextSavedForm);
    onRequestClose?.();
  }

  function handleDiscard() {
    setForm(savedForm);
    onRequestClose?.();
  }

  return (
    <CampaignInspectorDrawer
      badge={t(`campaigns.state.${node.state}`)}
      eyebrow={t(`campaigns.node.${node.nodeKind}`)}
      isDirty={isDirty}
      onRequestClose={onRequestClose}
      title={t("campaigns.studio.inspector")}
    >
      <p className="mt-4 text-sm leading-6 text-zinc-500">
        {t(`campaigns.node.${node.nodeKind}.description`)}
      </p>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <label className="block">
            <span className="field-label">{t("campaigns.studio.nodeTitle")}</span>
            <input
              className="field-control"
              disabled={disabled || !isBuilder}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              value={form.title}
            />
          </label>
          <label className="block">
            <span className="field-label">{t("campaigns.studio.nodeDescription")}</span>
            <textarea
              className="field-control min-h-24 resize-none"
              disabled={disabled || !isBuilder}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              value={form.description}
            />
          </label>
          <label className="block">
            <span className="field-label">{t("campaigns.studio.stage")}</span>
            <input
              className="field-control"
              disabled={disabled || !isBuilder}
              onChange={(event) => setForm((current) => ({ ...current, stage: event.target.value }))}
              value={form.stage}
            />
          </label>
        </div>

        <div className="space-y-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <label className="block">
            <span className="field-label">{t("campaigns.studio.rewardSkill")}</span>
            <select
              className="field-control"
              disabled={disabled || !canEditReward}
              onChange={(event) =>
                setForm((current) => ({ ...current, rewardSkillId: event.target.value }))
              }
              value={form.rewardSkillId}
            >
              <option value="">{t("campaigns.studio.noRewardSkill")}</option>
              {skills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="field-label">{t("campaigns.studio.rewardXp")}</span>
            <input
              className="field-control"
              disabled={disabled || !isBuilder}
              min={0}
              onChange={(event) =>
                setForm((current) => ({ ...current, rewardXp: event.target.value }))
              }
              type="number"
              value={form.rewardXp}
            />
            {hasInvalidReward ? (
              <span className="mt-2 block text-xs leading-5 text-epic">
                {t("campaigns.studio.rewardSkillRequired")}
              </span>
            ) : !canEditReward ? (
              <span className="mt-2 block text-xs leading-5 text-zinc-500">
                {t("campaigns.studio.rewardXpReadOnlyHint")}
              </span>
            ) : null}
          </label>
        </div>

        <div className="space-y-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
          <label className="block">
            <span className="field-label">{t("campaigns.studio.unlockMode")}</span>
            <select
              className="field-control"
              disabled={disabled || !isBuilder}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  unlockMode: event.target.value as CampaignQuestUnlockMode
                }))
              }
              value={form.unlockMode}
            >
              {unlockModes.map((modeOption) => (
                <option key={modeOption} value={modeOption}>
                  {t(`campaigns.unlockMode.${modeOption}`)}
                </option>
              ))}
            </select>
            <span className="mt-2 block text-xs leading-5 text-zinc-500">
              {describeUnlockMode(form.unlockMode, incomingNodes, t)}
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-black/10 p-3">
            <input
              checked={form.isRequired}
              className="mt-1"
              disabled={disabled || !isBuilder}
              onChange={(event) =>
                setForm((current) => ({ ...current, isRequired: event.target.checked }))
              }
              type="checkbox"
            />
            <span>
              <span className="block text-sm font-semibold text-zinc-100">
                {t("campaigns.studio.requiredNode")}
              </span>
              <span className="mt-1 block text-xs leading-5 text-zinc-500">
                {t("campaigns.studio.requiredNodeDescription")}
              </span>
            </span>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            className="primary-button inline-flex items-center justify-center gap-2"
            disabled={disabled || !isBuilder || !isDirty || hasInvalidReward}
            type="submit"
          >
            <Save size={16} />
            {t("campaigns.studio.saveNode")}
          </button>
          <button
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm font-semibold text-zinc-200 transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-50"
            disabled={disabled || !isDirty}
            onClick={handleDiscard}
            type="button"
          >
            <RotateCcw size={16} />
            {t("common.cancel")}
          </button>
        </div>
      </form>

      <div className="mt-4 grid gap-3 text-sm">
        <NodeLinks title={t("campaigns.studio.lockedBy")} nodes={incomingNodes} />
        <NodeLinks title={t("campaigns.studio.unlocks")} nodes={outgoingNodes} />
      </div>

      <button
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm font-semibold text-epic transition hover:bg-epic/15 disabled:cursor-not-allowed disabled:opacity-50"
        disabled={disabled || !isBuilder}
        onClick={() => void onDeleteNode(node.id)}
        type="button"
      >
        <Trash2 size={16} />
        {t("campaigns.studio.deleteNode")}
      </button>
    </CampaignInspectorDrawer>
  );
}

export function EdgeInspectorDrawer({
  disabled,
  edge,
  mode,
  nodes,
  onDeleteEdge,
  onRequestClose
}: {
  disabled: boolean;
  edge: CampaignStudioEdge;
  mode: CampaignStudioMode;
  nodes: CampaignStudioNode[];
  onDeleteEdge: (edgeId: string) => Promise<void>;
  onRequestClose?: () => void;
}) {
  const { t } = useI18n();
  const source = nodes.find((node) => node.id === edge.sourceNodeId);
  const target = nodes.find((node) => node.id === edge.targetNodeId);
  const isBuilder = mode === "builder";

  return (
    <CampaignInspectorDrawer
      badge={t("campaigns.studio.edge")}
      eyebrow={t("campaigns.studio.connection")}
      onRequestClose={onRequestClose}
      title={t("campaigns.studio.unlockPath")}
    >
      <p className="mt-4 text-sm leading-6 text-zinc-500">
        {t("campaigns.studio.edgeDescription")}
      </p>

      <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm">
        <p className="text-zinc-500">{t("campaigns.studio.from")}</p>
        <p className="mt-1 font-semibold text-zinc-100">{source?.title ?? edge.sourceNodeId}</p>
        <p className="mt-3 text-zinc-500">{t("campaigns.studio.to")}</p>
        <p className="mt-1 font-semibold text-zinc-100">{target?.title ?? edge.targetNodeId}</p>
      </div>

      <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {t("campaigns.studio.unlockPath")}
        </p>
        <p className="mt-2 leading-6 text-zinc-200">{describeEdgeRoute(edge, source, target, t)}</p>
      </div>

      <button
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm font-semibold text-epic transition hover:bg-epic/15 disabled:cursor-not-allowed disabled:opacity-50"
        disabled={disabled || !isBuilder}
        onClick={() => void onDeleteEdge(edge.id)}
        type="button"
      >
        <Link2Off size={16} />
        {t("campaigns.studio.deleteConnection")}
      </button>
    </CampaignInspectorDrawer>
  );
}

export function ValidationInspectorDrawer({
  validation
}: {
  validation: CampaignValidationReport;
}) {
  return <CampaignReadinessPanel validation={validation} />;
}

function CampaignInspectorDrawer({
  badge,
  children,
  eyebrow,
  isDirty = false,
  onRequestClose,
  title
}: {
  badge?: string;
  children: ReactNode;
  eyebrow: string;
  isDirty?: boolean;
  onRequestClose?: () => void;
  title: string;
}) {
  const { t } = useI18n();
  const canClose = Boolean(onRequestClose) && !isDirty;

  return (
    <section className="panel overflow-hidden p-0" data-campaign-inspector-drawer>
      <div className="border-b border-white/10 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2 className="text-lg font-semibold text-zinc-50">{title}</h2>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {badge || isDirty ? (
              <span
                className={
                  isDirty
                    ? "rounded-full border border-xp/30 bg-xp/10 px-2 py-1 text-xs font-semibold text-xp"
                    : "rounded-full border border-white/10 bg-white/[0.03] px-2 py-1 text-xs font-semibold text-zinc-300"
                }
              >
                {isDirty ? t("campaigns.studio.dirty") : badge}
              </span>
            ) : null}
            {onRequestClose ? (
              <button
                aria-label={t("common.cancel")}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-zinc-300 transition hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-40"
                disabled={!canClose}
                onClick={onRequestClose}
                title={isDirty ? t("campaigns.studio.dirty") : t("common.cancel")}
                type="button"
              >
                <X size={16} />
              </button>
            ) : null}
          </div>
        </div>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function NodeLinks({ title, nodes }: { title: string; nodes: CampaignStudioNode[] }) {
  const { t } = useI18n();

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">{title}</p>
      {nodes.length ? (
        <div className="mt-2 space-y-1">
          {nodes.map((node) => (
            <p className="truncate text-sm text-zinc-200" key={node.id}>
              {node.title}
            </p>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-sm text-zinc-500">{t("campaigns.studio.noLinkedNodes")}</p>
      )}
    </div>
  );
}

function formFromNode(node: CampaignStudioNode): NodeFormState {
  return {
    title: node.title,
    description: node.description,
    stage: node.stage,
    rewardXp: String(node.rewardXp),
    rewardSkillId: node.rewardSkill?.id ?? "",
    isRequired: node.isRequired,
    unlockMode: node.unlockMode
  };
}

function normalizeNodeForm(form: NodeFormState): NodeFormState {
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    stage: form.stage.trim(),
    rewardXp: String(Number(form.rewardXp) || 0),
    rewardSkillId: form.rewardSkillId,
    isRequired: form.isRequired,
    unlockMode: form.unlockMode
  };
}

function nodeFormsEqual(left: NodeFormState, right: NodeFormState): boolean {
  return (
    left.title === right.title &&
    left.description === right.description &&
    left.stage === right.stage &&
    left.rewardXp === right.rewardXp &&
    left.rewardSkillId === right.rewardSkillId &&
    left.isRequired === right.isRequired &&
    left.unlockMode === right.unlockMode
  );
}

function describeEdgeRoute(
  edge: CampaignStudioEdge,
  source: CampaignStudioNode | undefined,
  target: CampaignStudioNode | undefined,
  t: (key: string) => string
): string {
  if (!target) {
    return `${edge.sourceNodeId} -> ${edge.targetNodeId}`;
  }

  if (target.unlockMode === "after_dependencies") {
    return `${t("campaigns.studio.unlockAfter")}: ${source?.title ?? edge.sourceNodeId}`;
  }

  return describeUnlockMode(target.unlockMode, source ? [source] : [], t);
}

function describeUnlockMode(
  unlockMode: CampaignQuestUnlockMode,
  incomingNodes: CampaignStudioNode[],
  t: (key: string) => string
) {
  if (unlockMode === "immediate") {
    return t("campaigns.studio.unlockImmediateDescription");
  }
  if (unlockMode === "manual") {
    return t("campaigns.studio.unlockManualDescription");
  }
  if (!incomingNodes.length) {
    return t("campaigns.studio.unlockNoDependencies");
  }

  return `${t("campaigns.studio.unlockAfter")}: ${incomingNodes
    .map((node) => node.title)
    .join(", ")}`;
}
