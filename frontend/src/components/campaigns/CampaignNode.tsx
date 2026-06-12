import { CheckCircle2, Flag, Gem, GitBranch, Lock, Milestone, PenLine, ShieldCheck, Trophy } from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { CampaignFlowNode } from "./campaignFlowMapper";
import type { CampaignNodeKind, CampaignQuestState } from "../../types/campaigns";

const stateClasses: Record<CampaignQuestState, string> = {
  locked: "border-white/10 bg-zinc-950/80 text-zinc-500",
  available: "border-xp/50 bg-xp/10 text-zinc-100 shadow-[0_0_30px_rgb(var(--color-xp)/0.12)]",
  completed: "border-success/50 bg-success/10 text-zinc-100 shadow-[0_0_30px_rgb(var(--color-success)/0.12)]"
};

export function CampaignNode({ data, selected }: NodeProps<CampaignFlowNode>) {
  const { node, mode, t } = data;
  const Icon = nodeKindIcon(node.nodeKind);

  return (
    <div
      className={`min-h-[118px] w-[236px] rounded-lg border p-3 backdrop-blur-xl transition ${stateClasses[node.state]} ${
        selected ? "ring-2 ring-xp/70" : ""
      }`}
    >
      <Handle
        className="!h-3 !w-3 !border-xp/40 !bg-background"
        isConnectable={mode === "builder"}
        position={Position.Left}
        type="target"
      />
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/[0.05] text-xp">
            <Icon size={16} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.16em] text-xp">
              {t(`campaigns.node.${node.nodeKind}`)}
            </p>
            <p className="mt-0.5 truncate text-sm font-semibold text-zinc-50">
              {node.title || t("campaigns.studio.untitledNode")}
            </p>
          </div>
        </div>
        {stateIcon(node.state)}
      </div>

      <p className="mt-3 line-clamp-2 min-h-8 text-xs leading-4 text-zinc-400">
        {node.description || t("campaigns.studio.nodeDescriptionEmpty")}
      </p>

      <div className="mt-3 flex items-center justify-between gap-3 text-xs">
        <span className="truncate text-zinc-500">{node.stage || t("campaigns.studio.noStage")}</span>
        <span className="shrink-0 font-semibold text-xp">+{node.rewardXp} XP</span>
      </div>

      <Handle
        className="!h-3 !w-3 !border-xp/40 !bg-background"
        isConnectable={mode === "builder"}
        position={Position.Right}
        type="source"
      />
    </div>
  );
}

function nodeKindIcon(kind: CampaignNodeKind) {
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

function stateIcon(state: CampaignQuestState) {
  if (state === "completed") {
    return <CheckCircle2 className="shrink-0 text-success" size={16} />;
  }
  if (state === "locked") {
    return <Lock className="shrink-0 text-zinc-500" size={16} />;
  }
  return <ShieldCheck className="shrink-0 text-xp" size={16} />;
}
