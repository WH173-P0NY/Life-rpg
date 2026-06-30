import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import {
  Archive,
  Bot,
  CheckCircle2,
  ChevronDown,
  GitBranch,
  LayoutDashboard,
  Plus,
  RefreshCw,
  Save,
  Search,
  X
} from "lucide-react";

import type { SettingsSkill } from "../../api/settings";
import { useI18n } from "../../i18n";
import type {
  Campaign,
  CampaignAddNodeRequest,
  CampaignNodeKind,
  CampaignNodePositionPayload,
  CampaignNodeUpdatePayload,
  CampaignStudioEdge,
  CampaignStudioMode,
  CampaignStudioResponse,
  CampaignSummary,
  CampaignValidationReport
} from "../../types/campaigns";
import { CampaignCanvas } from "./CampaignCanvas";
import { CampaignInspector } from "./CampaignInspector";
import { CampaignListPanel } from "./CampaignListPanel";
import { CampaignReadinessPanel } from "./CampaignReadinessPanel";
import {
  layoutCampaignNodes,
  resolveCampaignNodeDragPositions
} from "./campaignLayout";
import { validateCampaignLocally } from "./campaignValidation";

interface CampaignStudioProps {
  campaigns: CampaignSummary[];
  disabled: boolean;
  errorMessage: string | null;
  mode: CampaignStudioMode;
  pendingAction: string | null;
  skills: SettingsSkill[];
  studio: CampaignStudioResponse | null;
  onAddNode: (request: CampaignAddNodeRequest) => Promise<void>;
  onAiDraft: () => Promise<void>;
  onArchive: () => Promise<void>;
  onCreateCampaign: (payload: {
    title: string;
    description?: string;
    difficulty?: Campaign["difficulty"];
  }) => Promise<void>;
  onCreateEdge: (sourceNodeId: string, targetNodeId: string) => Promise<void>;
  onDeleteEdge: (edgeId: string) => Promise<void>;
  onDeleteNode: (nodeId: string) => Promise<void>;
  onModeChange: (mode: CampaignStudioMode) => void;
  onPublish: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onSelectCampaign: (campaignId: string) => void;
  onUpdateNode: (nodeId: string, payload: CampaignNodeUpdatePayload) => Promise<void>;
  onUpdatePositions: (positions: CampaignNodePositionPayload[]) => Promise<void>;
  onValidate: () => Promise<CampaignValidationReport | null>;
}

export function CampaignStudio({
  campaigns,
  disabled,
  errorMessage,
  mode,
  pendingAction,
  skills,
  studio,
  onAddNode,
  onAiDraft,
  onArchive,
  onCreateCampaign,
  onCreateEdge,
  onDeleteEdge,
  onDeleteNode,
  onModeChange,
  onPublish,
  onRefresh,
  onSelectCampaign,
  onUpdateNode,
  onUpdatePositions,
  onValidate
}: CampaignStudioProps) {
  const { t } = useI18n();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [isSwitcherOpen, setIsSwitcherOpen] = useState(false);
  const [isValidationOpen, setIsValidationOpen] = useState(false);
  const [isInspectorDirty, setIsInspectorDirty] = useState(false);
  const [nodePickerContext, setNodePickerContext] =
    useState<Omit<CampaignAddNodeRequest, "kind"> | null>(null);
  const localValidation = useMemo(
    () => validateCampaignLocally(studio?.nodes ?? [], studio?.edges ?? []),
    [studio?.edges, studio?.nodes]
  );
  const validation =
    studio?.validation.checks.length || studio?.validation.issues.length
      ? studio.validation
      : localValidation;

  async function handleAutoLayout() {
    if (!studio) {
      return;
    }
    const positions = layoutCampaignNodes(studio.nodes, studio.edges);
    await onUpdatePositions(positions);
  }

  async function handleAddNode(request: CampaignAddNodeRequest) {
    await onAddNode({
      ...(nodePickerContext ?? {}),
      ...request
    });
    setNodePickerContext(null);
  }

  async function handleValidate() {
    const report = await onValidate();
    if (report && !report.valid) {
      setIsValidationOpen(true);
    }
  }

  function handleInspectorClose() {
    if (isInspectorDirty) {
      return;
    }
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setIsInspectorDirty(false);
  }

  if (!studio) {
    return (
      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <CampaignListPanel
          campaigns={campaigns}
          disabled={disabled}
          onCreateCampaign={onCreateCampaign}
          onRefresh={() => void onRefresh()}
          onSelectCampaign={onSelectCampaign}
          selectedCampaignId={null}
        />
        <section className="panel grid min-h-[520px] place-items-center p-8 text-center">
          <div className="max-w-md">
            <p className="eyebrow">{t("campaigns.studio.label")}</p>
            <h2 className="text-xl font-semibold text-zinc-50">
              {t("campaigns.noSelection")}
            </h2>
            <p className="mt-3 text-sm leading-6 text-zinc-500">
              {t("campaigns.studio.noSelectionDescription")}
            </p>
            {errorMessage ? (
              <p className="mt-4 rounded-lg border border-epic/30 bg-epic/10 p-3 text-sm text-epic">
                {errorMessage}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    );
  }

  const selectedItem = selectedNodeId || selectedEdgeId;
  const isBusy = pendingAction !== null;
  const isDraft = studio.campaign.status === "draft";

  return (
    <div className="relative min-w-0 space-y-3">
      <section className="panel p-3">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <button
              className="inline-flex min-w-0 max-w-full items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-left transition hover:border-xp/40"
              onClick={() => setIsSwitcherOpen((current) => !current)}
              type="button"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-zinc-50">
                  {studio.campaign.title}
                </span>
                <span className="block truncate text-xs text-zinc-500">
                  {studio.campaign.description || t("campaigns.studio.noCampaignDescription")}
                </span>
              </span>
              <span className="rounded-md border border-white/10 px-2 py-1 text-xs text-zinc-400">
                {t(`campaigns.status.${studio.campaign.status}`)}
              </span>
              <ChevronDown className="shrink-0 text-zinc-500" size={16} />
            </button>

            <button
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition ${
                validation.valid
                  ? "border-success/40 bg-success/10 text-success"
                  : "border-epic/40 bg-epic/10 text-epic"
              }`}
              onClick={() => setIsValidationOpen(true)}
              type="button"
            >
              <CheckCircle2 size={15} />
              {validation.valid
                ? t("campaigns.studio.ready")
                : t("campaigns.studio.needsWork")}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-white/10 bg-white/[0.04] p-1">
              <button
                className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition ${
                  mode === "builder" ? "bg-xp text-background" : "text-zinc-400 hover:text-zinc-100"
                }`}
                onClick={() => onModeChange("builder")}
                type="button"
              >
                <GitBranch size={15} />
                {t("campaigns.studio.builder")}
              </button>
              <button
                className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition ${
                  mode === "play" ? "bg-success text-background" : "text-zinc-400 hover:text-zinc-100"
                }`}
                onClick={() => onModeChange("play")}
                type="button"
              >
                {t("campaigns.studio.play")}
              </button>
            </div>

            <WorkbenchButton disabled={disabled || mode !== "builder"} icon={Plus} onClick={() => setNodePickerContext({})}>
              {t("common.add")}
            </WorkbenchButton>
            <WorkbenchButton disabled={disabled || mode !== "builder"} icon={LayoutDashboard} onClick={() => void handleAutoLayout()}>
              {t("campaigns.studio.autoLayout")}
            </WorkbenchButton>
            <WorkbenchButton disabled={disabled} icon={CheckCircle2} onClick={() => void handleValidate()}>
              {t("campaigns.studio.validate")}
            </WorkbenchButton>
            <WorkbenchButton disabled={disabled || !isDraft} icon={Save} onClick={() => void onPublish()} variant="primary">
              {t("campaigns.studio.publish")}
            </WorkbenchButton>
            <WorkbenchButton disabled={disabled} icon={Bot} onClick={() => void onAiDraft()}>
              {t("campaigns.studio.aiDraft")}
            </WorkbenchButton>
            <button
              className="icon-button"
              disabled={isBusy}
              onClick={() => void onArchive()}
              title={t("campaigns.studio.archive")}
              type="button"
            >
              <Archive size={16} />
            </button>
            <button
              className="icon-button"
              disabled={isBusy}
              onClick={() => void onRefresh()}
              title={t("common.refresh")}
              type="button"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>
      </section>

      {isSwitcherOpen ? (
        <div className="absolute left-0 top-16 z-30 w-full max-w-md">
          <CampaignListPanel
            campaigns={campaigns}
            disabled={disabled}
            onCreateCampaign={async (payload) => {
              await onCreateCampaign(payload);
              setIsSwitcherOpen(false);
            }}
            onRefresh={() => void onRefresh()}
            onSelectCampaign={(campaignId) => {
              onSelectCampaign(campaignId);
              setIsSwitcherOpen(false);
            }}
            selectedCampaignId={studio.campaign.id}
          />
        </div>
      ) : null}

      {errorMessage ? (
        <p className="rounded-lg border border-epic/30 bg-epic/10 px-4 py-3 text-sm text-epic">
          {errorMessage}
        </p>
      ) : null}

      <main className="min-w-0">
        <CampaignCanvas
          edges={studio.edges}
          mode={mode}
          nodes={studio.nodes}
          onAddNodeRequest={setNodePickerContext}
          onConnect={onCreateEdge}
          onEdgeSelect={setSelectedEdgeId}
          onEdgesDelete={async (edgeIds) => {
            for (const edgeId of edgeIds) {
              await onDeleteEdge(edgeId);
            }
          }}
          onNodeDragStop={async (nodeId, position) =>
            onUpdatePositions(
              resolveCampaignNodeDragPositions(studio.nodes, nodeId, position)
            )
          }
          onNodeSelect={setSelectedNodeId}
          onNodesDelete={async (nodeIds) => {
            for (const nodeId of nodeIds) {
              await onDeleteNode(nodeId);
            }
          }}
        />
      </main>

      {nodePickerContext ? (
        <NodePickerPopover
          availableNodeTypes={studio.availableNodeTypes}
          disabled={disabled}
          onAddNode={(request) => void handleAddNode(request)}
          onClose={() => setNodePickerContext(null)}
          skills={skills}
        />
      ) : null}

      {selectedItem ? (
        <Drawer title={t("campaigns.studio.inspector")} onClose={handleInspectorClose}>
          <CampaignInspector
            disabled={disabled}
            edges={studio.edges}
            mode={mode}
            nodes={studio.nodes}
            onDirtyChange={setIsInspectorDirty}
            onDeleteEdge={onDeleteEdge}
            onDeleteNode={onDeleteNode}
            onRequestClose={handleInspectorClose}
            onUpdateNode={onUpdateNode}
            selectedEdgeId={selectedEdgeId}
            selectedNodeId={selectedNodeId}
            skills={skills}
            validation={validation}
          />
        </Drawer>
      ) : null}

      {isValidationOpen ? (
        <Drawer title={t("campaigns.studio.readiness")} onClose={() => setIsValidationOpen(false)}>
          <CampaignReadinessPanel validation={validation} />
        </Drawer>
      ) : null}
    </div>
  );
}

function WorkbenchButton({
  children,
  disabled,
  icon: Icon,
  onClick,
  variant = "secondary"
}: {
  children: string;
  disabled: boolean;
  icon: typeof Plus;
  onClick: () => void;
  variant?: "primary" | "secondary";
}) {
  return (
    <button
      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
        variant === "primary"
          ? "border-xp/40 bg-xp text-background hover:bg-xp/90"
          : "border-white/10 bg-white/[0.04] text-zinc-300 hover:border-xp/40 hover:text-xp"
      }`}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <Icon size={15} />
      {children}
    </button>
  );
}

function NodePickerPopover({
  availableNodeTypes,
  disabled,
  onAddNode,
  onClose,
  skills
}: {
  availableNodeTypes: CampaignNodeKind[];
  disabled: boolean;
  onAddNode: (request: CampaignAddNodeRequest) => void;
  onClose: () => void;
  skills: SettingsSkill[];
}) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [selectedKind, setSelectedKind] = useState<CampaignNodeKind | null>(null);
  const [rewardSkillId, setRewardSkillId] = useState(() =>
    skills[0] ? String(skills[0].id) : ""
  );
  const [rewardXp, setRewardXp] = useState("25");
  const nodeTypes = availableNodeTypes.filter((kind) =>
    t(`campaigns.node.${kind}`).toLowerCase().includes(query.toLowerCase())
  );
  const rewardXpValue = Number(rewardXp) || 0;
  const canAddQuestReward = rewardXpValue <= 0 || Boolean(rewardSkillId);

  function handleNodeTypeClick(kind: CampaignNodeKind) {
    if (kind === "quest") {
      setSelectedKind(kind);
      return;
    }
    onAddNode({ kind });
  }

  function handleAddQuest() {
    onAddNode({
      kind: "quest",
      rewardSkillId: rewardSkillId || undefined,
      rewardXp: rewardXpValue
    });
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/30 p-4 backdrop-blur-sm" onClick={onClose}>
      <section
        className="panel mx-auto mt-20 max-w-lg p-4"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">{t("campaigns.studio.addNode")}</p>
            <h2>{t("campaigns.studio.nodePicker")}</h2>
          </div>
          <button className="icon-button" onClick={onClose} type="button">
            <X size={16} />
          </button>
        </div>
        <label className="mt-4 flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
          <Search className="text-zinc-500" size={16} />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("campaigns.studio.searchNodes")}
            value={query}
          />
        </label>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {nodeTypes.map((kind) => (
            <button
              className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-left transition hover:border-xp/40 hover:bg-xp/10 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={disabled}
              key={kind}
              onClick={() => handleNodeTypeClick(kind)}
              type="button"
            >
              <span className="text-sm font-semibold text-zinc-100">
                {t(`campaigns.node.${kind}`)}
              </span>
              <span className="mt-1 block text-xs leading-5 text-zinc-500">
                {t(`campaigns.node.${kind}.description`)}
              </span>
            </button>
          ))}
        </div>
        {selectedKind === "quest" ? (
          <div className="mt-4 space-y-3 rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <label className="block">
              <span className="field-label">{t("campaigns.studio.rewardSkill")}</span>
              <select
                className="field-control"
                disabled={disabled || !skills.length}
                onChange={(event) => setRewardSkillId(event.target.value)}
                value={rewardSkillId}
              >
                {skills.length ? null : (
                  <option value="">{t("campaigns.studio.noRewardSkill")}</option>
                )}
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
                disabled={disabled}
                min={0}
                onChange={(event) => setRewardXp(event.target.value)}
                type="number"
                value={rewardXp}
              />
            </label>
            {!canAddQuestReward ? (
              <p className="text-xs leading-5 text-epic">
                {t("campaigns.studio.rewardSkillRequired")}
              </p>
            ) : null}
            <button
              className="primary-button inline-flex w-full items-center justify-center gap-2"
              disabled={disabled || !canAddQuestReward}
              onClick={handleAddQuest}
              type="button"
            >
              <Plus size={16} />
              {t("campaigns.studio.addQuest")}
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function Drawer({
  children,
  onClose,
  title
}: {
  children: ReactNode;
  onClose: () => void;
  title: string;
}) {
  return (
    <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <aside
        className="panel absolute bottom-0 right-0 top-auto max-h-[88vh] w-full overflow-y-auto p-4 sm:bottom-4 sm:right-4 sm:top-4 sm:max-h-none sm:w-[420px]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-zinc-50">{title}</h2>
          <button className="icon-button" onClick={onClose} type="button">
            <X size={16} />
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
