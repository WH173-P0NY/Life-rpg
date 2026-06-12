import { useMemo, useState } from "react";

import type { SettingsSkill } from "../../api/settings";
import { useI18n } from "../../i18n";
import type {
  Campaign,
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
import { CampaignPalette } from "./CampaignPalette";
import { CampaignToolbar } from "./CampaignToolbar";
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
  onAddNode: (kind: CampaignNodeKind) => Promise<void>;
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

  return (
    <div className="grid gap-4 2xl:grid-cols-[320px_minmax(0,1fr)_380px]">
      <aside className="space-y-4">
        <CampaignListPanel
          campaigns={campaigns}
          disabled={disabled}
          onCreateCampaign={onCreateCampaign}
          onRefresh={() => void onRefresh()}
          onSelectCampaign={onSelectCampaign}
          selectedCampaignId={studio.campaign.id}
        />
        <CampaignPalette
          availableNodeTypes={studio.availableNodeTypes}
          disabled={disabled || mode !== "builder"}
          onAddNode={(kind) => void onAddNode(kind)}
        />
      </aside>

      <main className="min-w-0 space-y-4">
        <CampaignToolbar
          campaign={studio.campaign}
          mode={mode}
          onAiDraft={() => void onAiDraft()}
          onArchive={() => void onArchive()}
          onAutoLayout={() => void handleAutoLayout()}
          onModeChange={onModeChange}
          onPublish={() => void onPublish()}
          onRefresh={() => void onRefresh()}
          onValidate={() => void onValidate()}
          pendingAction={pendingAction}
        />

        {errorMessage ? (
          <p className="rounded-lg border border-epic/30 bg-epic/10 px-4 py-3 text-sm text-epic">
            {errorMessage}
          </p>
        ) : null}

        <CampaignCanvas
          edges={studio.edges}
          mode={mode}
          nodes={studio.nodes}
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

      <aside className="space-y-4">
        <CampaignInspector
          disabled={disabled}
          edges={studio.edges}
          mode={mode}
          nodes={studio.nodes}
          onDeleteEdge={onDeleteEdge}
          onDeleteNode={onDeleteNode}
          onUpdateNode={onUpdateNode}
          selectedEdgeId={selectedEdgeId}
          selectedNodeId={selectedNodeId}
          skills={skills}
          validation={validation}
        />
      </aside>
    </div>
  );
}
