import { useCallback, useEffect, useState } from "react";

import {
  archiveCampaign,
  createCampaign,
  createCampaignEdge,
  createCampaignNode,
  deleteCampaignEdge,
  deleteCampaignNode,
  fetchCampaign,
  fetchCampaigns,
  fetchCampaignStudio,
  generateAiCampaignDraft,
  publishCampaign,
  updateCampaignNode,
  updateCampaignNodePositions,
  validateCampaign
} from "../../api/campaigns";
import { fetchAppSettings, type SettingsSkill } from "../../api/settings";
import { useI18n } from "../../i18n";
import type {
  Campaign,
  CampaignNodeKind,
  CampaignNodePositionPayload,
  CampaignNodeUpdatePayload,
  CampaignPayload,
  CampaignStudioMode,
  CampaignStudioResponse,
  CampaignSummary,
  CampaignValidationReport
} from "../../types/campaigns";
import { CampaignStudio } from "./CampaignStudio";
import { findOpenCampaignNodePosition } from "./campaignLayout";
import { validateCampaignLocally } from "./campaignValidation";

interface CampaignsViewProps {
  isApiReady: boolean;
  onCampaignChanged: () => Promise<void>;
}

export function CampaignsView({ isApiReady, onCampaignChanged }: CampaignsViewProps) {
  const { t } = useI18n();
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [studio, setStudio] = useState<CampaignStudioResponse | null>(null);
  const [skills, setSkills] = useState<SettingsSkill[]>([]);
  const [mode, setMode] = useState<CampaignStudioMode>("builder");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadCampaignStudio = useCallback(
    async (campaignId: string) => {
      try {
        const nextStudio = await fetchCampaignStudio(campaignId);
        setStudio(nextStudio);
        setMode(nextStudio.campaign.status === "draft" ? "builder" : "play");
      } catch (error) {
        const fallbackCampaign = await fetchCampaign(campaignId);
        setStudio(studioFromCampaign(fallbackCampaign));
        setMode(fallbackCampaign.status === "draft" ? "builder" : "play");
        setErrorMessage(
          error instanceof Error
            ? `${t("campaigns.studio.contractPending")}: ${error.message}`
            : t("campaigns.studio.contractPending")
        );
      }
    },
    [t]
  );

  const refreshCampaigns = useCallback(
    async (preferredCampaignId?: string) => {
      if (!isApiReady) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [campaignResponse, settingsResponse] = await Promise.all([
          fetchCampaigns("all"),
          fetchAppSettings()
        ]);
        setCampaigns(campaignResponse.campaigns);
        setSkills(settingsResponse.skills);
        const nextCampaignId =
          preferredCampaignId ??
          selectedCampaignId ??
          campaignResponse.campaigns[0]?.id ??
          null;
        setSelectedCampaignId(nextCampaignId);
        if (nextCampaignId) {
          await loadCampaignStudio(nextCampaignId);
        } else {
          setStudio(null);
        }
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : t("campaigns.apiError"));
      } finally {
        setIsLoading(false);
      }
    },
    [isApiReady, loadCampaignStudio, selectedCampaignId, t]
  );

  useEffect(() => {
    void refreshCampaigns();
  }, [refreshCampaigns]);

  async function runStudioAction(actionName: string, action: () => Promise<void>) {
    if (!isApiReady || pendingAction) {
      return;
    }
    setPendingAction(actionName);
    setErrorMessage(null);
    try {
      await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : t("campaigns.mutationFailed"));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleCreateCampaign(payload: CampaignPayload) {
    await runStudioAction("create-campaign", async () => {
      const response = await createCampaign(payload);
      setSelectedCampaignId(response.campaign.id);
      await refreshCampaigns(response.campaign.id);
      await onCampaignChanged();
    });
  }

  function handleSelectCampaign(campaignId: string) {
    if (pendingAction) {
      return;
    }
    setSelectedCampaignId(campaignId);
    setErrorMessage(null);
    void loadCampaignStudio(campaignId);
  }

  async function handleAddNode(kind: CampaignNodeKind) {
    if (!studio) {
      return;
    }
    await runStudioAction("add-node", async () => {
      const nodeCount = studio.nodes.length;
      const position = findOpenCampaignNodePosition(studio.nodes, {
        x: 160 + nodeCount * 80,
        y: 120
      });

      await createCampaignNode(studio.campaign.id, {
        nodeKind: kind,
        title: t(`campaigns.node.${kind}`),
        description: "",
        stage: t("campaigns.studio.defaultStage"),
        isRequired: kind !== "reward",
        unlockMode: nodeCount ? "after_dependencies" : "immediate",
        position,
        rewardXp: kind === "quest" ? 25 : 0,
        targetValue: 1,
        targetUnit: "check",
        difficulty: "normal",
        config: {}
      });
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleCreateEdge(sourceNodeId: string, targetNodeId: string) {
    if (!studio) {
      return;
    }
    await runStudioAction("create-edge", async () => {
      await createCampaignEdge(studio.campaign.id, { sourceNodeId, targetNodeId });
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleDeleteEdge(edgeId: string) {
    if (!studio) {
      return;
    }
    await runStudioAction("delete-edge", async () => {
      await deleteCampaignEdge(studio.campaign.id, edgeId);
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleDeleteNode(nodeId: string) {
    if (!studio) {
      return;
    }
    await runStudioAction("delete-node", async () => {
      await deleteCampaignNode(studio.campaign.id, nodeId);
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleUpdateNode(nodeId: string, payload: CampaignNodeUpdatePayload) {
    if (!studio) {
      return;
    }
    await runStudioAction("update-node", async () => {
      await updateCampaignNode(studio.campaign.id, nodeId, payload);
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleUpdatePositions(positions: CampaignNodePositionPayload[]) {
    if (!studio || !positions.length) {
      return;
    }
    await runStudioAction("update-positions", async () => {
      await updateCampaignNodePositions(studio.campaign.id, positions);
      await refreshCampaigns(studio.campaign.id);
    });
  }

  async function handleValidate(): Promise<CampaignValidationReport | null> {
    if (!studio) {
      return null;
    }
    let report: CampaignValidationReport | null = null;
    await runStudioAction("validate", async () => {
      try {
        report = await validateCampaign(studio.campaign.id);
      } catch {
        report = validateCampaignLocally(studio.nodes, studio.edges);
      }
      setStudio((current) =>
        current
          ? {
              ...current,
              validation: report ?? current.validation
            }
          : current
      );
    });
    return report;
  }

  async function handlePublish() {
    if (!studio) {
      return;
    }
    await runStudioAction("publish", async () => {
      await publishCampaign(studio.campaign.id);
      await refreshCampaigns(studio.campaign.id);
      await onCampaignChanged();
    });
  }

  async function handleArchive() {
    if (!studio) {
      return;
    }
    await runStudioAction("archive", async () => {
      const response = await archiveCampaign(studio.campaign.id);
      await refreshCampaigns(response.campaign.id);
      await onCampaignChanged();
    });
  }

  async function handleAiDraft() {
    const goal = window.prompt(t("campaigns.studio.aiPrompt"));
    if (!goal?.trim()) {
      return;
    }
    await runStudioAction("ai-draft", async () => {
      const response = await generateAiCampaignDraft({
        goal: goal.trim(),
        difficulty: "normal"
      });
      setSelectedCampaignId(response.campaign.id);
      await refreshCampaigns(response.campaign.id);
      await onCampaignChanged();
    });
  }

  if (!isApiReady) {
    return (
      <section className="panel p-4">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{t("campaigns.label")}</p>
            <h2>{t("campaigns.title")}</h2>
          </div>
          <span>{t("common.preview")}</span>
        </div>
        <p className="mt-4 text-sm text-zinc-500">{t("campaigns.apiRequired")}</p>
      </section>
    );
  }

  return (
    <CampaignStudio
      campaigns={campaigns}
      disabled={isLoading || pendingAction !== null}
      errorMessage={errorMessage}
      mode={mode}
      onAddNode={handleAddNode}
      onAiDraft={handleAiDraft}
      onArchive={handleArchive}
      onCreateCampaign={handleCreateCampaign}
      onCreateEdge={handleCreateEdge}
      onDeleteEdge={handleDeleteEdge}
      onDeleteNode={handleDeleteNode}
      onModeChange={setMode}
      onPublish={handlePublish}
      onRefresh={() => refreshCampaigns(studio?.campaign.id)}
      onSelectCampaign={handleSelectCampaign}
      onUpdateNode={handleUpdateNode}
      onUpdatePositions={handleUpdatePositions}
      onValidate={handleValidate}
      pendingAction={pendingAction}
      skills={skills}
      studio={studio}
    />
  );
}

function studioFromCampaign(campaign: Campaign): CampaignStudioResponse {
  const nodes = campaign.map.nodes.map((node) => ({
    ...node,
    nodeKind: "quest" as const,
    position: {
      x: node.x,
      y: node.y
    },
    config: {}
  }));
  const edges = campaign.map.edges.map((edge) => ({
    id: edge.id,
    sourceNodeId: edge.from,
    targetNodeId: edge.to
  }));

  return {
    campaign,
    nodes,
    edges,
    validation: validateCampaignLocally(nodes, edges),
    availableNodeTypes: ["quest", "milestone", "reward", "reflection", "gate"]
  };
}
