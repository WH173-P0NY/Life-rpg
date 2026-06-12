import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link2Off, Save, Trash2 } from "lucide-react";

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
  onDeleteEdge: (edgeId: string) => Promise<void>;
  onDeleteNode: (nodeId: string) => Promise<void>;
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
  onDeleteEdge,
  onDeleteNode,
  onUpdateNode
}: CampaignInspectorProps) {
  const { t } = useI18n();
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((edge) => edge.id === selectedEdgeId) ?? null;

  if (selectedNode) {
    return (
      <NodeInspector
        disabled={disabled}
        edges={edges}
        mode={mode}
        node={selectedNode}
        nodes={nodes}
        onDeleteNode={onDeleteNode}
        onUpdateNode={onUpdateNode}
        skills={skills}
      />
    );
  }

  if (selectedEdge) {
    const source = nodes.find((node) => node.id === selectedEdge.sourceNodeId);
    const target = nodes.find((node) => node.id === selectedEdge.targetNodeId);

    return (
      <section className="panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{t("campaigns.studio.connection")}</p>
            <h2>{t("campaigns.studio.unlockPath")}</h2>
          </div>
          <span>{t("campaigns.studio.edge")}</span>
        </div>
        <p className="mt-4 text-sm leading-6 text-zinc-500">
          {t("campaigns.studio.edgeDescription")}
        </p>
        <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm">
          <p className="text-zinc-500">{t("campaigns.studio.from")}</p>
          <p className="mt-1 font-semibold text-zinc-100">{source?.title ?? selectedEdge.sourceNodeId}</p>
          <p className="mt-3 text-zinc-500">{t("campaigns.studio.to")}</p>
          <p className="mt-1 font-semibold text-zinc-100">{target?.title ?? selectedEdge.targetNodeId}</p>
        </div>
        <button
          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-epic/30 bg-epic/10 px-3 py-2 text-sm font-semibold text-epic transition hover:bg-epic/15 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={disabled || mode !== "builder"}
          onClick={() => void onDeleteEdge(selectedEdge.id)}
          type="button"
        >
          <Link2Off size={16} />
          {t("campaigns.studio.deleteConnection")}
        </button>
      </section>
    );
  }

  return <CampaignReadinessPanel validation={validation} />;
}

function NodeInspector({
  disabled,
  edges,
  mode,
  node,
  nodes,
  onDeleteNode,
  onUpdateNode,
  skills
}: {
  disabled: boolean;
  edges: CampaignStudioEdge[];
  mode: CampaignStudioMode;
  node: CampaignStudioNode;
  nodes: CampaignStudioNode[];
  onDeleteNode: (nodeId: string) => Promise<void>;
  onUpdateNode: (nodeId: string, payload: CampaignNodeUpdatePayload) => Promise<void>;
  skills: SettingsSkill[];
}) {
  const { t } = useI18n();
  const [form, setForm] = useState<NodeFormState>(() => formFromNode(node));
  const isBuilder = mode === "builder";

  useEffect(() => {
    setForm(formFromNode(node));
  }, [node]);

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
    await onUpdateNode(node.id, {
      title: form.title.trim(),
      description: form.description.trim(),
      stage: form.stage.trim(),
      rewardXp: Number(form.rewardXp) || 0,
      rewardSkillId: form.rewardSkillId || undefined,
      isRequired: form.isRequired,
      unlockMode: form.unlockMode
    });
  }

  return (
    <section className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t(`campaigns.node.${node.nodeKind}`)}</p>
          <h2>{t("campaigns.studio.inspector")}</h2>
        </div>
        <span>{t(`campaigns.state.${node.state}`)}</span>
      </div>

      <p className="mt-4 text-sm leading-6 text-zinc-500">
        {t(`campaigns.node.${node.nodeKind}.description`)}
      </p>

      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
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
        <div className="grid gap-3 sm:grid-cols-2">
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
          </label>
          <label className="block">
            <span className="field-label">{t("campaigns.studio.rewardSkill")}</span>
            <select
              className="field-control"
              disabled={disabled || !isBuilder}
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
        </div>
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
        <label className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
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

        <button
          className="primary-button inline-flex items-center justify-center gap-2"
          disabled={disabled || !isBuilder}
          type="submit"
        >
          <Save size={16} />
          {t("campaigns.studio.saveNode")}
        </button>
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
    rewardSkillId: "",
    isRequired: node.isRequired,
    unlockMode: node.unlockMode
  };
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
