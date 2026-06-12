import { Archive, Bot, CheckCircle2, GitBranch, LayoutDashboard, Play, RefreshCw, Save } from "lucide-react";

import { useI18n } from "../../i18n";
import type { Campaign, CampaignStudioMode } from "../../types/campaigns";

interface CampaignToolbarProps {
  campaign: Campaign;
  mode: CampaignStudioMode;
  pendingAction: string | null;
  onModeChange: (mode: CampaignStudioMode) => void;
  onAutoLayout: () => void;
  onValidate: () => void;
  onPublish: () => void;
  onArchive: () => void;
  onAiDraft: () => void;
  onRefresh: () => void;
}

export function CampaignToolbar({
  campaign,
  mode,
  pendingAction,
  onModeChange,
  onAutoLayout,
  onValidate,
  onPublish,
  onArchive,
  onAiDraft,
  onRefresh
}: CampaignToolbarProps) {
  const { t } = useI18n();
  const isBusy = pendingAction !== null;
  const isDraft = campaign.status === "draft";

  return (
    <section className="panel p-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <p className="eyebrow">{t("campaigns.studio.label")}</p>
          <h2 className="truncate text-lg font-semibold text-zinc-50">{campaign.title}</h2>
          <p className="mt-1 truncate text-sm text-zinc-500">
            {campaign.description || t("campaigns.studio.noCampaignDescription")}
          </p>
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
              <Play size={15} />
              {t("campaigns.studio.play")}
            </button>
          </div>

          <ToolbarButton disabled={isBusy || mode !== "builder"} icon={LayoutDashboard} onClick={onAutoLayout}>
            {t("campaigns.studio.autoLayout")}
          </ToolbarButton>
          <ToolbarButton disabled={isBusy} icon={CheckCircle2} onClick={onValidate}>
            {t("campaigns.studio.validate")}
          </ToolbarButton>
          <ToolbarButton disabled={isBusy || !isDraft} icon={Save} onClick={onPublish} variant="primary">
            {t("campaigns.studio.publish")}
          </ToolbarButton>
          <ToolbarButton disabled={isBusy} icon={Bot} onClick={onAiDraft}>
            {t("campaigns.studio.aiDraft")}
          </ToolbarButton>
          <ToolbarButton disabled={isBusy} icon={Archive} onClick={onArchive}>
            {t("campaigns.studio.archive")}
          </ToolbarButton>
          <button
            className="icon-button"
            disabled={isBusy}
            onClick={onRefresh}
            title={t("common.refresh")}
            type="button"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}

function ToolbarButton({
  children,
  disabled,
  icon: Icon,
  onClick,
  variant = "secondary"
}: {
  children: string;
  disabled: boolean;
  icon: typeof Archive;
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
