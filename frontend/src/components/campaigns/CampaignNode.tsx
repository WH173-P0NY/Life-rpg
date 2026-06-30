import {
  CheckCircle2,
  Flag,
  Gem,
  GitBranch,
  Lock,
  Milestone,
  PenLine,
  Plus,
  ShieldCheck,
  Trophy
} from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { CampaignFlowNode } from "./campaignFlowMapper";
import type { CampaignNodeKind, CampaignQuestState } from "../../types/campaigns";

const moduleStateClasses: Record<CampaignQuestState, string> = {
  locked: "border-white/10 bg-zinc-950/90 text-zinc-500",
  available:
    "border-xp/55 bg-xp/10 text-xp shadow-[0_0_28px_rgb(var(--color-xp)/0.16)]",
  completed:
    "border-success/60 bg-success/15 text-success shadow-[0_0_28px_rgb(var(--color-success)/0.16)]"
};

const statusBadgeClasses: Record<CampaignQuestState, string> = {
  locked: "border-white/10 bg-zinc-950 text-zinc-500",
  available: "border-xp/50 bg-background text-xp",
  completed: "border-success/50 bg-background text-success"
};

export function CampaignNode({ data, selected }: NodeProps<CampaignFlowNode>) {
  const { node, mode, t } = data;
  const Icon = nodeKindIcon(node.nodeKind);
  const title = node.title || t("campaigns.studio.untitledNode");
  const stateLabel = t(`campaigns.state.${node.state}`);
  const kindLabel = t(`campaigns.node.${node.nodeKind}`);

  return (
    <div
      className="group relative h-[132px] w-[136px] select-none"
      title={`${kindLabel}: ${title}`}
    >
      <Handle
        className="!h-3 !w-3 !border-xp/45 !bg-background"
        isConnectable={mode === "builder"}
        position={Position.Left}
        style={{ left: 22, top: 42 }}
        type="target"
      />

      <div
        className={`relative mx-auto grid h-[84px] w-[84px] place-items-center rounded-[24px] border backdrop-blur-xl transition-colors ${moduleStateClasses[node.state]} ${
          selected ? "ring-2 ring-xp/80 ring-offset-2 ring-offset-background" : ""
        }`}
      >
        <span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/[0.06]">
          <Icon size={24} />
        </span>
        <span
          aria-label={stateLabel}
          className={`absolute -right-1 -top-1 grid h-7 w-7 place-items-center rounded-full border shadow-lg ${statusBadgeClasses[node.state]}`}
          title={stateLabel}
        >
          {stateIcon(node.state)}
        </span>
        {node.rewardXp > 0 ? (
          <span className="absolute -bottom-2 right-1 whitespace-nowrap rounded-full border border-xp/40 bg-background px-1.5 py-0.5 text-[10px] font-semibold leading-none text-xp shadow-lg">
            +{node.rewardXp} XP
          </span>
        ) : null}
      </div>

      <button
        aria-label={t("campaigns.studio.addNextNode")}
        className="nodrag nopan absolute right-[-38px] top-[29px] grid h-7 w-7 place-items-center rounded-full border border-xp/35 bg-background/95 text-xp opacity-0 shadow-lg transition-opacity hover:border-xp group-hover:opacity-100 group-focus-within:opacity-100 disabled:pointer-events-none disabled:opacity-0"
        disabled={mode !== "builder"}
        onClick={(event) => {
          event.stopPropagation();
          data.onAddNodeRequest?.({ sourceNodeId: node.id });
        }}
        type="button"
      >
        <Plus size={15} />
      </button>

      <p className="mx-auto mt-3 line-clamp-2 h-9 w-[124px] break-words px-1 text-center text-[13px] font-semibold leading-[18px] text-zinc-100">
        {title}
      </p>

      <Handle
        className="!h-3 !w-3 !border-xp/45 !bg-background"
        isConnectable={mode === "builder"}
        position={Position.Right}
        style={{ right: 22, top: 42 }}
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
    return <CheckCircle2 className="shrink-0" size={15} />;
  }
  if (state === "locked") {
    return <Lock className="shrink-0" size={15} />;
  }
  return <ShieldCheck className="shrink-0" size={15} />;
}
