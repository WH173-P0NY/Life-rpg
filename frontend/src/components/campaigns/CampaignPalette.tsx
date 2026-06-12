import { Flag, Gem, GitBranch, Milestone, PenLine, Plus, ShieldCheck, Trophy } from "lucide-react";

import { useI18n } from "../../i18n";
import type { CampaignNodeKind } from "../../types/campaigns";

interface CampaignPaletteProps {
  availableNodeTypes: CampaignNodeKind[];
  disabled: boolean;
  onAddNode: (kind: CampaignNodeKind) => void;
}

const defaultNodeTypes: CampaignNodeKind[] = [
  "quest",
  "milestone",
  "reward",
  "reflection",
  "gate"
];

export function CampaignPalette({
  availableNodeTypes,
  disabled,
  onAddNode
}: CampaignPaletteProps) {
  const { t } = useI18n();
  const nodeTypes = availableNodeTypes.length ? availableNodeTypes : defaultNodeTypes;

  return (
    <section className="panel p-4">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("campaigns.studio.palette")}</p>
          <h2>{t("campaigns.studio.addNode")}</h2>
        </div>
        <span>{nodeTypes.length}</span>
      </div>
      <div className="mt-4 space-y-2">
        {nodeTypes.map((kind) => {
          const Icon = iconForKind(kind);

          return (
            <button
              className="flex w-full items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-3 text-left transition hover:border-xp/40 hover:bg-xp/10 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={disabled}
              key={kind}
              onClick={() => onAddNode(kind)}
              type="button"
            >
              <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-xp/30 bg-xp/10 text-xp">
                <Icon size={16} />
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  {t(`campaigns.node.${kind}`)}
                  <Plus size={13} />
                </span>
                <span className="mt-1 block text-xs leading-5 text-zinc-500">
                  {t(`campaigns.node.${kind}.description`)}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function iconForKind(kind: CampaignNodeKind) {
  const icons = {
    start: Flag,
    quest: ShieldCheck,
    milestone: Milestone,
    reward: Gem,
    reflection: PenLine,
    gate: GitBranch,
    end: Trophy
  };

  return icons[kind];
}
