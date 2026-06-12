import { FormEvent, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";

import { useI18n } from "../../i18n";
import type { CampaignDifficulty, CampaignPayload, CampaignSummary } from "../../types/campaigns";
import { ProgressBar } from "../ui/ProgressBar";

interface CampaignListPanelProps {
  campaigns: CampaignSummary[];
  selectedCampaignId: string | null;
  disabled: boolean;
  onCreateCampaign: (payload: CampaignPayload) => Promise<void>;
  onRefresh: () => void;
  onSelectCampaign: (campaignId: string) => void;
}

const difficulties: CampaignDifficulty[] = ["easy", "normal", "hard", "epic", "legendary"];

export function CampaignListPanel({
  campaigns,
  selectedCampaignId,
  disabled,
  onCreateCampaign,
  onRefresh,
  onSelectCampaign
}: CampaignListPanelProps) {
  const { t } = useI18n();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState<CampaignDifficulty>("normal");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      return;
    }
    await onCreateCampaign({
      title: title.trim(),
      description: description.trim(),
      difficulty
    });
    setTitle("");
    setDescription("");
    setDifficulty("normal");
  }

  return (
    <section className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("campaigns.label")}</p>
          <h2>{t("campaigns.studio.library")}</h2>
        </div>
        <button
          className="icon-button h-8 w-8"
          disabled={disabled}
          onClick={onRefresh}
          title={t("common.refresh")}
          type="button"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      <form className="mt-4 space-y-2 rounded-lg border border-white/10 bg-white/[0.03] p-3" onSubmit={handleSubmit}>
        <p className="text-sm font-semibold text-zinc-100">{t("campaigns.studio.newCampaign")}</p>
        <input
          className="field-control mt-2"
          disabled={disabled}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("campaigns.studio.campaignTitle")}
          value={title}
        />
        <textarea
          className="field-control min-h-20 resize-none"
          disabled={disabled}
          onChange={(event) => setDescription(event.target.value)}
          placeholder={t("campaigns.studio.campaignDescription")}
          value={description}
        />
        <select
          className="field-control"
          disabled={disabled}
          onChange={(event) => setDifficulty(event.target.value as CampaignDifficulty)}
          value={difficulty}
        >
          {difficulties.map((option) => (
            <option key={option} value={option}>
              {t(`campaigns.difficulty.${option}`)}
            </option>
          ))}
        </select>
        <button className="primary-button inline-flex items-center justify-center gap-2" disabled={disabled || !title.trim()} type="submit">
          <Plus size={16} />
          {t("campaigns.studio.createCampaign")}
        </button>
      </form>

      <div className="mt-4 space-y-2">
        {campaigns.map((campaign) => (
          <button
            className={`w-full rounded-lg border p-3 text-left transition ${
              selectedCampaignId === campaign.id
                ? "border-xp/50 bg-xp/10"
                : "border-white/10 bg-white/[0.03] hover:border-white/20"
            }`}
            disabled={disabled}
            key={campaign.id}
            onClick={() => onSelectCampaign(campaign.id)}
            type="button"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-zinc-100">{campaign.title}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.16em] text-zinc-500">
                  {t(`campaigns.status.${campaign.status}`)} · {t(`campaigns.createdBy.${campaign.createdBy}`)}
                </p>
              </div>
              <span className="text-xs font-semibold text-xp">
                {campaign.progressPercent}%
              </span>
            </div>
            <ProgressBar className="mt-3 h-1.5" value={campaign.progressPercent} />
          </button>
        ))}
        {!campaigns.length ? (
          <p className="rounded-lg border border-white/10 bg-white/[0.03] p-3 text-sm leading-6 text-zinc-500">
            {t("campaigns.studio.emptyLibrary")}
          </p>
        ) : null}
      </div>
    </section>
  );
}
